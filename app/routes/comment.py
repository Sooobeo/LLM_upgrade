from typing import List
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.comment import (
    BranchCommentCreate,
    BranchCommentResponse,
    BranchCommentUpdate,
    BranchPositionResponse,
    BranchPositionUpdate,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
)
from app.repository.comment import (
    BRANCH_NODE_POSITION_MESSAGE_INDEX,
    BranchCommentForbiddenError,
    BranchCommentNotFoundError,
    create_branch_comment,
    delete_branch_positions,
    delete_branch_comment,
    list_branch_positions,
    list_branch_comments,
    save_branch_position,
    update_branch_comment,
    _accessible_thread_ids,
)
from app.db import supabase as sb
from app.db.deps import get_access_token, get_current_user
from app.db.supabase_users import get_users_by_ids

router = APIRouter(prefix="/threads", tags=["comments"])
branch_router = APIRouter(prefix="/branch-comments", tags=["branch-comments"])
position_router = APIRouter(
    prefix="/branch-positions",
    tags=["branch-positions"],
)


def _owner_id(user) -> str:
    owner_id = user.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return owner_id


def _email_id(email: object) -> str:
    if not isinstance(email, str):
        return ""
    normalized = email.strip()
    if not normalized:
        return ""
    return normalized.split("@", 1)[0] if "@" in normalized else normalized


def _author_id(user) -> str:
    return _email_id(user.get("email")) or "사용자"


def _normalize_comment_authors(comments, user) -> None:
    current_user_id = _owner_id(user)
    current_author_id = _author_id(user)
    other_user_ids = list(
        {
            str(comment.get("user_id"))
            for comment in comments
            if comment.get("user_id")
            and str(comment.get("user_id")) != current_user_id
        }
    )
    try:
        user_map = get_users_by_ids(other_user_ids) if other_user_ids else {}
    except Exception:
        # New comments already carry the display id in their encoded payload.
        # Keep listing available if the optional admin lookup is unavailable.
        user_map = {}

    for comment in comments:
        user_id = str(comment.get("user_id") or "")
        if user_id == current_user_id:
            comment["author_id"] = current_author_id
            continue
        email = user_map.get(user_id, {}).get("email")
        resolved = _email_id(email)
        stored = str(comment.get("author_id") or "")
        comment["author_id"] = resolved or (
            stored if stored and stored != user_id else "사용자"
        )


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
    _normalize_comment_authors(comments, user)
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
            author_id=_author_id(user),
        )
        comment["can_edit"] = True
        return comment
    except BranchCommentForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "BRANCH_COMMENT_FORBIDDEN",
                "message": "접근할 수 있는 브랜치 노드에만 코멘트를 작성할 수 있습니다.",
            },
        )
    except BranchCommentNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "BRANCH_COMMENT_SAVE_FAILED",
                "message": "코멘트를 저장하지 못했습니다.",
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
            author_id=_author_id(user),
        )
        comment["can_edit"] = True
        return comment
    except BranchCommentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BRANCH_COMMENT_NOT_FOUND",
                "message": "코멘트를 찾을 수 없습니다.",
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
                "message": "코멘트를 찾을 수 없습니다.",
            },
        )
    return {"ok": True}


@position_router.get("", response_model=List[BranchPositionResponse])
def get_branch_positions(
    thread_id: List[UUID] = Query(..., min_length=1, max_length=100),
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    return list_branch_positions(
        _owner_id(user),
        [str(value) for value in thread_id],
        access_token,
    )


@position_router.put("/{thread_id}", response_model=BranchPositionResponse)
def put_branch_position(
    thread_id: UUID,
    body: BranchPositionUpdate,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        return save_branch_position(
            _owner_id(user),
            str(thread_id),
            body.position_x,
            body.position_y,
            access_token,
        )
    except BranchCommentForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "BRANCH_POSITION_FORBIDDEN",
                "message": "접근할 수 있는 브랜치의 위치만 저장할 수 있습니다.",
            },
        )
    except BranchCommentNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "BRANCH_POSITION_SAVE_FAILED",
                "message": "브랜치 위치를 저장하지 못했습니다.",
            },
        )


