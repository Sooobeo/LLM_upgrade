from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.comment import (
    BranchCommentCreate,
    BranchCommentResponse,
    BranchCommentUpdate,
    CommentCreate,
)
from app.repository.comment import (
    BranchCommentForbiddenError,
    BranchCommentNotFoundError,
    CommentRepository,
    create_branch_comment,
    delete_branch_comment,
    list_branch_comments,
    update_branch_comment,
)
from app.db.supabase import get_supabase
from app.db.deps import get_access_token, get_current_user

router = APIRouter(prefix="/threads", tags=["comments"])
branch_router = APIRouter(prefix="/branch-comments", tags=["branch-comments"])


def _owner_id(user) -> str:
    owner_id = user.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return owner_id


@branch_router.get("", response_model=List[BranchCommentResponse])
def get_branch_comments(
    thread_id: List[UUID] = Query(..., min_length=1, max_length=100),
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    owner_id = _owner_id(user)
    comments = list_branch_comments(
        owner_id,
        [str(value) for value in thread_id],
        access_token,
    )
    for comment in comments:
        comment["can_edit"] = comment["user_id"] == owner_id
    return comments


@branch_router.post(
    "",
    response_model=BranchCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_branch_comment(
    body: BranchCommentCreate,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        comment = create_branch_comment(
            _owner_id(user),
            body.thread_id,
            body.content,
            body.position_x,
            body.position_y,
            access_token,
            author_id=user.get("email") or user.get("id"),
        )
        comment["can_edit"] = True
        return comment
    except BranchCommentForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "BRANCH_COMMENT_FORBIDDEN",
                "message": "You can only comment on your own branch nodes.",
            },
        )
    except BranchCommentNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "BRANCH_COMMENT_SAVE_FAILED",
                "message": "The comment was not saved.",
            },
        )


@branch_router.patch("/{comment_id}", response_model=BranchCommentResponse)
def edit_branch_comment(
    comment_id: UUID,
    body: BranchCommentUpdate,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        comment = update_branch_comment(
            _owner_id(user),
            str(comment_id),
            access_token,
            content=body.content,
            position_x=body.position_x,
            position_y=body.position_y,
        )
        comment["can_edit"] = True
        return comment
    except BranchCommentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BRANCH_COMMENT_NOT_FOUND",
                "message": "Comment not found.",
            },
        )


@branch_router.delete("/{comment_id}")
def remove_branch_comment(
    comment_id: UUID,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    if not delete_branch_comment(
        _owner_id(user),
        str(comment_id),
        access_token,
    ):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BRANCH_COMMENT_NOT_FOUND",
                "message": "Comment not found.",
            },
        )
    return {"ok": True}


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
