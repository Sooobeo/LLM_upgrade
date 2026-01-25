from __future__ import annotations
from typing import Dict, Any, List, Tuple
from uuid import uuid4
from datetime import datetime, timezone
from urllib.parse import quote

from app.db import supabase as sb
from app.services import llm_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def _normalize_role(role: str) -> str:
    r = (role or "").lower().strip()
    if r in ("user", "assistant", "system", "tool"):
        return r
    return "assistant"


def _can_access_thread(user_id: str, thread_id: str, access_token: str) -> bool:
    """
    접근 허용 조건
    1) threads.owner_id == user_id
    2) threads.is_workspace == true 이고 thread_members에 user가 존재
    """

    # 1) owner check
    q_owner = "&".join([
        f"id=eq.{quote(thread_id)}",
        f"owner_id=eq.{quote(user_id)}",
        "select=id",
        "limit=1",
    ])
    owner_rows = sb.rest_select("threads", q_owner, access_token)
    if owner_rows:
        return True

    # 2) workspace + member check
    q_thread = "&".join([
        f"id=eq.{quote(thread_id)}",
        "select=id,is_workspace",
        "limit=1",
    ])
    trows = sb.rest_select("threads", q_thread, access_token)
    if not trows or not trows[0].get("is_workspace"):
        return False

    q_member = "&".join([
        f"thread_id=eq.{quote(thread_id)}",
        f"user_id=eq.{quote(user_id)}",
        "select=thread_id",
        "limit=1",
    ])
    mrows = sb.rest_select("thread_members", q_member, access_token)
    return bool(mrows)

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
def delete_thread_by_id(user_id: str, thread_id: str, access_token: str) -> int:
    # Load thread info
    q_thread = "&".join(
        [
            f"id=eq.{quote(thread_id)}",
            "select=id,owner_id,is_workspace",
            "limit=1",
        ]
    )
    trows = sb.rest_select("threads", q_thread, access_token)
    if not trows:
        return 0
    thread = trows[0]
    is_workspace = bool(thread.get("is_workspace"))
    owner_id = thread.get("owner_id")

    # Permission: owner OR (workspace and member)
    if not is_workspace and owner_id != user_id:
        return 0
    if is_workspace and not _can_access_thread(user_id, thread_id, access_token):
        return 0

    # Delete messages and members first for cleanliness (RLS permitting)
    try:
        sb.rest_delete("messages", f"thread_id=eq.{quote(thread_id)}", access_token)
    except Exception:
        pass
    try:
        sb.rest_delete("thread_members", f"thread_id=eq.{quote(thread_id)}", access_token)
    except Exception:
        pass

    deleted = sb.rest_delete("threads", f"id=eq.{quote(thread_id)}", access_token)
    return deleted

# 스레드 상세 조회
def get_thread_detail(owner_id: str, thread_id: str, access_token: str) -> Dict[str, Any]:
    if not _can_access_thread(owner_id, thread_id, access_token):
        return {}

    q = "&".join([
        f"id=eq.{quote(thread_id)}",
        "select=" + ",".join([
            "id", "title", "created_at",
            "messages(index,role,content,created_at)"
        ]),
        "messages.order=index.asc",
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
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, [])

    order = "asc" if str(order).lower() != "desc" else "desc"

    q_msgs = "&".join([
        f"thread_id=eq.{quote(thread_id)}",
        "select=index,role,content,created_at",
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
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, 0)

    now = datetime.now(timezone.utc).isoformat()

    rows = []
    for m in messages:
        content = (m.get("content") or "").strip()
        if not content:
            raise ValueError("Message content cannot be empty")

        rows.append({
            "thread_id": thread_id,
            "role": _normalize_role(m.get("role", "")),
            "content": content,
            "created_at": now,
        })

    sb.rest_insert("messages", rows, access_token)
    return (True, len(rows))


def _get_max_index(thread_id: str, access_token: str) -> int:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "select=index",
                "order=index.desc",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        return -1
    try:
        return int(rows[0].get("index", -1))
    except Exception:
        return -1


def insert_and_fetch_message(
    thread_id: str,
    role: str,
    content: str,
    access_token: str,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    last_idx = _get_max_index(thread_id, access_token)
    new_index = last_idx + 1
    sb.rest_insert(
        "messages",
        [
            {
                "thread_id": thread_id,
                "role": role,
                "content": content.strip(),
                "index": new_index,
                "created_at": now,
            }
        ],
        access_token,
    )
    # Fetch back deterministically
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                f"index=eq.{new_index}",
                "select=index,role,content,created_at",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        raise RuntimeError("Inserted message not found")
    row = rows[0]
    row["index"] = int(row.get("index", new_index))
    return row


def list_recent_messages(thread_id: str, limit: int, access_token: str) -> List[Dict[str, Any]]:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "select=index,role,content,created_at",
                "order=index.desc",
                f"limit={limit}",
            ]
        ),
        access_token,
    )
    return rows


