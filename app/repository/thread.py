from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import json
import re
import requests

from app.db import supabase as sb
from app.services import llm_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

BRANCH_META_PREFIX = "__BRANCH_META__:"
# Some deployed schemas constrain message indexes to non-negative values.
# Reserve the maximum signed int32 value and exclude it from every public and
# LLM-context query, avoiding a database migration.
BRANCH_META_INDEX = 2_147_483_647
TUTORIAL_TITLE = "tutorial branch"
TUTORIAL_LEGACY_TITLE = "test branch"


class BranchNotFoundError(LookupError):
    pass


class BranchForbiddenError(PermissionError):
    pass


class BranchModelError(ValueError):
    pass


def _normalize_role(role: str) -> str:
    r = (role or "").lower().strip()
    if r in ("user", "assistant", "system", "tool"):
        return r
    return "assistant"


def _can_access_thread(user_id: str, thread_id: str, access_token: str) -> bool:
    """
    접근 허용 조건
    1) threads.owner_id == user_id
    2) thread_members에 user가 존재

    브랜치 하위 스레드는 워크스페이스가 아니지만 루트 멤버의 접근권한은
    명시적인 membership 행으로 상속할 수 있다.
    """

    # 1) owner check
    q_owner = "&".join([
        f"id=eq.{quote(thread_id)}",
        f"owner_id=eq.{quote(user_id)}",
        "select=id",
        "limit=1",
    ])
    owner_rows = sb.rest_select("threads", q_owner, access_token)
    if owner_rows:
        return True

    # Branch children inherit an explicit thread_members row from the
    # workspace root without becoming workspaces themselves.
    q_member = "&".join([
        f"thread_id=eq.{quote(thread_id)}",
        f"user_id=eq.{quote(user_id)}",
        "select=thread_id",
        "limit=1",
    ])
    mrows = sb.rest_select("thread_members", q_member, access_token)
    return bool(mrows)

# 스레드 생성 + 초기 메시지 삽입
def create_thread_with_messages(owner_id: str, payload: Dict[str, Any], access_token: str) -> str:
    thread_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    t = [{
        "id": thread_id,
        "title": payload["title"].strip(),
        "owner_id": owner_id,
        "created_at": now,
    }]
    sb.rest_insert("threads", t, access_token=access_token)

    msgs = payload.get("messages") or []
    if msgs:
        rows = []
        next_index = 0
        for m in msgs:
            rows.append(
                {
                    "thread_id": thread_id,
                    "role": _normalize_role(m["role"]),
                    "content": m["content"].strip(),
                    "index": next_index,
                    "created_at": now,
                }
            )
            next_index += 1
        sb.rest_insert("messages", rows, access_token=access_token)

    return thread_id


def _encode_branch_metadata(metadata: Dict[str, Any]) -> str:
    return BRANCH_META_PREFIX + json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))


def _decode_branch_metadata(content: str) -> Optional[Dict[str, Any]]:
    if not isinstance(content, str) or not content.startswith(BRANCH_META_PREFIX):
        return None
    try:
        value = json.loads(content[len(BRANCH_META_PREFIX):])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _get_thread_metadata(thread_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                f"index=eq.{BRANCH_META_INDEX}",
                "select=content",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        return None
    return _decode_branch_metadata(rows[0].get("content") or "")


def get_branch_root_id(thread_id: str, access_token: str) -> str:
    metadata = _get_thread_metadata(thread_id, access_token) or {}
    return str(metadata.get("root_thread_id") or thread_id)


def is_branch_root(thread_id: str, access_token: str) -> bool:
    metadata = _get_thread_metadata(thread_id, access_token) or {}
    return (
        not metadata.get("parent_thread_id")
        or metadata.get("root_thread_id") == thread_id
    )


def branch_lineage_thread_ids(
    owner_id: str,
    root_thread_id: str,
    access_token: str,
) -> List[str]:
    """Return a root and every owned branch descendant in its lineage."""
    owned_threads = _owned_thread_rows(owner_id, access_token)
    owned_ids = [str(row["id"]) for row in owned_threads if row.get("id")]
    metadata_by_id = _metadata_for_thread_ids(owned_ids, access_token)
    lineage_ids = [
        thread_id
        for thread_id in owned_ids
        if thread_id == root_thread_id
        or (metadata_by_id.get(thread_id) or {}).get("root_thread_id")
        == root_thread_id
    ]
    if root_thread_id not in lineage_ids:
        lineage_ids.insert(0, root_thread_id)
    return list(dict.fromkeys(lineage_ids))


def _persist_thread_metadata(
    thread_id: str,
    metadata: Dict[str, Any],
    access_token: str,
) -> None:
    content = _encode_branch_metadata(metadata)
    query = "&".join(
        [
            f"thread_id=eq.{quote(thread_id)}",
            f"index=eq.{BRANCH_META_INDEX}",
        ]
    )
    existing = sb.rest_select(
        "messages",
        query + "&select=index&limit=1",
        access_token,
    )
    if existing:
        sb.rest_update("messages", query, {"role": "assistant", "content": content}, access_token)
        return

    sb.rest_insert(
        "messages",
        [
            {
                "thread_id": thread_id,
                "role": "assistant",
                "content": content,
                "index": BRANCH_META_INDEX,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        access_token,
    )


def _owned_thread_rows(owner_id: str, access_token: str) -> List[Dict[str, Any]]:
    return sb.rest_select(
        "threads",
        "&".join(
            [
                f"owner_id=eq.{quote(owner_id)}",
                "select=id,title,created_at",
                "order=created_at.asc",
            ]
        ),
        access_token,
    )


def _metadata_for_thread_ids(
    thread_ids: List[str],
    access_token: str,
) -> Dict[str, Dict[str, Any]]:
    if not thread_ids:
        return {}
    safe_ids = ",".join(quote(thread_id) for thread_id in thread_ids)
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=in.({safe_ids})",
                f"index=eq.{BRANCH_META_INDEX}",
                "select=thread_id,content",
            ]
        ),
        access_token,
    )
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        thread_id = str(row.get("thread_id") or "")
        metadata = _decode_branch_metadata(row.get("content") or "")
        if thread_id and metadata:
            result[thread_id] = metadata
    return result


