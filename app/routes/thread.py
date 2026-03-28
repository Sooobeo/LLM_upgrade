from __future__ import annotations

from typing import Any, Dict, List
import requests
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query

from app.db import supabase as sb
from app.db.deps import get_access_token, get_current_user
from app.db.supabase_users import get_user_id_by_email, get_users_by_ids
from app.repository.thread import (
    add_messages_to_thread,
    create_thread_with_messages,
    delete_thread_by_id,
    get_thread_detail,
    list_thread_messages,
    list_threads_for_owner,
    insert_and_fetch_message,
    list_recent_messages,
    list_messages_before_index,
)
from app.schemas.thread import (
    AddMessagesBody,
    AddMessagesResp,
    MessagesResp,
    ThreadCreate,
    ThreadCreateResp,
    ThreadDetailResp,
    ThreadsListResp,
    ChatRequest,
    ChatResponse,
)
from app.schemas.workspace import WorkspaceCreatedOut, WorkspaceMembersIn
from app.services import llm_client
from app.services.llm_client import LLMUpstreamError
from app.core.config import settings

router = APIRouter(prefix="/threads", tags=["threads"])


def _is_echo(text: str, user_text: str) -> bool:
    import re

    def norm(s: str) -> str:
        return re.sub(r"\W+", "", (s or "").lower())

    return norm(text) == norm(user_text) or norm(user_text) and norm(user_text) in norm(text)


@router.post("", response_model=ThreadCreateResp, status_code=200)
def create_thread(
    body: ThreadCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        payload = {
            "title": body.title,
            "messages": [{"role": m.role, "content": m.content} for m in body.messages],
        }
        thread_id = create_thread_with_messages(owner_id, payload, access_token)
        return {"thread_id": thread_id, "status": "saved"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}")


@router.get("", response_model=ThreadsListResp)
def get_threads(
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = list_threads_for_owner(
            owner_id=owner_id,
            access_token=access_token,
            limit=limit,
            offset=offset,
            order=order,
        )
        return {"threads": rows}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_QUERY_FAILED", "message": "Failed to fetch threads from Supabase"},
        )


@router.delete("/{thread_id}")
def delete_thread(
    thread_id: str = Path(..., min_length=10),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        current_id = user.get("id")
        if not current_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        deleted = delete_thread_by_id(current_id, thread_id, access_token)

        if deleted == 0:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Thread not found"},
            )

        return {"ok": True}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_DELETE_FAILED", "message": "Failed to delete thread"},
        )


@router.get("/{thread_id}", response_model=ThreadDetailResp)
def get_thread_by_id(
    thread_id: str = Path(..., min_length=10),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        data = get_thread_detail(owner_id, thread_id, access_token)
        if not data:
            # Ownership mismatch or missing thread is treated as 404
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Thread not found"})
        return data

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_FETCH_FAILED", "message": "Failed to retrieve thread or messages"},
        )


@router.get("/{thread_id}/messages", response_model=MessagesResp)
def get_thread_messages(
    thread_id: str = Path(..., min_length=10),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Missing or invalid access token"},
            )

        owned, rows = list_thread_messages(
            owner_id=owner_id,
            thread_id=thread_id,
            access_token=access_token,
            limit=limit,
            offset=offset,
            order=order,
        )
        if not owned:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Thread not found"})

        return {"messages": rows}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail={"code": "DB_FETCH_FAILED", "message": "Failed to fetch messages"})


@router.post("/{thread_id}/messages", response_model=AddMessagesResp, status_code=200)
def add_messages(
    thread_id: str = Path(..., min_length=10),
    body: AddMessagesBody = Body(...),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Missing or invalid access token"},
            )

        # Prevent empty/whitespace-only messages slipping past validation
        for message in body.messages:
            if not message.content.strip():
                raise HTTPException(
                    status_code=422,
                    detail={"code": "VALIDATION_ERROR", "message": "Message content cannot be empty"},
                )

        owned, added = add_messages_to_thread(
            owner_id=owner_id,
            thread_id=thread_id,
            messages=[{"role": m.role, "content": m.content} for m in body.messages],
            access_token=access_token,
        )

        if not owned:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Thread not found"})

        return {"thread_id": thread_id, "added_count": added, "status": "saved"}

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(exc)})
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_INSERT_FAILED", "message": "Failed to insert messages into Supabase"},
        )

@router.post("/{thread_id}/workspace", response_model=WorkspaceCreatedOut)
def convert_to_workspace(
    thread_id: str = Path(..., min_length=10),
    payload: WorkspaceMembersIn = Body(...),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """
    Convert a thread to a workspace and add members by email.
    """
    owner_id = user.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 1) Load thread and verify ownership
    q_thread = "&".join(
        [
            f"id=eq.{quote(thread_id)}",
            "select=id,owner_id,is_workspace",
            "limit=1",
        ]
    )
    rows = sb.rest_select("threads", q_thread, access_token)
    if not rows:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread = rows[0]
    if thread.get("owner_id") != owner_id:
        raise HTTPException(status_code=403, detail="Only the owner can convert to workspace.")

    # 2) Mark as workspace (RLS-enforced via caller token)
    sb.rest_update("threads", f"id=eq.{quote(thread_id)}", {"is_workspace": True}, access_token)

    # 3) Existing members to avoid duplicates
    member_rows = sb.rest_select(
        "thread_members", f"thread_id=eq.{quote(thread_id)}&select=user_id", access_token
    )
    existing_ids = {m.get("user_id") for m in member_rows if m.get("user_id")}

    rows_to_add: List[Dict[str, Any]] = []
    added: List[str] = []
    not_found: List[str] = []

    # Ensure owner is present
    if owner_id not in existing_ids:
        rows_to_add.append({"thread_id": thread_id, "user_id": owner_id, "role": "owner"})
        existing_ids.add(owner_id)

    # Add members by email lookup
    for email in payload.emails:
        try:
            uid = get_user_id_by_email(email)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        if not uid:
            not_found.append(email)
            continue
        if uid in existing_ids:
            added.append(email)
            continue
        rows_to_add.append({"thread_id": thread_id, "user_id": uid, "role": "member"})
        existing_ids.add(uid)
        added.append(email)

    if rows_to_add:
        try:
            sb.rest_insert("thread_members", rows_to_add, access_token)
        except requests.HTTPError as exc:
            # Ignore conflict duplicates; re-raise others.
            if not exc.response or exc.response.status_code != 409:
                raise

    return {
        "thread_id": thread_id,
        "is_workspace": True,
        "added_members": added,
        "not_found": not_found,
    }


