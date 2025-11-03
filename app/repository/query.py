from supabase import Client
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime, timezone

def insert_thread(sb: Client, payload: Dict[str, Any]) -> str:
    thread_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    thread_data = {
        "id": thread_id,
        "title": payload["title"],
        "owner_id": payload["owner_id"],
        # created_at을 쓰는 스키마라면 created_at으로 저장하는 게 더 깔끔
        "created_at": timestamp,     # ← 권장
    }
    r = sb.table("threads").insert(thread_data).execute()
    if getattr(r, "error", None):
        raise RuntimeError(f"Failed to insert thread: {r.error}")
    return thread_id


def insert_messages(sb: Client, thread_id: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    messages: [{"role": "...", "content": "..."}, ...]
    """
    # 마지막 index 가져오기 (가장 큰 index 1개)
    r = (
        sb.table("messages")
        .select("index")
        .eq("thread_id", thread_id)
        .order("index", desc=True)
        .limit(1)                              # ← .range(1) 아님!
        .execute()
    )
    last_index = r.data[0]["index"] if (getattr(r, "data", None)) else -1

    now = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []
    for i, m in enumerate(messages, start=1):
        idx = last_index + i
        rows.append({
            "thread_id": thread_id,
            "role": m["role"],
            "content": m["content"],
            "index": idx,
            "created_at": now,     # 스키마가 created_at을 요구하므로 넣어두기

        })

    if rows:
        r2 = sb.table("messages").insert(rows).execute()
        if getattr(r2, "error", None):
            raise RuntimeError(f"Failed to insert messages: {r2.error}")

    return rows


def fetch_thread(sb: Client, thread_id: str) -> Dict[str, Any] | None:
    """
    특정 thread를 가져오되, ThreadOut / MessageOut 스키마와 맞는 구조로 정리해서 반환
    """
    r = (
        sb.table("threads")
        .select(
            "id, title, summary, tags, source_url, model, created_at"
            "messages(role, content, created_at)"
        )
        .eq("id", thread_id)
        .single()
        .execute()
    )

    if getattr(r, "error", None):
        raise RuntimeError(f"fetch_thread query error: {r.error}")
    if not r.data:
        return None

    t = r.data
    created_at = t.get("created_at")

    # messages를 스키마에 맞게 변환
    msgs_raw = t.get("messages") or []
    messages = [
        {
            "role": m["role"],
            "content": m["content"],
            "created_at": m.get("created_at"),
        }
        for m in msgs_raw
    ]

    return {
        "id": t["id"],
        "title": t["title"],
        "summary": t.get("summary"),
        "tags": t.get("tags") or [],
        "source_url": t.get("source_url"),
        "model": t.get("model"),
        "created_at": created_at,
        "messages": messages,
    }


def list_threads(sb: Client, owner_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    r = (
        sb.table("threads")
        .select("id,title,summary,tags,source_url,model,created_at")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    if getattr(r, "error", None):
        raise RuntimeError(f"list_threads query error: {r.error}")

    out = []
    for t in r.data or []:
        out.append({
            "id": t["id"],
            "title": t["title"],
            "summary": t.get("summary"),
            "tags": t.get("tags") or [],
            "source_url": t.get("source_url"),
            "model": t.get("model"),
            "created_at": t.get("created_at"),
            "messages": [],  
        })
    return out
