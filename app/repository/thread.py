from __future__ import annotations
from typing import Dict, Any, List, Tuple
from uuid import uuid4
from datetime import datetime, timezone
from urllib.parse import quote
from app.db import supabase as sb

def _normalize_role(role: str) -> str:
    r = (role or "").lower().strip()
    return "user" if r == "user" else "assistant"

# 스레드 생성 + 초기 메시지 삽입
def create_thread_with_messages(owner_id: str, payload: Dict[str, Any], access_token: str) -> str:
    thread_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    t = [{
        "id": thread_id,
        "title": payload["title"].strip(),
        "owner_id": owner_id,
        "created_at": now,
    }]
    sb.rest_insert("threads", t, access_token=access_token)

    msgs = payload.get("messages") or []
    if msgs:
        rows = [{
            "thread_id": thread_id,
            "role": _normalize_role(m["role"]),
            "content": m["content"].strip(),
            "created_at": now,
        } for m in msgs]
        sb.rest_insert("messages", rows, access_token=access_token)

    return thread_id

# 스레드 목록 조회 (owner이거나 member인 스레드 모두)
def list_threads_for_owner(
    owner_id: str,
    access_token: str,
    limit: int = 20,
    offset: int = 0,
    order: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Supabase REST: fetch threads where current user is owner OR member (thread_members.user_id).
    We first fetch membership thread_ids to avoid relying on join semantics that can break.
    """
    order = "desc" if str(order).lower() != "asc" else "asc"

    # Step 1: collect thread_ids where user is a member
    member_rows = sb.rest_select(
        "thread_members",
        "&".join(
            [
                f"user_id=eq.{quote(owner_id)}",
                "select=thread_id",
            ]
        ),
        access_token,
    )
    member_thread_ids = [m.get("thread_id") for m in member_rows if m.get("thread_id")]

    # Build OR filter: owner or in member_thread_ids
    or_filters = [f"owner_id.eq.{quote(owner_id)}"]
    if member_thread_ids:
        ids = ",".join(quote(tid) for tid in member_thread_ids)
        or_filters.append(f"id.in.({ids})")

    filters = [
        "select=" + ",".join(
            [
                "id",
                "title",
                "created_at",
                "is_workspace",
                "messages(count)",
                "last:messages(content,created_at)",
            ]
        ),
        f"or=({','.join(or_filters)})",
        f"order=created_at.{order}",
        f"limit={limit}",
        f"offset={offset}",
        "last.order=created_at.desc",
        "last.limit=1",
    ]
    query = "&".join(filters)
    rows = sb.rest_select("threads", query, access_token)

    member_thread_id_set = set(member_thread_ids)

    out: List[Dict[str, Any]] = []
    for r in rows:
        cnt = int(r.get("messages", [{}])[0].get("count", 0)) if r.get("messages") else 0
        preview = None
        if isinstance(r.get("last"), list) and r["last"]:
            preview = (r["last"][0].get("content") or "")[:50] or None
        # If current user is listed as a member, the thread is a workspace for them.
        is_ws = bool(r.get("is_workspace", False))
        if not is_ws and r.get("id") in member_thread_id_set:
            is_ws = True
        out.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "created_at": r.get("created_at"),
            "is_workspace": is_ws,
            "message_count": cnt,
            "last_message_preview": preview,
        })
    return out

# 스레드 삭제
def delete_thread_by_id(owner_id: str, thread_id: str, access_token: str) -> int:
    q = "&".join([
        f"id=eq.{quote(thread_id)}",
        f"owner_id=eq.{quote(owner_id)}",
    ])
    deleted = sb.rest_delete("threads", q, access_token)
    return deleted

# 스레드 상세 조회
def get_thread_detail(owner_id: str, thread_id: str, access_token: str) -> Dict[str, Any]:
    q = "&".join([
        f"id=eq.{quote(thread_id)}",
        f"owner_id=eq.{quote(owner_id)}",
        "select=" + ",".join([
            "id", "title", "created_at",
            "messages(role,content,created_at)"
        ]),
        "messages.order=created_at.asc",
        "limit=1",
    ])
    rows = sb.rest_select("threads", q, access_token)
    if not rows:
        return {}

    row = rows[0]
    msgs = row.get("messages") or []
    messages = [{
        "role": (m.get("role") or "assistant"),
        "content": m.get("content") or "",
        "created_at": m.get("created_at") or "",
    } for m in msgs]

    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "created_at": row.get("created_at"),
        "messages": messages,
    }

# 스레드별 메시지 목록 조회
def list_thread_messages(
    owner_id: str,
    thread_id: str,
    access_token: str,
    limit: int = 50,
    offset: int = 0,
    order: str = "asc",
) -> Tuple[bool, list[dict]]:
    q_check = "&".join([
        f"id=eq.{quote(thread_id)}",
        f"owner_id=eq.{quote(owner_id)}",
        "select=id",
        "limit=1",
    ])
    trows = sb.rest_select("threads", q_check, access_token)
    if not trows:
        return (False, [])

    order = "asc" if str(order).lower() != "desc" else "desc"
    q_msgs = "&".join([
        f"thread_id=eq.{quote(thread_id)}",
        "select=" + ",".join(["index", "role", "content", "created_at"]),
        f"order=index.{order}",
        f"limit={limit}",
        f"offset={offset}",
    ])
    mrows = sb.rest_select("messages", q_msgs, access_token)

    rows = [{
        "index": int(m.get("index", 0)),
        "role": (m.get("role") or "assistant"),
        "content": m.get("content") or "",
        "created_at": m.get("created_at") or "",
    } for m in mrows]

    return (True, rows)

# 스레드에 메시지 추가
def add_messages_to_thread(
    owner_id: str,
    thread_id: str,
    messages: List[Dict[str, str]],
    access_token: str,
) -> Tuple[bool, int]:
    q_check = "&".join([
        f"id=eq.{quote(thread_id)}",
        f"owner_id=eq.{quote(owner_id)}",
        "select=id",
        "limit=1",
    ])
    trows = sb.rest_select("threads", q_check, access_token)
    if not trows:
        return (False, 0)

    rows = []
    for m in messages:
        content = (m.get("content") or "").strip()
        if not content:
            raise ValueError("Message content cannot be empty")
        rows.append({
            "thread_id": thread_id,
            "role": _normalize_role(m.get("role", "")),
            "content": content,
        })

    sb.rest_insert("messages", rows, access_token)
    return (True, len(rows))
