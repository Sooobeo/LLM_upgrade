from __future__ import annotations

from typing import Any, Dict, List
import requests
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query

from app.db import supabase as sb
from app.db.deps import get_access_token, get_current_user
from app.db.supabase_users import get_user_id_by_email
from app.repository.thread import (
    add_messages_to_thread,
    create_thread_with_messages,
    delete_thread_by_id,
    get_thread_detail,
    list_thread_messages,
    list_threads_for_owner,
)
from app.schemas.thread import (
    AddMessagesBody,
    AddMessagesResp,
    MessagesResp,
    ThreadCreate,
    ThreadCreateResp,
    ThreadDetailResp,
    ThreadsListResp,
)
from app.schemas.workspace import WorkspaceCreatedOut, WorkspaceMembersIn

router = APIRouter(prefix="/threads", tags=["threads"])


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
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        deleted = delete_thread_by_id(owner_id, thread_id, access_token)

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
    return members