def list_messages_before_index(thread_id: str, before_index: int, limit: int, access_token: str) -> List[Dict[str, Any]]:
    """
    Fetch messages with index < before_index ordered desc, limited.
    """
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                f"index=lt.{before_index}",
                "select=index,role,content,created_at",
                "order=index.desc",
                f"limit={limit}",
            ]
        ),
        access_token,
    )
    return rows


def get_first_assistant_message(thread_id: str, access_token: str) -> Dict[str, Any] | None:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "role=eq.assistant",
                "select=index,role,content",
                "order=index.asc",
                "limit=1",
            ]
        ),
        access_token,
    )
    return rows[0] if rows else None


async def chat_with_llm(
    owner_id: str,
    thread_id: str,
    content: str,
    model: str,
    context_limit: int,
    access_token: str,
) -> Dict[str, Any]:
    """
    Insert user message, call LLM, insert assistant message, and return summary.
    """
    # Ownership check
    q_check = "&".join(
        [
            f"id=eq.{quote(thread_id)}",
            f"owner_id=eq.{quote(owner_id)}",
            "select=id",
            "limit=1",
        ]
    )
    trows = sb.rest_select("threads", q_check, access_token)
    if not trows:
        return {}

    now = datetime.now(timezone.utc).isoformat()
    # 1) Insert user message
    user_row = insert_and_fetch_message(thread_id, "user", content, access_token)
    incoming = content.strip()
    saved = (user_row.get("content") or "").strip()
    if saved != incoming and settings.CHAT_DEBUG_ASSERTS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "code": "CHAT_INCOMING_MISMATCH",
                "incoming": incoming[:60],
                "saved": saved[:60],
                "inserted_index": user_row.get("index"),
            },
        )

    # 2) Fetch recent messages for context (including the new one) AFTER insert
    recent_desc = list_recent_messages(thread_id, context_limit, access_token)
    chron = list(reversed(recent_desc))  # to chronological order
    llm_messages = [
        {"role": m.get("role", "assistant"), "content": m.get("content", ""), "index": int(m.get("index", 0))}
        for m in chron
    ]

    if settings.CHAT_DEBUG_ASSERTS:
        indices = [m["index"] for m in llm_messages]
        if user_row.get("index") not in indices:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "CHAT_CONTEXT_MISSING_INSERTED",
                    "inserted_index": user_row.get("index"),
                    "first": indices[0] if indices else None,
                    "last": indices[-1] if indices else None,
                    "count": len(indices),
                },
            )
        last_user = next((m for m in reversed(llm_messages) if m.get("role") == "user"), None)
        if last_user:
            if (last_user.get("content") or "").strip() != incoming:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "CHAT_LAST_USER_WRONG",
                        "incoming": incoming[:60],
                        "last_user_index": last_user.get("index"),
                        "last_user_preview": (last_user.get("content") or "")[:60],
                        "chron_first": (
                            llm_messages[0]["index"],
                            llm_messages[0]["role"],
                            (llm_messages[0]["content"] or "")[:30],
                        )
                        if llm_messages
                        else None,
                        "chron_last": (
                            llm_messages[-1]["index"],
                            llm_messages[-1]["role"],
                            (llm_messages[-1]["content"] or "")[:30],
                        )
                        if llm_messages
                        else None,
                    },
                )
        else:
            raise HTTPException(
                status_code=500,
                detail={"code": "CHAT_NO_USER_IN_CONTEXT", "incoming": incoming[:60]},
            )

    if settings.APP_ENV in ("dev", "local"):
        last_user = next((m for m in reversed(llm_messages) if m.get("role") == "user"), None)
        logger.info(
            "[chat] context debug",
            extra={
                "thread_id": thread_id,
                "requested_content_preview": content[:60],
                "requested_content_len": len(content),
                "inserted_user_index": user_row.get("index"),
                "context_limit": context_limit,
                "fetched_count": len(recent_desc),
                "first_msg": {
                    "index": llm_messages[0].get("index") if llm_messages else None,
                    "role": llm_messages[0].get("role") if llm_messages else None,
                    "preview": (llm_messages[0].get("content") or "")[:20] if llm_messages else None,
                },
                "last_msg": {
                    "index": llm_messages[-1].get("index") if llm_messages else None,
                    "role": llm_messages[-1].get("role") if llm_messages else None,
                    "preview": (llm_messages[-1].get("content") or "")[:20] if llm_messages else None,
                },
                "last_user": {
                    "index": last_user.get("index") if isinstance(last_user, dict) else None,
                    "preview": last_user.get("content")[:40] if isinstance(last_user, dict) and last_user.get("content") else None,
                }
            },
        )

    # 3) Call LLM server (with fallback)
    payload_messages = [{"role": m["role"], "content": m["content"]} for m in llm_messages]
    if settings.CHAT_DEBUG_ASSERTS:
        if payload_messages[-1]["content"].strip() != incoming:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={"code": "CHAT_PAYLOAD_LAST_USER_MISMATCH", "incoming": incoming[:60]},
            )

    # Pre-LLM debug logging
    if settings.APP_ENV in ("dev", "local"):
        logger.info(
            "[chat] pre-llm",
            extra={
                "incoming_preview": incoming[:40],
                "last_user_preview": (last_user.get("content") or "")[:40] if "last_user" in locals() and last_user else None,
                "chron_first_preview": (llm_messages[0]["content"] or "")[:40] if llm_messages else None,
                "chron_last_preview": (llm_messages[-1]["content"] or "")[:40] if llm_messages else None,
                "first_index": llm_messages[0]["index"] if llm_messages else None,
                "last_index": llm_messages[-1]["index"] if llm_messages else None,
            },
        )

    assistant_content = await llm_client.generate(
        model=model,
        messages=payload_messages,
    )

    assistant_row = insert_and_fetch_message(thread_id, "assistant", assistant_content, access_token)
    saved_assistant = (assistant_row.get("content") or "").strip()
    if saved_assistant != assistant_content.strip() and settings.CHAT_DEBUG_ASSERTS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ASSISTANT_SAVE_MISMATCH",
                "assistant_preview": assistant_content[:80],
                "saved_preview": saved_assistant[:80],
                "assistant_index": assistant_row.get("index"),
            },
        )

    first_asst = get_first_assistant_message(thread_id, access_token)
    if (
        first_asst
        and assistant_row.get("index") != first_asst.get("index")
        and saved_assistant == (first_asst.get("content") or "").strip()
    ):
        logger.warning(
            "ASSISTANT_EQUALS_FIRST",
            extra={
                "thread_id": thread_id,
                "current_index": assistant_row.get("index"),
                "first_index": first_asst.get("index"),
            },
        )

    if settings.APP_ENV in ("dev", "local"):
        # Warn if echo
        if assistant_content.strip() == incoming.strip():
            logger.warning("[chat] assistant echoed user content", extra={"incoming_preview": incoming[:80]})

    return {
        "thread_id": thread_id,
        "user_content": content,
        "assistant_content": saved_assistant,
        "assistant_index": assistant_row.get("index"),
        "status": "saved",
    }

    assistant_index = user_index + 1
    sb.rest_insert(
        "messages",
        [
            {
                "thread_id": thread_id,
                "role": "assistant",
                "content": assistant_content,
                "index": assistant_index,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        access_token,
    )

    return {
        "thread_id": thread_id,
        "user_content": content,
        "assistant_content": assistant_content,
        "assistant_index": assistant_index,
        "status": "saved",
    }
