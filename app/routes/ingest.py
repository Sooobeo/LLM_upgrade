from __future__ import annotations
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException

from app.db.deps import get_current_user, get_access_token
from app.schemas.thread import ThreadCreate, ThreadCreateResp
from app.repository.thread import create_thread_with_messages

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=ThreadCreateResp, status_code=200)
def ingest_thread(
    body: ThreadCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """
    Thin wrapper:
    - body: ThreadCreate (title + messages[])
    - owner_id는 FE가 안 보내고, 로그인 유저 id로 서버에서 채움
    - 내부적으로는 create_thread_with_messages() 재사용
    """
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        payload = {
            "title": body.title,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in body.messages
            ],
        }

        thread_id = create_thread_with_messages(
            owner_id=owner_id,
            payload=payload,
            access_token=access_token,
        )
        return {"thread_id": thread_id, "status": "saved"}

    except HTTPException:
        # 인증/권한 에러는 그대로 다시 던짐
        raise
    except Exception as e:
        # 나머지는 500으로 래핑
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {e}",
        )