def _ensure_tutorial_branch(owner_id: str, access_token: str) -> None:
    """Create one private tutorial copy per account, or adopt the legacy demo."""
    owned_threads = _owned_thread_rows(owner_id, access_token)
    owned_ids = [str(row["id"]) for row in owned_threads if row.get("id")]
    metadata_by_id = _metadata_for_thread_ids(owned_ids, access_token)
    thread_by_id = {
        str(row["id"]): row for row in owned_threads if row.get("id")
    }

    tutorial_ids = [
        thread_id
        for thread_id, metadata in metadata_by_id.items()
        if metadata.get("is_tutorial")
    ]
    if tutorial_ids:
        active_root_id = next(
            (
                thread_id
                for thread_id in tutorial_ids
                if not metadata_by_id[thread_id].get("parent_thread_id")
                and not metadata_by_id[thread_id].get("tutorial_dismissed")
            ),
            None,
        )
        if (
            active_root_id
            and str(
                (thread_by_id.get(active_root_id) or {}).get("title") or ""
            ).strip().lower()
            == TUTORIAL_LEGACY_TITLE
        ):
            sb.rest_update(
                "threads",
                f"id=eq.{quote(active_root_id)}&owner_id=eq.{quote(owner_id)}",
                {"title": TUTORIAL_TITLE},
                access_token,
            )
        return

    legacy_root_id = next(
        (
            thread_id
            for thread_id, row in thread_by_id.items()
            if str(row.get("title") or "").strip().lower()
            in {TUTORIAL_LEGACY_TITLE, TUTORIAL_TITLE}
            and thread_id in metadata_by_id
            and (
                not metadata_by_id[thread_id].get("parent_thread_id")
                or metadata_by_id[thread_id].get("root_thread_id") == thread_id
            )
            and any(
                metadata.get("root_thread_id") == thread_id
                and child_id != thread_id
                for child_id, metadata in metadata_by_id.items()
            )
        ),
        None,
    )
    if legacy_root_id:
        sb.rest_update(
            "threads",
            f"id=eq.{quote(legacy_root_id)}&owner_id=eq.{quote(owner_id)}",
            {"title": TUTORIAL_TITLE},
            access_token,
        )
        for thread_id, metadata in metadata_by_id.items():
            if (
                thread_id == legacy_root_id
                or metadata.get("root_thread_id") == legacy_root_id
            ):
                _persist_thread_metadata(
                    thread_id,
                    {**metadata, "is_tutorial": True},
                    access_token,
                )
        return

    root_id = str(uuid4())
    level_one = [str(uuid4()) for _ in range(2)]
    level_two = [str(uuid4()) for _ in range(4)]
    level_three = [str(uuid4()) for _ in range(8)]
    node_ids = [root_id, *level_one, *level_two, *level_three]
    parents: Dict[str, Optional[str]] = {root_id: None}
    for index, thread_id in enumerate(level_one):
        parents[thread_id] = root_id
    for index, thread_id in enumerate(level_two):
        parents[thread_id] = level_one[index // 2]
    for index, thread_id in enumerate(level_three):
        parents[thread_id] = level_two[index // 2]

    titles = {
        root_id: TUTORIAL_TITLE,
        **{
            thread_id: f"tutorial branch {index + 1}"
            for index, thread_id in enumerate(node_ids[1:])
        },
    }
    created_at = datetime.now(timezone.utc)
    thread_rows = []
    message_rows = []
    for index, thread_id in enumerate(node_ids):
        timestamp = (created_at + timedelta(milliseconds=index)).isoformat()
        thread_rows.append(
            {
                "id": thread_id,
                "title": titles[thread_id],
                "owner_id": owner_id,
                "is_workspace": False,
                "created_at": timestamp,
            }
        )
        message_rows.append(
            {
                "thread_id": thread_id,
                "role": "assistant",
                "content": _encode_branch_metadata(
                    {
                        "version": 1,
                        "parent_thread_id": parents[thread_id],
                        "root_thread_id": root_id,
                        "context_preview": (
                            None
                            if thread_id == root_id
                            else "튜토리얼 분기 예시"
                        ),
                        "model": "gemini-2.5-flash",
                        "is_tutorial": True,
                    }
                ),
                "index": BRANCH_META_INDEX,
                "created_at": timestamp,
            }
        )

    sb.rest_insert("threads", thread_rows, access_token)
    try:
        sb.rest_insert("messages", message_rows, access_token)
    except Exception:
        for thread_id in reversed(node_ids):
            try:
                sb.rest_delete(
                    "threads",
                    f"id=eq.{quote(thread_id)}&owner_id=eq.{quote(owner_id)}",
                    access_token,
                )
            except Exception:
                pass
        raise


def remember_thread_model(
    owner_id: str,
    thread_id: str,
    model: str,
    access_token: str,
) -> bool:
    """Persist a Gemini model hint without requiring a threads schema change."""
    if not (model or "").lower().startswith("gemini-"):
        return False

    rows = sb.rest_select(
        "threads",
        "&".join(
            [
                f"id=eq.{quote(thread_id)}",
                f"owner_id=eq.{quote(owner_id)}",
                "select=id",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        return False

    metadata = _get_thread_metadata(thread_id, access_token) or {
        "version": 1,
        "parent_thread_id": None,
        "root_thread_id": thread_id,
        "context_preview": None,
    }
    metadata["model"] = model
    _persist_thread_metadata(thread_id, metadata, access_token)
    return True


def _context_preview(messages: List[Dict[str, Any]]) -> str:
    source = next(
        (
            (row.get("content") or "").strip()
            for row in reversed(messages)
            if (row.get("role") or "").lower() == "assistant"
            and (row.get("content") or "").strip()
        ),
        "",
    )
    if not source:
        source = next(
            (
                (row.get("content") or "").strip()
                for row in reversed(messages)
                if (row.get("content") or "").strip()
            ),
            "",
        )
    return source[:20]


def _single_sentence_summary(text: str) -> str:
    summary = re.sub(r"\s+", " ", (text or "")).strip().strip("\"'“”")
    if not summary:
        return "이전 대화 내용이 없습니다."

    sentence_end = re.search(r"[.!?。！？]", summary)
    if sentence_end:
        summary = summary[: sentence_end.end()]

    # The original branch-banner contract is 20 characters maximum.
    if len(summary) > 20:
        summary = summary[:19].rstrip(" .!?。！？") + "…"
    return summary


async def _summarize_branch_context(
    messages: List[Dict[str, Any]],
    model: str,
) -> str:
    visible = [
        {
            "role": _normalize_role(row.get("role") or ""),
            "content": (row.get("content") or "").strip(),
        }
        for row in messages[-20:]
        if (row.get("content") or "").strip()
    ]
    if not visible:
        return "이전 대화 내용이 없습니다."

    transcript = "\n".join(
        f"{row['role']}: {row['content']}" for row in visible
    )[-6000:]
    prompt = [
        {
            "role": "system",
            "content": (
                "이전 대화의 핵심 맥락을 한국어 한 문장으로 요약하세요. "
                "공백과 문장부호를 포함해 20자 이내로 쓰고, 설명이나 따옴표는 붙이지 마세요."
            ),
        },
        {
            "role": "user",
            "content": f"요약할 이전 대화:\n{transcript}",
        },
    ]
    try:
        generated = await llm_client.generate(model=model, messages=prompt)
        return _single_sentence_summary(generated)
    except Exception:
        logger.exception("Failed to summarize branch context; using a local fallback")
        return _single_sentence_summary(_context_preview(messages))


async def create_thread_branch(
    owner_id: str,
    parent_thread_id: str,
    access_token: str,
    requested_model: Optional[str] = None,
) -> Dict[str, Any]:
    parent_rows = sb.rest_select(
        "threads",
        "&".join(
            [
                f"id=eq.{quote(parent_thread_id)}",
                "select=id,title,owner_id,is_workspace",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not parent_rows:
        raise BranchNotFoundError("Thread not found")
    parent = parent_rows[0]
    if parent.get("owner_id") != owner_id:
        raise BranchForbiddenError("Only the thread owner can create a branch")

    metadata = _get_thread_metadata(parent_thread_id, access_token)
    if (metadata or {}).get("is_deleted"):
        raise BranchNotFoundError("Thread has been deleted")
    stored_model = (metadata or {}).get("model")
    model = requested_model or stored_model
    if not model or not str(model).lower().startswith("gemini-"):
        raise BranchModelError("Branching is available only for Gemini threads")
    if stored_model and requested_model and stored_model != requested_model:
        raise BranchModelError("Requested model does not match the thread model")

    messages = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(parent_thread_id)}",
                "index=gte.0",
                f"index=lt.{BRANCH_META_INDEX}",
                "select=index,role,content,created_at",
                "order=index.asc",
            ]
        ),
        access_token,
    )
    preview = await _summarize_branch_context(messages, str(model))
    child_thread_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    title = (parent.get("title") or "").strip()
    root_thread_id = (metadata or {}).get("root_thread_id") or parent_thread_id
    root = parent
    if root_thread_id != parent_thread_id:
        root_rows = sb.rest_select(
            "threads",
            "&".join(
                [
                    f"id=eq.{quote(root_thread_id)}",
                    "select=id,title,owner_id,is_workspace",
                    "limit=1",
                ]
            ),
            access_token,
        )
        if not root_rows:
            raise BranchNotFoundError("Branch root not found")
        root = root_rows[0]
    root_is_workspace = bool(root.get("is_workspace"))

    # Mark the original/root thread as Gemini as well. This also makes legacy
    # Gemini threads branchable after the first explicit branch request.
    if metadata is None:
        _persist_thread_metadata(
            parent_thread_id,
            {
                "version": 1,
                "parent_thread_id": None,
                "root_thread_id": root_thread_id,
                "context_preview": None,
                "model": model,
            },
            access_token,
        )

    sb.rest_insert(
        "threads",
        [
            {
                "id": child_thread_id,
                "title": title,
                "owner_id": owner_id,
                "is_workspace": False,
                "created_at": now,
            }
        ],
        access_token,
    )
    try:
        if root_is_workspace:
            root_members = sb.rest_select(
                "thread_members",
                "&".join(
                    [
                        f"thread_id=eq.{quote(root_thread_id)}",
                        "select=user_id,role",
                    ]
                ),
                access_token,
            )
            if root_members:
                sb.rest_insert(
                    "thread_members",
                    [
                        {
                            "thread_id": child_thread_id,
                            "user_id": member["user_id"],
                            "role": member.get("role") or "member",
                        }
                        for member in root_members
                        if member.get("user_id")
                    ],
                    access_token,
                )

        child_metadata = {
            "version": 1,
            "parent_thread_id": parent_thread_id,
            "root_thread_id": root_thread_id,
            "context_preview": preview,
            "model": model,
        }
        rows = [
            {
                "thread_id": child_thread_id,
                "role": "assistant",
                "content": _encode_branch_metadata(child_metadata),
                "index": BRANCH_META_INDEX,
                "created_at": now,
            }
        ]
        sb.rest_insert("messages", rows, access_token)
    except Exception:
        # Avoid leaving an empty child if branch metadata persistence fails.
        try:
            sb.rest_delete("threads", f"id=eq.{quote(child_thread_id)}", access_token)
        except Exception:
            pass
        raise

    return {
        "thread_id": child_thread_id,
        "title": title,
        "parent_thread_id": parent_thread_id,
        "context_preview": preview,
        "status": "saved",
    }


def list_branch_trees(owner_id: str, access_token: str) -> List[Dict[str, Any]]:
    _ensure_tutorial_branch(owner_id, access_token)
    member_rows = sb.rest_select(
        "thread_members",
        "&".join(
            [
                f"user_id=eq.{quote(owner_id)}",
                "select=thread_id,role",
            ]
        ),
        access_token,
    )
    member_thread_ids = list(
        dict.fromkeys(
            str(row["thread_id"])
            for row in member_rows
            if row.get("thread_id")
        )
    )
    member_role_by_thread_id = {
        str(row["thread_id"]): str(row.get("role") or "member")
        for row in member_rows
        if row.get("thread_id")
    }
    owned_threads = sb.rest_select(
        "threads",
        "&".join(
            [
                f"owner_id=eq.{quote(owner_id)}",
                "select=id",
                "order=created_at.asc",
            ]
        ),
        access_token,
    )
    accessible_ids = list(
        dict.fromkeys(
            [
                *(str(row["id"]) for row in owned_threads if row.get("id")),
                *member_thread_ids,
            ]
        )
    )
    if not accessible_ids:
        return []

    safe_accessible_ids = ",".join(quote(thread_id) for thread_id in accessible_ids)
    threads = sb.rest_select(
        "threads",
        "&".join(
            [
                f"id=in.({safe_accessible_ids})",
                "select=id,title,created_at,is_workspace,owner_id",
                "order=created_at.asc",
            ]
        ),
        access_token,
    )
    by_id = {str(row.get("id")): row for row in threads if row.get("id")}
    if not by_id:
        return []

    markers = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=in.({safe_accessible_ids})",
                f"index=eq.{BRANCH_META_INDEX}",
                "select=thread_id,content",
            ]
        ),
        access_token,
    )
    metadata_by_id: Dict[str, Dict[str, Any]] = {}
    for row in markers:
        thread_id = str(row.get("thread_id") or "")
        if thread_id not in by_id:
            continue
        metadata = _decode_branch_metadata(row.get("content") or "")
        if metadata:
            metadata_by_id[thread_id] = metadata

    # A lineage exists only if at least one owned thread has a parent.
    child_ids = {
        thread_id
        for thread_id, metadata in metadata_by_id.items()
        if metadata.get("parent_thread_id")
    }
    if not child_ids:
        return []

    included = set(child_ids)
    for child_id in list(child_ids):
        current = child_id
        seen = set()
        while current not in seen:
            seen.add(current)
            parent_id = (metadata_by_id.get(current) or {}).get("parent_thread_id")
            if not parent_id or parent_id not in by_id:
                break
            included.add(parent_id)
            current = parent_id

    nodes: Dict[str, Dict[str, Any]] = {}
    for thread_id in included:
        thread = by_id[thread_id]
        metadata = metadata_by_id.get(thread_id) or {}
        if metadata.get("tutorial_dismissed"):
            continue
        is_root = (
            not metadata.get("parent_thread_id")
            or metadata.get("root_thread_id") == thread_id
        )
        is_workspace = is_root and bool(thread.get("is_workspace"))
        can_manage = thread.get("owner_id") == owner_id
        workspace_role = None
        if is_workspace:
            workspace_role = (
                "owner"
                if can_manage
                else member_role_by_thread_id.get(thread_id)
            )
        nodes[thread_id] = {
            "id": thread_id,
            "thread_id": thread_id,
            "title": thread.get("title") or "",
            "parent_thread_id": metadata.get("parent_thread_id"),
            "context_preview": metadata.get("context_preview"),
            "created_at": thread.get("created_at") or "",
            "is_deleted": bool(metadata.get("is_deleted")),
            "is_tutorial": bool(metadata.get("is_tutorial")),
            "can_manage": can_manage,
            "is_workspace": is_workspace,
            "workspace_role": workspace_role,
            "can_manage_workspace": is_root and can_manage,
            "children": [],
        }

    roots: List[Dict[str, Any]] = []
    for thread_id, node in nodes.items():
        parent_id = node.get("parent_thread_id")
        if parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    def sort_tree(node: Dict[str, Any]) -> None:
        node["children"].sort(key=lambda child: (child.get("created_at") or "", child["thread_id"]))
        for child in node["children"]:
            sort_tree(child)

    roots.sort(key=lambda node: (node.get("created_at") or "", node["thread_id"]))
    for root in roots:
        sort_tree(root)
    return roots

# 스레드 목록 조회 (owner이거나 member인 스레드 모두)
def list_threads_for_owner(
    owner_id: str,
    access_token: str,
    limit: int = 20,
    offset: int = 0,
    order: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Supabase REST: fetch threads where current user is owner OR member (thread_members.user_id).
    We first fetch membership thread_ids to avoid relying on join semantics that can break.
    """
    order = "desc" if str(order).lower() != "asc" else "asc"

    # Step 1: collect thread_ids where user is a member
    member_rows = sb.rest_select(
        "thread_members",
        "&".join(
            [
                f"user_id=eq.{quote(owner_id)}",
                "select=thread_id,role",
            ]
        ),
        access_token,
    )
    member_thread_ids = [m.get("thread_id") for m in member_rows if m.get("thread_id")]
    member_roles = {
        str(row["thread_id"]): str(row.get("role") or "member")
        for row in member_rows
        if row.get("thread_id")
    }

    # Build OR filter: owner or in member_thread_ids
    or_filters = [f"owner_id.eq.{quote(owner_id)}"]
    if member_thread_ids:
        ids = ",".join(quote(tid) for tid in member_thread_ids)
        or_filters.append(f"id.in.({ids})")

    filters = [
        "select=" + ",".join(
            [
                "id",
                "title",
                "created_at",
                "is_workspace",
                "owner_id",
                "messages(count)",
                "last:messages(content,created_at)",
            ]
        ),
        f"or=({','.join(or_filters)})",
        f"order=created_at.{order}",
        f"limit={limit}",
        f"offset={offset}",
        f"messages.index=lt.{BRANCH_META_INDEX}",
        f"last.index=lt.{BRANCH_META_INDEX}",
        "last.order=created_at.desc",
        "last.limit=1",
    ]
    query = "&".join(filters)
    rows = sb.rest_select("threads", query, access_token)
    listed_ids = [str(row["id"]) for row in rows if row.get("id")]
    listed_metadata = _metadata_for_thread_ids(listed_ids, access_token)

    out: List[Dict[str, Any]] = []
    for r in rows:
        metadata = listed_metadata.get(str(r.get("id"))) or {}
        if metadata.get("is_tutorial") and metadata.get("tutorial_dismissed"):
            continue
        cnt = int(r.get("messages", [{}])[0].get("count", 0)) if r.get("messages") else 0
        preview = None
        if isinstance(r.get("last"), list) and r["last"]:
            preview = (r["last"][0].get("content") or "")[:50] or None
        thread_id = str(r.get("id") or "")
        is_root = (
            not metadata.get("parent_thread_id")
            or metadata.get("root_thread_id") == thread_id
        )
        is_owner = r.get("owner_id") == owner_id
        is_ws = is_root and bool(r.get("is_workspace", False))
        workspace_role = None
        if is_ws:
            workspace_role = "owner" if is_owner else member_roles.get(thread_id)
        out.append({
            "id": thread_id,
            "title": r.get("title"),
            "created_at": r.get("created_at"),
            "is_workspace": is_ws,
            "workspace_role": workspace_role,
            "can_manage_workspace": is_root and is_owner,
            "message_count": cnt,
            "last_message_preview": preview,
        })
    return out

def _hard_delete_thread(thread_id: str, access_token: str) -> int:
    """Delete one physical thread row and its directly stored children."""
    for table in ("comments", "bookmarks"):
        try:
            sb.rest_delete(table, f"thread_id=eq.{quote(thread_id)}", access_token)
        except Exception:
            pass
    try:
        sb.rest_delete("messages", f"thread_id=eq.{quote(thread_id)}", access_token)
    except Exception:
        pass
    try:
        sb.rest_delete("thread_members", f"thread_id=eq.{quote(thread_id)}", access_token)
    except Exception:
        pass
    return sb.rest_delete("threads", f"id=eq.{quote(thread_id)}", access_token)


def _all_branch_metadata(access_token: str) -> Dict[str, Dict[str, Any]]:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"index=eq.{BRANCH_META_INDEX}",
                "select=thread_id,content",
            ]
        ),
        access_token,
    )
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        thread_id = str(row.get("thread_id") or "")
        metadata = _decode_branch_metadata(row.get("content") or "")
        if thread_id and metadata:
            result[thread_id] = metadata
    return result


# 스레드 삭제
def delete_thread_by_id(user_id: str, thread_id: str, access_token: str) -> int:
    # Load thread info
    q_thread = "&".join(
        [
            f"id=eq.{quote(thread_id)}",
            "select=id,owner_id,is_workspace",
            "limit=1",
        ]
    )
    trows = sb.rest_select("threads", q_thread, access_token)
    if not trows:
        return 0
    thread = trows[0]
    is_workspace = bool(thread.get("is_workspace"))
    owner_id = thread.get("owner_id")

    # Deleting a thread or an entire branch lineage is owner-only.
    if owner_id != user_id:
        return 0

    metadata = _get_thread_metadata(thread_id, access_token)
    if not metadata:
        return _hard_delete_thread(thread_id, access_token)

    metadata_by_id = _all_branch_metadata(access_token)
    children = [
        child_id
        for child_id, child_metadata in metadata_by_id.items()
        if child_metadata.get("parent_thread_id") == thread_id
    ]
    is_root = (
        not metadata.get("parent_thread_id")
        or metadata.get("root_thread_id") == thread_id
    )

    if is_root:
        lineage_ids = {
            candidate_id
            for candidate_id, candidate_metadata in metadata_by_id.items()
            if candidate_id == thread_id
            or candidate_metadata.get("root_thread_id") == thread_id
        }
        lineage_ids.add(thread_id)
        deleted = 0
        if metadata.get("is_tutorial"):
            for candidate_id in lineage_ids:
                if candidate_id != thread_id:
                    deleted += _hard_delete_thread(candidate_id, access_token)
            for table in ("comments", "bookmarks"):
                try:
                    sb.rest_delete(
                        table,
                        f"thread_id=eq.{quote(thread_id)}",
                        access_token,
                    )
                except Exception:
                    pass
            try:
                sb.rest_delete(
                    "messages",
                    "&".join(
                        [
                            f"thread_id=eq.{quote(thread_id)}",
                            f"index=lt.{BRANCH_META_INDEX}",
                        ]
                    ),
                    access_token,
                )
            except Exception:
                pass
            _persist_thread_metadata(
                thread_id,
                {
                    **metadata,
                    "is_deleted": True,
                    "tutorial_dismissed": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                },
                access_token,
            )
            return deleted + 1

        for candidate_id in lineage_ids:
            deleted += _hard_delete_thread(candidate_id, access_token)
        return deleted

    if children:
        tombstone = {
            **metadata,
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }
        _persist_thread_metadata(thread_id, tombstone, access_token)
        try:
            sb.rest_delete(
                "messages",
                "&".join(
                    [
                        f"thread_id=eq.{quote(thread_id)}",
                        f"index=lt.{BRANCH_META_INDEX}",
                    ]
                ),
                access_token,
            )
        except Exception:
            pass
        return 1

    return _hard_delete_thread(thread_id, access_token)


def update_thread_title(
    owner_id: str,
    thread_id: str,
    title: str,
    access_token: str,
) -> Optional[str]:
    normalized_title = (title or "").strip()
    if not normalized_title:
        raise ValueError("Thread title cannot be empty")

    rows = sb.rest_select(
        "threads",
        "&".join(
            [
                f"id=eq.{quote(thread_id)}",
                f"owner_id=eq.{quote(owner_id)}",
                "select=id",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        return None

    sb.rest_update(
        "threads",
        "&".join(
            [
                f"id=eq.{quote(thread_id)}",
                f"owner_id=eq.{quote(owner_id)}",
            ]
        ),
        {"title": normalized_title},
        access_token,
    )
    return normalized_title


def get_thread_detail(user_id: str, thread_id: str, access_token: str):
    q = "&".join(
        [
            f"id=eq.{quote(thread_id)}",
            "select=id,title,created_at,is_workspace,owner_id",
            "limit=1",
        ]
    )
    rows = sb.rest_select("threads", q, access_token)
    if not rows:
        return None

    thread = rows[0]
    metadata = _get_thread_metadata(thread_id, access_token) or {}
    if metadata.get("is_deleted"):
        return None

    member_role = None
    if thread["owner_id"] != user_id:
        m = sb.rest_select(
            "thread_members",
            "&".join([
                f"thread_id=eq.{quote(thread_id)}",
                f"user_id=eq.{quote(user_id)}",
                "select=role",
                "limit=1",
            ]),
            access_token,
        )
        if not m:
            return None
        member_role = str(m[0].get("role") or "member")

    _, messages = list_thread_messages(
        owner_id=thread["owner_id"],
        thread_id=thread_id,
        access_token=access_token,
        limit=200,
        offset=0,
        order="asc",
    )

    thread["messages"] = messages
    thread["can_rename"] = thread["owner_id"] == user_id
    thread["parent_thread_id"] = metadata.get("parent_thread_id")
    thread["root_thread_id"] = metadata.get("root_thread_id")
    thread["context_preview"] = metadata.get("context_preview")
    is_root = (
        not metadata.get("parent_thread_id")
        or metadata.get("root_thread_id") == thread_id
    )
    thread["is_workspace"] = is_root and bool(thread.get("is_workspace"))
    thread["workspace_role"] = (
        ("owner" if thread["owner_id"] == user_id else member_role)
        if thread["is_workspace"]
        else None
    )
    thread["can_manage_workspace"] = is_root and thread["owner_id"] == user_id
    return thread



# 스레드별 메시지 목록 조회
def _normalize_bookmark_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "thread_id": str(row.get("thread_id") or ""),
        "message_index": int(row.get("message_index", 0)),
        "created_at": row.get("created_at"),
    }


def _message_exists(thread_id: str, message_index: int, access_token: str) -> bool:
    q = "&".join(
        [
            f"thread_id=eq.{quote(thread_id)}",
            f"index=eq.{message_index}",
            "select=index",
            "limit=1",
        ]
    )
    rows = sb.rest_select("messages", q, access_token)
    return bool(rows)


def list_thread_bookmarks(
    owner_id: str,
    thread_id: str,
    access_token: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, [])

    q = "&".join(
        [
            f"user_id=eq.{quote(owner_id)}",
            f"thread_id=eq.{quote(thread_id)}",
            "select=thread_id,message_index,created_at",
            "order=message_index.asc",
        ]
    )
    rows = sb.rest_select("bookmarks", q, access_token)
    return (True, [_normalize_bookmark_row(r) for r in rows])


def add_thread_bookmark(
    owner_id: str,
    thread_id: str,
    message_index: int,
    access_token: str,
) -> Tuple[bool, Dict[str, Any] | None]:
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, None)

    if not _message_exists(thread_id, message_index, access_token):
        raise ValueError("Message not found for this thread")

    q_existing = "&".join(
        [
            f"user_id=eq.{quote(owner_id)}",
            f"thread_id=eq.{quote(thread_id)}",
            f"message_index=eq.{message_index}",
            "select=thread_id,message_index,created_at",
            "limit=1",
        ]
    )
    existing = sb.rest_select("bookmarks", q_existing, access_token)
    if existing:
        return (True, _normalize_bookmark_row(existing[0]))

    try:
        sb.rest_insert(
            "bookmarks",
            [
                {
                    "user_id": owner_id,
                    "thread_id": thread_id,
                    "message_index": message_index,
                }
            ],
            access_token,
        )
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 409:
            raise

    rows = sb.rest_select("bookmarks", q_existing, access_token)
    if not rows:
        return (
            True,
            {
                "thread_id": thread_id,
                "message_index": message_index,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return (True, _normalize_bookmark_row(rows[0]))


def remove_thread_bookmark(
    owner_id: str,
    thread_id: str,
    message_index: int,
    access_token: str,
) -> Tuple[bool, bool]:
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, False)

    q = "&".join(
        [
            f"user_id=eq.{quote(owner_id)}",
            f"thread_id=eq.{quote(thread_id)}",
            f"message_index=eq.{message_index}",
        ]
    )
    deleted = sb.rest_delete("bookmarks", q, access_token)
    return (True, deleted > 0)


def list_thread_messages(
    owner_id: str,
    thread_id: str,
    access_token: str,
    limit: int = 50,
    offset: int = 0,
    order: str = "asc",
) -> Tuple[bool, list[dict]]:
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, [])

    order = "asc" if str(order).lower() != "desc" else "desc"

    q_msgs = "&".join([
        f"thread_id=eq.{quote(thread_id)}",
        "index=gte.0",
        f"index=lt.{BRANCH_META_INDEX}",
        "select=index,role,content,created_at",
        f"order=index.{order}",
        f"limit={limit}",
        f"offset={offset}",
    ])
    mrows = sb.rest_select("messages", q_msgs, access_token)

    rows = [{
        "index": int(m.get("index", 0)),
        "role": (m.get("role") or "assistant"),
        "content": m.get("content") or "",
        "created_at": m.get("created_at") or "",
    } for m in mrows]

    return (True, rows)


# 스레드에 메시지 추가
def add_messages_to_thread(
    owner_id: str,
    thread_id: str,
    messages: List[Dict[str, str]],
    access_token: str,
) -> Tuple[bool, int]:
    if not _can_access_thread(owner_id, thread_id, access_token):
        return (False, 0)

    now = datetime.now(timezone.utc).isoformat()
    next_index = _get_max_index(thread_id, access_token) + 1

    rows = []
    for m in messages:
        content = (m.get("content") or "").strip()
        if not content:
            raise ValueError("Message content cannot be empty")

        rows.append(
            {
                "thread_id": thread_id,
                "role": _normalize_role(m.get("role", "")),
                "content": content,
                "index": next_index,
                "created_at": now,
            }
        )
        next_index += 1

    sb.rest_insert("messages", rows, access_token)
    return (True, len(rows))


def _get_max_index(thread_id: str, access_token: str) -> int:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "index=not.is.null",
                f"index=lt.{BRANCH_META_INDEX}",
                "select=index",
                "order=index.desc",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        return -1
    try:
        return int(rows[0].get("index", -1))
    except Exception:
        return -1


def insert_and_fetch_message(
    thread_id: str,
    role: str,
    content: str,
    access_token: str,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    last_idx = _get_max_index(thread_id, access_token)
    new_index = last_idx + 1
    sb.rest_insert(
        "messages",
        [
            {
                "thread_id": thread_id,
                "role": role,
                "content": content.strip(),
                "index": new_index,
                "created_at": now,
            }
        ],
        access_token,
    )
    # Fetch back deterministically
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                f"index=eq.{new_index}",
                "select=index,role,content,created_at",
                "order=created_at.desc",
                "limit=1",
            ]
        ),
        access_token,
    )
    if not rows:
        raise RuntimeError("Inserted message not found")
    row = rows[0]
    row["index"] = int(row.get("index", new_index))
    return row


def list_recent_messages(thread_id: str, limit: int, access_token: str) -> List[Dict[str, Any]]:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "index=gte.0",
                f"index=lt.{BRANCH_META_INDEX}",
                "select=index,role,content,created_at",
                "order=index.desc",
                f"limit={limit}",
            ]
        ),
        access_token,
    )
    return rows


def list_messages_before_index(thread_id: str, before_index: int, limit: int, access_token: str) -> List[Dict[str, Any]]:
    """
    Fetch messages with index < before_index ordered desc, limited.
    """
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "index=gte.0",
                f"index=lt.{BRANCH_META_INDEX}",
                f"index=lt.{before_index}",
                "select=index,role,content,created_at",
                "order=index.desc",
                f"limit={limit}",
            ]
        ),
        access_token,
    )
    return rows


def get_first_assistant_message(thread_id: str, access_token: str) -> Dict[str, Any] | None:
    rows = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "role=eq.assistant",
                f"index=lt.{BRANCH_META_INDEX}",
                "select=index,role,content",
                "order=index.asc",
                "limit=1",
            ]
        ),
        access_token,
    )
    return rows[0] if rows else None


async def chat_with_llm(
    owner_id: str,
    thread_id: str,
    content: str,
    model: str,
    context_limit: int,
    access_token: str,
) -> Dict[str, Any]:
    """
    Insert user message, call LLM, insert assistant message, and return summary.
    """
    # Ownership check
    q_check = "&".join(
        [
            f"id=eq.{quote(thread_id)}",
            f"owner_id=eq.{quote(owner_id)}",
            "select=id",
            "limit=1",
        ]
    )
    trows = sb.rest_select("threads", q_check, access_token)
    if not trows:
        return {}

    now = datetime.now(timezone.utc).isoformat()
    # 1) Insert user message
    user_row = insert_and_fetch_message(thread_id, "user", content, access_token)
    incoming = content.strip()
    saved = (user_row.get("content") or "").strip()
    if saved != incoming and settings.CHAT_DEBUG_ASSERTS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "code": "CHAT_INCOMING_MISMATCH",
                "incoming": incoming[:60],
                "saved": saved[:60],
                "inserted_index": user_row.get("index"),
            },
        )

    # 2) Fetch recent messages for context (including the new one) AFTER insert
    recent_desc = list_recent_messages(thread_id, context_limit, access_token)
    chron = list(reversed(recent_desc))  # to chronological order
    llm_messages = [
        {"role": m.get("role", "assistant"), "content": m.get("content", ""), "index": int(m.get("index", 0))}
        for m in chron
    ]

    if settings.CHAT_DEBUG_ASSERTS:
        indices = [m["index"] for m in llm_messages]
        if user_row.get("index") not in indices:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "CHAT_CONTEXT_MISSING_INSERTED",
                    "inserted_index": user_row.get("index"),
                    "first": indices[0] if indices else None,
                    "last": indices[-1] if indices else None,
                    "count": len(indices),
                },
            )
        last_user = next((m for m in reversed(llm_messages) if m.get("role") == "user"), None)
        if last_user:
            if (last_user.get("content") or "").strip() != incoming:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "CHAT_LAST_USER_WRONG",
                        "incoming": incoming[:60],
                        "last_user_index": last_user.get("index"),
                        "last_user_preview": (last_user.get("content") or "")[:60],
                        "chron_first": (
                            llm_messages[0]["index"],
                            llm_messages[0]["role"],
                            (llm_messages[0]["content"] or "")[:30],
                        )
                        if llm_messages
                        else None,
                        "chron_last": (
                            llm_messages[-1]["index"],
                            llm_messages[-1]["role"],
                            (llm_messages[-1]["content"] or "")[:30],
                        )
                        if llm_messages
                        else None,
                    },
                )
        else:
            raise HTTPException(
                status_code=500,
                detail={"code": "CHAT_NO_USER_IN_CONTEXT", "incoming": incoming[:60]},
            )

    if settings.APP_ENV in ("dev", "local"):
        last_user = next((m for m in reversed(llm_messages) if m.get("role") == "user"), None)
        logger.info(
            "[chat] context debug",
            extra={
                "thread_id": thread_id,
                "requested_content_preview": content[:60],
                "requested_content_len": len(content),
                "inserted_user_index": user_row.get("index"),
                "context_limit": context_limit,
                "fetched_count": len(recent_desc),
                "first_msg": {
                    "index": llm_messages[0].get("index") if llm_messages else None,
                    "role": llm_messages[0].get("role") if llm_messages else None,
                    "preview": (llm_messages[0].get("content") or "")[:20] if llm_messages else None,
                },
                "last_msg": {
                    "index": llm_messages[-1].get("index") if llm_messages else None,
                    "role": llm_messages[-1].get("role") if llm_messages else None,
                    "preview": (llm_messages[-1].get("content") or "")[:20] if llm_messages else None,
                },
                "last_user": {
                    "index": last_user.get("index") if isinstance(last_user, dict) else None,
                    "preview": last_user.get("content")[:40] if isinstance(last_user, dict) and last_user.get("content") else None,
                }
            },
        )

    # 3) Call LLM server (with fallback)
    payload_messages = [{"role": m["role"], "content": m["content"]} for m in llm_messages]
    if not any((m.get("role") or "").lower() == "system" for m in payload_messages):
        payload_messages = [
            {"role": "system", "content": settings.LLM_SYSTEM_PROMPT + " Never repeat the user's question; answer directly."}
        ] + payload_messages
    if settings.CHAT_DEBUG_ASSERTS:
        if payload_messages[-1]["content"].strip() != incoming:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={"code": "CHAT_PAYLOAD_LAST_USER_MISMATCH", "incoming": incoming[:60]},
            )

    # Pre-LLM debug logging
    if settings.APP_ENV in ("dev", "local"):
        logger.info(
            "[chat] pre-llm",
            extra={
                "incoming_preview": incoming[:40],
                "last_user_preview": (last_user.get("content") or "")[:40] if "last_user" in locals() and last_user else None,
                "chron_first_preview": (llm_messages[0]["content"] or "")[:40] if llm_messages else None,
                "chron_last_preview": (llm_messages[-1]["content"] or "")[:40] if llm_messages else None,
                "first_index": llm_messages[0]["index"] if llm_messages else None,
                "last_index": llm_messages[-1]["index"] if llm_messages else None,
            },
        )

    assistant_content = await llm_client.generate(
        model=model,
        messages=payload_messages,
    )
    def _is_echo(text: str, user_text: str) -> bool:
        import re
        def norm(s: str) -> str:
            return re.sub(r"\W+", "", (s or "").lower())
        return norm(text) == norm(user_text) or (norm(user_text) and norm(user_text) in norm(text))

    if _is_echo(assistant_content, incoming):
        payload_messages.append(
            {"role": "system", "content": "Do not repeat the user's question. Provide a concise answer now."}
        )
        assistant_content = await llm_client.generate(model=model, messages=payload_messages)

    assistant_row = insert_and_fetch_message(thread_id, "assistant", assistant_content, access_token)
    saved_assistant = (assistant_row.get("content") or "").strip()
    if saved_assistant != assistant_content.strip() and settings.CHAT_DEBUG_ASSERTS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ASSISTANT_SAVE_MISMATCH",
                "assistant_preview": assistant_content[:80],
                "saved_preview": saved_assistant[:80],
                "assistant_index": assistant_row.get("index"),
            },
        )

    first_asst = get_first_assistant_message(thread_id, access_token)
    if (
        first_asst
        and assistant_row.get("index") != first_asst.get("index")
        and saved_assistant == (first_asst.get("content") or "").strip()
    ):
        logger.warning(
            "ASSISTANT_EQUALS_FIRST",
            extra={
                "thread_id": thread_id,
                "current_index": assistant_row.get("index"),
                "first_index": first_asst.get("index"),
            },
        )

    if settings.APP_ENV in ("dev", "local"):
        # Warn if echo
        if assistant_content.strip() == incoming.strip():
            logger.warning("[chat] assistant echoed user content", extra={"incoming_preview": incoming[:80]})

    return {
        "thread_id": thread_id,
        "user_content": content,
        "assistant_content": saved_assistant,
        "assistant_index": assistant_row.get("index"),
        "status": "saved",
    }
