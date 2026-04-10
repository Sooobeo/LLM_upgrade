from fastapi import APIRouter, Depends, HTTPException
from app.schemas.comment import CommentCreate
from app.repository.comment import CommentRepository
from app.db.supabase import get_supabase
from app.db.deps import get_current_user

router = APIRouter(prefix="/threads", tags=["comments"])


@router.post("/{thread_id}/comments")
def create_comment(
    thread_id: str,
    body: CommentCreate,
    supabase=Depends(get_supabase),
    user=Depends(get_current_user),
):
    repo = CommentRepository(supabase)

    comment = repo.create_comment(
        thread_id=thread_id,
        user_id=user["id"],
        message_index=body.message_index,
        content=body.content,
    )

    if not comment:
        raise HTTPException(status_code=400, detail="코멘트 생성 실패")

    return comment


@router.get("/{thread_id}/comments")
def get_comments(
    thread_id: str,
    message_index: int,
    supabase=Depends(get_supabase),
):
    repo = CommentRepository(supabase)

    return repo.get_comments(thread_id, message_index)


@router.delete("/{thread_id}/comments/{comment_id}")
def delete_comment(
    thread_id: str,
    comment_id: str,
    supabase=Depends(get_supabase),
    user=Depends(get_current_user),
):
    repo = CommentRepository(supabase)

    result = repo.delete_comment(comment_id, user["id"])

    if not result:
        raise HTTPException(status_code=404, detail="코멘트를 찾을 수 없음")

    return {"message": "삭제 완료"}