from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import os, httpx

from app.db import get_supabase
from app.repository import (
    insert_thread_and_messages,
    fetch_thread,
    list_threads,
    search_messages_by_owner,
)

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/google/exchange-id-token")
async def exchange_id_token(payload: dict):
    # 기대 바디: { provider, id_token, client_id, (nonce?) }
    required = ["provider", "id_token", "client_id"]
    if any(k not in payload for k in required):
        raise HTTPException(status_code=400, detail={"error":"missing fields","got":list(payload.keys())})

    SUPABASE_URL = os.environ.get("SUPABASE_URL")    # e.g. https://<project>.supabase.co
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="missing env SUPABASE_URL / SUPABASE_ANON_KEY")

    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=id_token"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json=payload)

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=data)

    return data

# 20251113 추가기능 - owner_id 기준으로 messages 검색
from app.repository import (
    insert_thread_and_messages,
    fetch_thread,
    list_threads,
    search_messages_by_owner, 
)


@app.get("/messages")
def get_messages(
    owner_id: str,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    특정 owner_id의 모든 스레드에 속한 메시지들을 조회.
    - owner_id: 필수. 이 유저의 threads에 속한 messages만 가져온다.
    - q: 선택. content에 q가 포함된 메시지만 필터 (부분 검색).
    """
    try:
        data = search_messages_by_owner(
            get_supabase(),
            owner_id=owner_id,
            q=q,
            limit=limit,
            offset=offset,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"search_messages_by_owner failed: {e}")

# 어디서 무슨 키를 읽었는지 확인
@app.get("/_env_check")
def env_check():
    import os
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return {
        "url_set": bool(url),
        "key_len": len(key) if key else 0,
        "has_service_role": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "has_anon": bool(os.getenv("SUPABASE_ANON_KEY")),
    }

@app.get("/_env_check")
def env_check():
    import os
    url = os.getenv("SUPABASE_URL")
    anon = os.getenv("SUPABASE_ANON_KEY")
    return {
        "SUPABASE_URL": url,
        "ANON_LEN": len(anon) if anon else 0,
    }