@position_router.delete("")
def reset_branch_positions(
    thread_id: List[UUID] = Query(..., min_length=1, max_length=100),
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    try:
        deleted_count = delete_branch_positions(
            _owner_id(user),
            [str(value) for value in thread_id],
            access_token,
        )
    except BranchCommentForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "BRANCH_POSITION_FORBIDDEN",
                "message": "접근할 수 있는 브랜치의 위치만 초기화할 수 있습니다.",
            },
        )
    return {"ok": True, "deleted_count": deleted_count}


def _normalize_message_comments(comments, user) -> None:
    current_user_id = _owner_id(user)
    _normalize_comment_authors(comments, user)
    for comment in comments:
        comment["can_edit"] = str(comment.get("user_id") or "") == current_user_id


@router.post(
    "/{thread_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    thread_id: str,
    body: CommentCreate,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    owner_id = _owner_id(user)
    if not _accessible_thread_ids(owner_id, [thread_id], access_token):
        raise HTTPException(status_code=404, detail="Thread not found")
    comment_id = str(uuid4())
    sb.rest_insert(
        "comments",
        [{
            "id": comment_id,
            "thread_id": thread_id,
            "user_id": owner_id,
            "message_index": body.message_index,
            "content": body.content.strip(),
        }],
        access_token,
    )
    comments = sb.rest_select(
        "comments",
        "&".join(
            [
                f"id=eq.{quote(comment_id)}",
                f"thread_id=eq.{quote(thread_id)}",
                f"user_id=eq.{quote(owner_id)}",
                "select=id,thread_id,message_index,user_id,content,created_at",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not comments:
        raise HTTPException(status_code=400, detail="코멘트 생성 실패")

    comment = comments[0]
    _normalize_message_comments([comment], user)
    return comment


@router.get("/{thread_id}/comments", response_model=List[CommentResponse])
def get_comments(
    thread_id: str,
    message_index: int | None = Query(
        default=None,
        ge=0,
        lt=BRANCH_NODE_POSITION_MESSAGE_INDEX,
    ),
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    owner_id = _owner_id(user)
    if not _accessible_thread_ids(owner_id, [thread_id], access_token):
        raise HTTPException(status_code=404, detail="Thread not found")
    filters = [
        f"thread_id=eq.{quote(thread_id)}",
        f"message_index=lt.{BRANCH_NODE_POSITION_MESSAGE_INDEX}",
        "select=id,thread_id,message_index,user_id,content,created_at",
        "order=message_index.asc,created_at.asc",
    ]
    if message_index is not None:
        filters.insert(1, f"message_index=eq.{message_index}")
    comments = sb.rest_select(
        "comments",
        "&".join(filters),
        access_token,
    )
    _normalize_message_comments(comments, user)
    return comments


@router.patch(
    "/{thread_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
def update_comment(
    thread_id: str,
    comment_id: UUID,
    body: CommentUpdate,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    owner_id = _owner_id(user)
    if not _accessible_thread_ids(owner_id, [thread_id], access_token):
        raise HTTPException(status_code=404, detail="Thread not found")
    updated = sb.rest_update(
        "comments",
        "&".join(
            [
                f"id=eq.{quote(str(comment_id))}",
                f"thread_id=eq.{quote(thread_id)}",
                f"user_id=eq.{quote(owner_id)}",
                f"message_index=lt.{BRANCH_NODE_POSITION_MESSAGE_INDEX}",
            ]
        ),
        {"content": body.content.strip()},
        access_token,
    )
    comment = updated[0] if isinstance(updated, list) and updated else None
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    _normalize_message_comments([comment], user)
    return comment


@router.delete("/{thread_id}/comments/{comment_id}")
def delete_comment(
    thread_id: str,
    comment_id: str,
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    result = sb.rest_delete(
        "comments",
        "&".join([
            f"id=eq.{quote(comment_id)}",
            f"thread_id=eq.{quote(thread_id)}",
            f"user_id=eq.{quote(_owner_id(user))}",
            f"message_index=lt.{BRANCH_NODE_POSITION_MESSAGE_INDEX}",
        ]),
        access_token,
    )

    if not result:
        raise HTTPException(status_code=404, detail="코멘트를 찾을 수 없음")

    return {"message": "삭제 완료"}
