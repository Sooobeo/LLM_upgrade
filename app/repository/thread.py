# app/repository/thread.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from uuid import uuid4
from datetime import datetime, timezone
from app.db import supabase as sb


def _normalize_role(role: str) -> str:
    r = (role or "").lower().strip()
    return "user" if r == "user" else "assistant"


# ----------------------------------------
# 1) 스레드 생성 + 초기 메시지 삽입
# ----------------------------------------
def create_thread_with_messages(
    owner_id: str,
    payload: Dict[str, Any],
    access_token: str,  # signature 유지용
) -> str:
    _ = access_token
    client = sb.get_supabase()

    thread_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    t = {
        "id": thread_id,
        "title": (payload.get("title") or "").strip(),
        "owner_id": owner_id,
        "created_at": now,
    }

    r1 = client.table("threads").insert(t).execute()
    if getattr(r1, "error", None):
        raise RuntimeError(f"threads insert error: {r1.error}")

    msgs_in = payload.get("messages") or []
    rows = []
    for m in msgs_in:
        rows.append(
            {
                "thread_id": thread_id,
                "role": _normalize_role(m.get("role", "")),
                "content": (m.get("content") or "").strip(),
                "created_at": now,
            }
        )

    if rows:
        r2 = client.table("messages").insert(rows).execute()
        if getattr(r2, "error", None):
            raise RuntimeError(f"messages insert error: {r2.error}")

    return thread_id


# ----------------------------------------
# 2) 스레드 목록 조회 (message_count + preview 포함)
# ----------------------------------------
def list_threads_for_owner(
    owner_id: str,
    access_token: str,
    limit: int = 20,
    offset: int = 0,
    order: str = "desc",
) -> List[Dict[str, Any]]:
    _ = access_token
    client = sb.get_supabase()

    order = "desc" if order.lower() != "asc" else "asc"
    desc_flag = order == "desc"

    select_str = ",".join(
        [
            "id",
            "title",
            "created_at",
            "messages(count)",
            "last:messages(content,created_at)",
        ]
    )

    r = (
        client.table("threads")
        .select(select_str)
        .eq("owner_id", owner_id)
        .order("created_at", desc=desc_flag)
        .range(offset, offset + max(0, limit) - 1)
        .execute()
    )
    if getattr(r, "error", None):
        raise RuntimeError(f"threads list error: {r.error}")

    rows = r.data or []
    out = []

    for row in rows:
        # messages(count)
        cnt = 0
        if isinstance(row.get("messages"), list) and row["messages"]:
            cnt = int(row["messages"][0].get("count", 0))

        # last message preview
        preview = None
        if isinstance(row.get("last"), list) and row["last"]:
            preview = (row["last"][0].get("content") or "")[:50] or None

        out.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "created_at": row.get("created_at"),
                "message_count": cnt,
                "last_message_preview": preview,
            }
        )

    return out


# ----------------------------------------
# 3) 스레드 삭제
# ----------------------------------------
def delete_thread_by_id(
    owner_id: str,
    thread_id: str,
    access_token: str,
) -> int:
    _ = access_token
    client = sb.get_supabase()

    r = (
        client.table("threads")
        .delete()
        .eq("id", thread_id)
        .eq("owner_id", owner_id)
        .execute()
    )
    if getattr(r, "error", None):
        raise RuntimeError(f"threads delete error: {r.error}")

    return len(r.data or [])


# ----------------------------------------
# 4) 스레드 상세 조회
# ----------------------------------------
def get_thread_detail(
    owner_id: str,
    thread_id: str,
    access_token: str,
) -> Dict[str, Any]:
    _ = access_token
    client = sb.get_supabase()

    rt = (
        client.table("threads")
        .select("id,title,created_at")
        .eq("id", thread_id)
        .eq("owner_id", owner_id)
        .single()
        .execute()
    )
    if getattr(rt, "error", None):
        return {}
    if not rt.data:
        return {}

    rm = (
        client.table("messages")
        .select("role,content,created_at")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    if getattr(rm, "error", None):
        raise RuntimeError(f"messages select error: {rm.error}")

    msgs = [
        {
            "role": m.get("role") or "assistant",
            "content": m.get("content") or "",
            "created_at": m.get("created_at") or "",
        }
        for m in (rm.data or [])
    ]

    return {
        "id": rt.data.get("id"),
        "title": rt.data.get("title"),
        "created_at": rt.data.get("created_at"),
        "messages": msgs,
    }


# ----------------------------------------
# 5) 메시지 목록 조회 (index 기반)
# ----------------------------------------
def list_thread_messages(
    owner_id: str,
    thread_id: str,
    access_token: str,
    limit: int = 50,
    offset: int = 0,
    order: str = "asc",
) -> Tuple[bool, list[dict]]:
    _ = access_token
    client = sb.get_supabase()

    # owner check
    rt = (
        client.table("threads")
        .select("id")
        .eq("id", thread_id)
        .eq("owner_id", owner_id)
        .limit(1)
        .execute()
    )
    if getattr(rt, "error", None):
        raise RuntimeError(f"threads check error: {rt.error}")
    if not rt.data:
        return (False, [])

    desc_flag = order.lower() == "desc"

    rm = (
        client.table("messages")
        .select("index,role,content,created_at")
        .eq("thread_id", thread_id)
        .order("index", desc=desc_flag)
        .range(offset, offset + max(0, limit) - 1)
        .execute()
    )
    if getattr(rm, "error", None):
        raise RuntimeError(f"messages list error: {rm.error}")

    rows = [
        {
            "index": int(m.get("index", 0)),
            "role": m.get("role") or "assistant",
            "content": m.get("content") or "",
            "created_at": m.get("created_at") or "",
        }
        for m in (rm.data or [])
    ]

    return (True, rows)


# ----------------------------------------
# 6) 메시지 추가
# ----------------------------------------
def add_messages_to_thread(
    owner_id: str,
    thread_id: str,
    messages: List[Dict[str, str]],
    access_token: str,
) -> Tuple[bool, int]:
    _ = access_token
    client = sb.get_supabase()

    rt = (
        client.table("threads")
        .select("id")
        .eq("id", thread_id)
        .eq("owner_id", owner_id)
        .limit(1)
        .execute()
    )
    if getattr(rt, "error", None):
        raise RuntimeError(f"threads check error: {rt.error}")
    if not rt.data:
        return (False, 0)

    rows = []
    for m in messages:
        content = (m.get("content") or "").strip()
        if not content:
            raise ValueError("Message content cannot be empty")
        rows.append(
            {
                "thread_id": thread_id,
                "role": _normalize_role(m.get("role", "")),
                "content": content,
            }
        )

    if not rows:
        return (True, 0)

    r = client.table("messages").insert(rows).execute()
    if getattr(r, "error", None):
        raise RuntimeError(f"messages insert error: {r.error}")

    return (True, len(rows))


# ----------------------------------------
# 7) NEW! owner_id 기준 메시지 검색
# ----------------------------------------
def search_messages_by_owner(
    owner_id: str,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    asc: bool = False,
) -> List[Dict[str, Any]]:
    client = sb.get_supabase()

    select_cols = "thread_id,role,content,created_at,threads!inner(id,title,owner_id)"

    query = (
        client.table("messages")
        .select(select_cols)
        .eq("threads.owner_id", owner_id)
        .order("created_at", desc=not asc)
        .range(offset, offset + max(0, limit) - 1)
    )

    if q:
        query = query.ilike("content", f"%{q}%")

    r = query.execute()
    if getattr(r, "error", None):
        raise RuntimeError(f"messages search error: {r.error}")

    return r.data or []
