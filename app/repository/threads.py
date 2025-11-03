
from typing import Any, Dict, List, Optional
from app.repository import query 

def insert_thread(sb: Any, payload: Dict) -> str:
    return query.insert_thread(sb, payload)

def insert_messages(sb: Any, thread_id: str, messages: List[Dict]) -> Dict:
    return query.insert_messages(sb, thread_id, messages)

def fetch_thread(sb: Any, thread_id: str) -> Optional[Dict]:
    return query.fetch_thread(sb, thread_id)

def list_threads(sb: Any, owner_id: str, limit: int, offset: int):
    return query.list_threads(sb, owner_id=owner_id, limit=limit, offset=offset)
