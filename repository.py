# app/repository.py
from __future__ import annotations
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime, timezone

# sb: supabase.Client

def insert_thread_and_messages(sb, payload: Dict[str, Any]) -> str:
    """
    payload = { title, owner_id, messages:[{role,content}, ...] }
    """
    thread_id = str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1) thread
    t = {
        "id": thread_id,
        "title": payload["title"],
        "owner_id": payload["owner_id"],
        "created_at": now_iso,  # 컬럼 default now()면 없어도 됨(있어도 OK)
    }
    r1 = sb.table("threads").insert(t).execute()
    if getattr(r1, "error", None):
        raise RuntimeError(f"threads insert error: {r1.error}")

    # 2) messages
    msgs: List[Dict[str, Any]] = []
    for m in payload.get("messages", []):
        msgs.append({
            "thread_id": thread_id,
            "role": m["role"],        # 'user' or 'assistant' (우리가 main에서 정규화)
            "content": m["content"],
            # "created_at": now_iso,  # DB default now() 있으면 주석
        })
    if msgs:
        r2 = sb.table("messages").insert(msgs).execute()
        if getattr(r2, "error", None):
            raise RuntimeError(f"messages insert error: {r2.error}")

    return thread_id

def create_thread_and_messages(*args, **kwargs):
    """
    Backward-compatible alias.
    예전 코드에서 쓰던 create_thread_and_messages 이름을
    지금 insert_thread_and_messages로 넘겨준다.
    """
    return insert_thread_and_messages(*args, **kwargs)


def fetch_thread(sb, thread_id: str) -> Dict[str, Any]:
    # thread 1건
    rt = sb.table("threads").select("*").eq("id", thread_id).single().execute()
    if getattr(rt, "error", None):
        raise RuntimeError(f"threads select error: {rt.error}")
    if not rt.data:
        raise RuntimeError("thread not found")

    # messages 시간 오름차순 (❗ asc 아님 → desc=False)
    rm = (
        sb.table("messages")
        .select("role,content,created_at")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    if getattr(rm, "error", None):
        raise RuntimeError(f"messages select error: {rm.error}")

    out = {
        "id": rt.data["id"],
        "title": rt.data.get("title"),
        "summary": rt.data.get("summary"),
        "tags": rt.data.get("tags") or [],
        "source_url": rt.data.get("source_url"),
        "model": rt.data.get("model"),
        "created_at": str(rt.data.get("created_at")),
        "messages": rm.data or [],
    }
    return out

def get_thread(*args, **kwargs):
    """
    Backward-compatible alias.
    예전 코드에서 쓰던 get_thread 이름을
    지금 fetch_thread 함수로 연결한다.
    """
    return fetch_thread(*args, **kwargs)


def list_threads(sb, owner_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    # 최신순(내림차순) → desc=True
    r = (
        sb.table("threads")
        .select("id,title,summary,tags,source_url,model,created_at")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .range(offset, offset + max(0, limit) - 1)
        .execute()
    )
    if getattr(r, "error", None):
        raise RuntimeError(f"threads list error: {r.error}")
    return r.data or []


## 20251113 추가기능 - owner_id 기준으로 messages 검색
def search_messages_by_owner(
    sb,
    owner_id: str,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    asc: bool = False,
) -> List[Dict[str, Any]]:
    """
    owner_id 기준으로, 그 유저의 모든 threads에 속한 messages를 가져오는 함수.
    선택적으로 q(검색어)로 content를 필터링한다.
    """
    # Supabase REST의 select 문자열과 동일한 구조
    select_cols = "thread_id,role,content,created_at,threads!inner(id,title,owner_id)"

    query = (
        sb.table("messages")
        .select(select_cols)
        .eq("threads.owner_id", owner_id)   # JOIN한 threads의 owner_id 기준 필터
        .order("created_at", desc=not asc)
        .range(offset, offset + max(0, limit) - 1)
    )

    # 검색어 q가 있으면 content 기준 ilike 필터 적용
    if q:
        query = query.ilike("content", f"%{q}%")

    r = query.execute()
    if getattr(r, "error", None):
        raise RuntimeError(f"messages search error: {r.error}")
    return r.data or []