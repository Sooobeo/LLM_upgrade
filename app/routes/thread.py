
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from fastapi import Path, Body
from app.db.deps import get_current_user, get_access_token
from app.schemas.thread import (
    ThreadCreate, ThreadCreateResp,
    ThreadsListResp, ThreadDetailResp, MessagesResp, AddMessagesBody, AddMessagesResp
)
from app.repository.thread import (
    create_thread_with_messages, list_threads_for_owner, get_thread_detail,delete_thread_by_id, list_thread_messages, add_messages_to_thread
)
from app.services.llm import call_llm_chat
router = APIRouter(prefix="/threads", tags=["threads"])

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

    # 👇 새로 추가: LLM 옵션
    with_llm: bool = Query(
        False,
        description="True면 LLM(GPT/Gemini) 답변을 자동으로 이어서 추가",
    ),
    provider: str = Query(
        "gpt",
        pattern="^(gpt|gemini)$",
        description="사용할 LLM 제공자: gpt 또는 gemini",
    ),
    model_name: str | None = Query(
        None,
        description="선택: 사용할 모델 이름(없으면 settings의 기본값)",
    ),
):
    try:
        owner_id = user.get("id")
        if not owner_id:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Missing or invalid access token"},
            )

        # 내용 공백 방지(422): pydantic에서도 걸리지만 한 번 더 확인
        for m in body.messages:
            if not m.content.strip():
                raise HTTPException(
                    status_code=422,
                    detail={"code": "VALIDATION_ERROR", "message": "Message content cannot be empty"},
                )

        # 1) 먼저 유저 메시지들을 DB에 저장
        owned, added = add_messages_to_thread(
            owner_id=owner_id,
            thread_id=thread_id,
            messages=[{"role": m.role, "content": m.content} for m in body.messages],
            access_token=access_token,
        )

        if not owned:
            # 남의 스레드 or 미존재 → 404
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Thread not found"},
            )

        total_added = added

        # 2) 옵션: LLM 호출로 assistant 답변 자동 이어 붙이기
        if with_llm:
            # 스레드 전체 메시지를 가져와서 LLM 컨텍스트로 사용
            detail = get_thread_detail(owner_id, thread_id, access_token)
            if not detail:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "NOT_FOUND", "message": "Thread not found"},
                )

            history_msgs = detail.get("messages", []) or []

            # LLM용 messages 배열 구성
            llm_messages: List[Dict[str, str]] = []

            # system 프롬프트 예시 (원하는 내용으로 수정 가능)
            llm_messages.append({
                "role": "system",
                "content": "너는 CareOn 서비스의 상담 챗봇이야. "
                           "사용자의 질문에 친절하게 한국어로 답변해줘.",
            })

            # 기존 대화 히스토리 추가
            for m in history_msgs:
                role = m.get("role") or "assistant"
                content = m.get("content") or ""
                llm_messages.append({"role": role, "content": content})

            # LLM 호출
            try:
                reply_text = call_llm_chat(
                    provider="gemini" if provider == "gemini" else "gpt",
                    messages=llm_messages,
                    model_name=model_name,
                )
            except Exception as e:
                # LLM 실패해도 전체 API가 죽지 않게 하고 싶으면 여기서 그냥 로그만 찍고 넘어가도 됨
                raise HTTPException(
                    status_code=500,
                    detail={"code": "LLM_ERROR", "message": f"LLM call failed: {e}"},
                )

            if reply_text.strip():
                # 3) LLM reply도 assistant 메시지로 같은 thread에 저장
                _, added_ai = add_messages_to_thread(
                    owner_id=owner_id,
                    thread_id=thread_id,
                    messages=[{"role": "assistant", "content": reply_text}],
                    access_token=access_token,
                )
                total_added += added_ai

        return {"thread_id": thread_id, "added_count": total_added, "status": "saved"}

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": str(ve)},
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_INSERT_FAILED", "message": "Failed to insert messages into Supabase"},
        )