@router.get("/{thread_id}/members")
def list_thread_members(
    thread_id: str = Path(..., min_length=10),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """
    List members of a workspace (owner or member can view).
    """
    current_user_id = user.get("id")
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Check ownership/membership
    q_thread = "&".join([f"id=eq.{quote(thread_id)}", "select=owner_id", "limit=1"])
    thread_rows = sb.rest_select("threads", q_thread, access_token)
    if not thread_rows:
        raise HTTPException(status_code=404, detail="Thread not found")
    is_owner = thread_rows[0].get("owner_id") == current_user_id
    if not is_owner:
        q_member = f"thread_id=eq.{quote(thread_id)}&user_id=eq.{quote(current_user_id)}&select=id&limit=1"
        membership = sb.rest_select("thread_members", q_member, access_token)
        if not membership:
            raise HTTPException(status_code=403, detail="Not allowed")

    members = sb.rest_select(
        "thread_members",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "select=user_id,role,created_at",
                "order=created_at.asc",
            ]
        ),
        access_token,
    )
    ids = [m.get("user_id") for m in members if m.get("user_id")]
    user_map = get_users_by_ids(ids) if ids else {}
    for m in members:
        uid = m.get("user_id")
        m["email"] = user_map.get(uid, {}).get("email")
    return members


@router.post("/{thread_id}/chat", response_model=ChatResponse, status_code=200)
async def chat_with_thread(
    thread_id: str = Path(..., min_length=10),
    body: ChatRequest = Body(...),
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    owner_id = user.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    incoming = (body.content or "").strip()
    if not incoming:
        raise HTTPException(status_code=422, detail="content is required")
    model = body.model or settings.LLM_MODEL
    context_limit = body.context_limit or 50
    context_limit = max(1, min(200, context_limit))

    # 1) Persist incoming user message (dedupe first-turn duplicate posts)
    recent_desc = list_recent_messages(thread_id, 2, access_token)
    latest = recent_desc[0] if recent_desc else None
    latest_role = str((latest or {}).get("role") or "").lower() if latest else ""
    latest_content = ((latest or {}).get("content") or "").strip() if latest else ""
    has_recent_assistant = any(((m.get("role") or "").lower() == "assistant") for m in recent_desc)
    if latest and latest_role == "user" and latest_content == incoming and not has_recent_assistant:
        try:
            latest_index = int(latest.get("index", 0))
        except Exception:
            latest_index = 0
        user_row = {
            "index": latest_index,
            "role": "user",
            "content": latest_content,
            "created_at": latest.get("created_at") or "",
        }
    else:
        user_row = insert_and_fetch_message(thread_id, "user", incoming, access_token)

    # 2) Build context in memory
    prior_limit = max(0, context_limit - 1)
    before_rows = list_messages_before_index(thread_id, int(user_row.get("index", 0)), prior_limit, access_token)
    chron = list(reversed(before_rows)) + [user_row]

    if settings.CHAT_DEBUG_ASSERTS:
        indices = [m.get("index") for m in chron]
        if user_row.get("index") not in indices:
            raise HTTPException(
                status_code=500,
                detail={"code": "CHAT_CONTEXT_MISSING_INSERTED", "inserted_index": user_row.get("index")},
            )
        last_user = next((m for m in reversed(chron) if m.get("role") == "user"), None)
        if not last_user or (last_user.get("content") or "").strip() != incoming:
            raise HTTPException(
                status_code=500,
                detail={"code": "CHAT_LAST_USER_WRONG", "incoming": incoming[:60]},
            )

    payload_messages = [{"role": m.get("role"), "content": m.get("content")} for m in chron]
    if not any((m.get("role") or "").lower() == "system" for m in payload_messages):
        payload_messages = [
            {"role": "system", "content": settings.LLM_SYSTEM_PROMPT + " Never repeat the user's question; answer directly."}
        ] + payload_messages

    try:
        assistant_content = await llm_client.generate(model=model, messages=payload_messages)
        # If the model echoed the user, retry once with a stricter instruction.
        if _is_echo(assistant_content, incoming):
            payload_messages.append(
                {
                    "role": "system",
                    "content": "Do not repeat the user's question. Provide a concise answer now.",
                }
            )
            assistant_content = await llm_client.generate(model=model, messages=payload_messages)
    except LLMUpstreamError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": exc.code or "LLM_FAILED",
                "message": str(exc),
                "provider": exc.provider,
                "status": exc.status,
            },
        )

    if not assistant_content or not assistant_content.strip():
        raise HTTPException(
            status_code=502,
            detail={"code": "EMPTY_COMPLETION", "message": "LLM returned empty completion"},
        )

    assistant_row = insert_and_fetch_message(thread_id, "assistant", assistant_content, access_token)

    return {
        "thread_id": thread_id,
        "user_content": incoming,
        "assistant_content": assistant_row.get("content"),
        "assistant_index": assistant_row.get("index"),
        "status": "saved",
    }
