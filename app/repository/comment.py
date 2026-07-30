from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote
from uuid import uuid4

from app.db import supabase as sb


BRANCH_COMMENT_MESSAGE_INDEX = 2_147_483_647
BRANCH_COMMENT_PREFIX = "__branch_node_comment_v1__:"


class BranchCommentForbiddenError(Exception):
    pass


class BranchCommentNotFoundError(Exception):
    pass


def _encode_branch_comment(
    content: str,
    position_x: float,
    position_y: float,
    author_id: Optional[str] = None,
) -> str:
    payload = {
        "text": content.strip(),
        "x": float(position_x),
        "y": float(position_y),
    }
    if author_id:
        payload["author_id"] = author_id
    return BRANCH_COMMENT_PREFIX + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _decode_branch_comment(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = row.get("content")
    if not isinstance(raw, str) or not raw.startswith(BRANCH_COMMENT_PREFIX):
        return None

    try:
        payload = json.loads(raw[len(BRANCH_COMMENT_PREFIX) :])
        content = payload["text"]
        position_x = float(payload["x"])
        position_y = float(payload["y"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    if (
        not isinstance(content, str)
        or not content.strip()
        or not math.isfinite(position_x)
        or not math.isfinite(position_y)
    ):
        return None

    return {
        "id": str(row["id"]),
        "thread_id": str(row["thread_id"]),
        "user_id": str(row["user_id"]),
        "author_id": str(payload.get("author_id") or row["user_id"]),
        "content": content,
        "position_x": position_x,
        "position_y": position_y,
        "created_at": row.get("created_at"),
    }


def _accessible_thread_ids(
    user_id: str,
    thread_ids: Iterable[str],
    access_token: str,
) -> List[str]:
    unique_ids = list(dict.fromkeys(str(thread_id) for thread_id in thread_ids))
    if not unique_ids:
        return []

    safe_ids = ",".join(quote(thread_id) for thread_id in unique_ids[:100])
    thread_rows = sb.rest_select(
        "threads",
        "&".join(
            [
                f"id=in.({safe_ids})",
                "select=id,owner_id,is_workspace",
            ]
        ),
        access_token,
    )
    member_rows = sb.rest_select(
        "thread_members",
        "&".join(
            [
                f"thread_id=in.({safe_ids})",
                f"user_id=eq.{quote(user_id)}",
                "select=thread_id",
            ]
        ),
        access_token,
    )
    member_ids = {
        str(row["thread_id"]) for row in member_rows if row.get("thread_id")
    }
    return [
        str(row["id"])
        for row in thread_rows
        if row.get("id")
        and (
            row.get("owner_id") == user_id
            or (bool(row.get("is_workspace")) and str(row["id"]) in member_ids)
        )
    ]


def list_branch_comments(
    owner_id: str,
    thread_ids: Iterable[str],
    access_token: str,
) -> List[Dict[str, Any]]:
    accessible_ids = _accessible_thread_ids(owner_id, thread_ids, access_token)
    if not accessible_ids:
        return []

    safe_ids = ",".join(quote(thread_id) for thread_id in accessible_ids)
    rows = sb.rest_select(
        "comments",
        "&".join(
            [
                "select=id,thread_id,user_id,content,created_at",
                f"thread_id=in.({safe_ids})",
                f"message_index=eq.{BRANCH_COMMENT_MESSAGE_INDEX}",
                "order=created_at.asc",
            ]
        ),
        access_token,
    )
    decoded = (_decode_branch_comment(row) for row in rows)
    return [comment for comment in decoded if comment is not None]


def create_branch_comment(
    owner_id: str,
    thread_id: str,
    content: str,
    position_x: float,
    position_y: float,
    access_token: str,
    author_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not _accessible_thread_ids(owner_id, [thread_id], access_token):
        raise BranchCommentForbiddenError

    comment_id = str(uuid4())
    encoded = _encode_branch_comment(
        content,
        position_x,
        position_y,
        author_id=author_id or owner_id,
    )
    sb.rest_insert(
        "comments",
        [
            {
                "id": comment_id,
                "thread_id": thread_id,
                "message_index": BRANCH_COMMENT_MESSAGE_INDEX,
                "user_id": owner_id,
                "content": encoded,
            }
        ],
        access_token,
    )
    rows = sb.rest_select(
        "comments",
        "&".join(
            [
                "select=id,thread_id,user_id,content,created_at",
                f"id=eq.{quote(comment_id)}",
                f"user_id=eq.{quote(owner_id)}",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        raise BranchCommentNotFoundError
    decoded = _decode_branch_comment(rows[0])
    if decoded is None:
        raise BranchCommentNotFoundError
    return decoded


def update_branch_comment(
    owner_id: str,
    comment_id: str,
    access_token: str,
    *,
    content: Optional[str] = None,
    position_x: Optional[float] = None,
    position_y: Optional[float] = None,
) -> Dict[str, Any]:
    rows = sb.rest_select(
        "comments",
        "&".join(
            [
                "select=id,thread_id,user_id,content,created_at",
                f"id=eq.{quote(comment_id)}",
                f"user_id=eq.{quote(owner_id)}",
                f"message_index=eq.{BRANCH_COMMENT_MESSAGE_INDEX}",
                "limit=1",
            ]
        ),
        access_token,
    )
    existing = _decode_branch_comment(rows[0]) if rows else None
    if existing is None:
        raise BranchCommentNotFoundError

    next_content = content.strip() if content is not None else existing["content"]
    next_x = position_x if position_x is not None else existing["position_x"]
    next_y = position_y if position_y is not None else existing["position_y"]
    encoded = _encode_branch_comment(
        next_content,
        next_x,
        next_y,
        author_id=existing["author_id"],
    )
    updated_rows = sb.rest_update(
        "comments",
        "&".join(
            [
                f"id=eq.{quote(comment_id)}",
                f"user_id=eq.{quote(owner_id)}",
                f"message_index=eq.{BRANCH_COMMENT_MESSAGE_INDEX}",
            ]
        ),
        {"content": encoded},
        access_token,
    )
    row = updated_rows[0] if isinstance(updated_rows, list) and updated_rows else None
    decoded = _decode_branch_comment(row) if row else None
    if decoded is None:
        raise BranchCommentNotFoundError
    return decoded


def delete_branch_comment(
    owner_id: str,
    comment_id: str,
    access_token: str,
) -> bool:
    deleted = sb.rest_delete(
        "comments",
        "&".join(
            [
                f"id=eq.{quote(comment_id)}",
                f"user_id=eq.{quote(owner_id)}",
                f"message_index=eq.{BRANCH_COMMENT_MESSAGE_INDEX}",
            ]
        ),
        access_token,
    )
    return deleted > 0
