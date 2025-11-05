from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from app.core.config import settings
from app.routes import health, auth, thread
from app.db.supabase import get_supabase  # 지금은 안 쓰여도 일단 둠


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# CORS (필요 시 조정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 시에는 특정 도메인으로 제한하는 것이 좋음
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 연결
app.include_router(health.router)
app.include_router(thread.router)
app.include_router(auth.router)




# ==============================
# 1) Google ID Token 교환 엔드포인트
#    POST /auth/google/exchange-id-token
# ==============================
@app.post("/auth/google/exchange-id-token")
async def exchange_id_token(payload: dict):
    """
    Google ID Token을 Supabase Auth로 교환하는 엔드포인트.

    기대 바디 예시:
    {
      "provider": "google",
      "id_token": "...",
      "client_id": "...",
      "nonce": "..." (옵션)
    }
    """
    required = ["provider", "id_token", "client_id"]
    if any(k not in payload for k in required):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing fields",
                "required": required,
                "got": list(payload.keys()),
            },
        )

    SUPABASE_URL = (settings.SUPABASE_URL or "").rstrip("/")
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=500,
            detail="missing settings.SUPABASE_URL / settings.SUPABASE_ANON_KEY",
        )

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


# ==============================
# 2) owner_id 기준 메시지 검색 (임시 비활성)
#    GET /messages
# ==============================
@app.get("/messages")
def get_messages(
    owner_id: str,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    [미구현] 특정 owner_id의 모든 threads에 속한 messages 조회 + (선택) content 부분 검색.

    지금은 BE 레포지토리에 search_messages_by_owner 함수가 없어서
    임시로 501 에러를 반환하도록 두었어.

    나중에 구현되면:
    - app.repository 쪽에 search_messages_by_owner(supabase, owner_id, q, limit, offset)
      함수 만든 다음
    - 여기서 그 함수를 호출하도록 수정하면 돼.
    """
    raise HTTPException(
        status_code=501,
        detail="search_messages_by_owner 미구현(/messages 임시 비활성 상태)",
    )


# ==============================
# 3) 환경 확인용 디버그 엔드포인트
#    GET /_env_check
# ==============================
@app.get("/_env_check")
def env_check():
    """
    Supabase 관련 설정이 제대로 들어가 있는지 확인용 디버그 엔드포인트.
    실제 운영에서는 제거하거나 보호 필요.
    """
    url = settings.SUPABASE_URL
    anon = settings.SUPABASE_ANON_KEY
    service_role = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    return {
        "url_set": bool(url),
        "anon_len": len(anon) if anon else 0,
        "has_service_role": bool(service_role),
    }


# ==============================
# 4) OpenAPI 서버 URL 커스터마이즈
# ==============================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["servers"] = [{"url": settings.OPENAPI_SERVER_URL}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

# app/main.py
from fastapi import FastAPI, HTTPException
import os, httpx

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

# app/main.py
from fastapi import FastAPI, HTTPException
import os, httpx

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
