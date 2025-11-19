# app/main.py
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.routes import health, auth, thread, message, ingest

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
)

# CORS (필요 시 조정)
app.add_middleware(
    CORSMiddleware(
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
)

# 라우터 연결
app.include_router(health.router)
app.include_router(thread.router)
app.include_router(message.router) 
app.include_router(auth.router)
app.include_router(ingest.router)


# ==============================
# 1) Google ID Token 교환 엔드포인트
#    POST /auth/google/exchange-id-token
# ==============================
@app.post("/auth/google/exchange-id-token")
async def exchange_id_token(payload: dict):
    """
    Google ID Token을 Supabase Auth로 교환하는 엔드포인트.
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
# 2) 환경 확인용 디버그 엔드포인트
#    GET /_env_check
# ==============================
@app.get("/_env_check")
def env_check():
    url = settings.SUPABASE_URL
    anon = settings.SUPABASE_ANON_KEY
    service_role = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    return {
        "url_set": bool(url),
        "anon_len": len(anon) if anon else 0,
        "has_service_role": bool(service_role),
    }


# ==============================
# 3) OpenAPI 서버 URL 커스터마이즈
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
