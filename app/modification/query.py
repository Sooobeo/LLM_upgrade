# query.py

from supabase import Client
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime, timezone

def insert_thread(sb: Client, payload: Dict[str, Any]) -> str:
    
    thread_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    #initiation
    thread_data = {
        "id": thread_id,
        "title": payload["title"],
        "owner_id": payload["owner_id"],
        "updated_at": timestamp,
    }
    thread_res = sb.table("threads").insert(thread_data).execute()
    
    if getattr(thread_res, "error", None):
        raise RuntimeError(f"Failed to insert thread: {thread_res.error}")

    return thread_id

def insert_messages(sb: Client, thread_id, payload: Dict[str, Any]) -> str:
    
    messages_data = []
    
    last_index = (
        sb.table("messages")
        .select("order")
        .eq("thread_id", thread_id)
        .order("updated_at", desc=True)
        .range(1) #get only last appendix message's index
        .execute()
    )
    if last_index:
        last_index = int(last_index)

    for i, msg in enumerate(payload["messages"]):
        index = i+last_index
        message_id = f"{thread_id}__{index}"

        messages_data.append({
            "message_id": message_id,
            "thread_id": thread_id,
            "role": msg["role"], #user or GPT
            "content": msg["content"],
            "index": index,
        })

    if messages_data:
        messages_res = sb.table("messages").insert(messages_data).execute()
        if getattr(messages_res, "error", None):
            raise RuntimeError(f"Failed to insert messages: {messages_res.error}")
    
    return messages_data


def fetch_thread(sb: Client, thread_id: str) -> Dict[str, Any]:

    fetched_res = (
        sb.table("threads")
        .select("*, messages(*)")
        .eq("id", thread_id)
        .order("updated_at", desc=False, referenced_table="messages")
        .single()
        .execute()
    )    
    if getattr(fetched_res, "error", None):
        raise RuntimeError(f"fetch_thread query error: {fetched_res.error}")
        
    if not fetched_res.data:
        return None
        
    return fetched_res.data


def list_threads(sb: Client, owner_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    #query threads with created in certain time range
    title_res = (
        sb.table("threads")
        .select("id, title, updated_at")
        .eq("owner_id", owner_id)
        .order("updated_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    
    if getattr(title_res, "error", None):
        raise RuntimeError(f"list_threads query error: {title_res.error}")

    return title_res.data