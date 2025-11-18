
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from fastapi import Path, Body
from app.db.deps import get_current_user, get_access_token
from app.schemas.thread import (
    ThreadCreate, ThreadCreateResp,
    ThreadsListResp, ThreadDetailResp, MessagesResp, AddMessagesBody, AddMessagesResp
)
from app.repository.thread import (
    create_thread_with_messages, list_threads_for_owner, get_thread_detail,delete_thread_by_id, list_thread_messages, add_messages_to_thread
)

router = APIRouter(prefix="/threads", tags=["threads"])

# POST /threads
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

# GET /threads
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
            # 소유 아님/미존재 → RLS 하에선 동일하게 보이므로 404 처리
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Thread not found"},
            )
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
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing or invalid access token"})

        owned, rows = list_thread_messages(
            owner_id=owner_id,
            thread_id=thread_id,
            access_token=access_token,
            limit=limit,
            offset=offset,
            order=order,
        )
        if not owned:
            # 소유 아님/존재하지 않음 → RLS 환경에선 동일하게 보이므로 404로 일괄 처리
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
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing or invalid access token"})

        # 내용 공백 방지(422): pydantic에 걸리지만 방어적으로 한 번 더
        for m in body.messages:
            if not m.content.strip():
                raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Message content cannot be empty"})

        owned, added = add_messages_to_thread(
            owner_id=owner_id,
            thread_id=thread_id,
            messages=[{"role": m.role, "content": m.content} for m in body.messages],
            access_token=access_token,
        )

        if not owned:
            # 남의 스레드 or 미존재 → RLS 하에선 동일하게 404
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Thread not found"})

        return {"thread_id": thread_id, "added_count": added, "status": "saved"}

    except HTTPException:
        raise
    except ValueError as ve:
        # repository에서 content 공백 등으로 올린 검증 오류
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(ve)})
    except Exception:
        raise HTTPException(status_code=500, detail={"code": "DB_INSERT_FAILED", "message": "Failed to insert messages into Supabase"})
    


from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from fastapi import Path, Body
from app.db.deps import get_current_user, get_access_token
from app.schemas.thread import (
    ThreadCreate, ThreadCreateResp,
    ThreadsListResp, ThreadDetailResp, MessagesResp, AddMessagesBody, AddMessagesResp
)
from app.repository.thread import (
    create_thread_with_messages, list_threads_for_owner, get_thread_detail, delete_thread_by_id,
    list_thread_messages, add_messages_to_thread
)

router = APIRouter(prefix="/threads", tags=["threads"])


# POST /threads
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


# GET /threads  (진짜 인증 버전)
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


# 🔽🔽🔽 여기부터 추가: 인증 없이 열어둔 dev용 엔드포인트 🔽🔽🔽
@router.get("/dev-open", response_model=ThreadsListResp, tags=["threads-dev"])
def get_threads_dev_open(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """
    개발용/프론트 연동용 엔드포인트.

    - get_current_user, get_access_token 의존성 없이 동작
    - 지금은 Supabase에 실제로 접근하지 않고, 빈 리스트 또는 샘플 데이터를 반환
    - 프론트에서 UI 흐름(목록 → 상세)만 먼저 붙이는 용도
    - 나중에 진짜 인증 붙이면 이 엔드포인트는 삭제하거나 /threads와 통합
    """

    # TODO: 필요하면 여기에 샘플 데이터 몇 개 넣어도 됨
    # 예시:
    # rows = [
    #     {"id": "dev-thread-1", "title": "테스트 스레드 1", "created_at": "2025-11-18T12:00:00"},
    #     {"id": "dev-thread-2", "title": "테스트 스레드 2", "created_at": "2025-11-18T13:00:00"},
    # ]
    rows = []

    return {"threads": rows}
# 🔼🔼🔼 추가 끝 🔼🔼🔼


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

# ... 이하 나머지 get_thread_by_id, get_thread_messages, add_messages 그대로 유지 ...
