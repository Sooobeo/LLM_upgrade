# app/routes/message.py
from __future__ import annotations
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.deps import get_current_user
from app.repository.thread import search_messages_by_owner

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
def search_my_messages(
    q: Optional[str] = Query(None, description="메시지 내용 부분 검색어"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    asc: bool = Query(False, description="True면 created_at 오름차순"),
    user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    현재 로그인한 사용자의 **모든 threads**에 속한 messages를 조회/검색하는 API.

    - q: 선택. content에 q가 포함된 메시지만 필터
    - limit, offset: 페이징
    - asc: True 이면 created_at 오름차순, 기본 False(내림차순)
    """
    owner_id = user.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        data = search_messages_by_owner(
            owner_id=owner_id,
            q=q,
            limit=limit,
            offset=offset,
            asc=asc,
        )
        # 그대로 리스트 반환. 필요하면 {"messages": data} 식으로 한번 감싸도 됨
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"search_messages_by_owner failed: {e}",
        )
