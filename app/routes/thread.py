from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query

from app.db.deps import get_access_token, get_current_user
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
