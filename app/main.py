from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.routes import health, auth, thread
from app.db.supabase import get_supabase
from app.repository import (
    # 필요한 것만 import – 지금은 search_messages_by_owner만 사용
    search_messages_by_owner,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
)

# CORS (필요 시 조정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

    # 팀 구조에서 이미 settings를 통해 SUPABASE 설정을 관리하므로 여기서 사용
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
        # Supabase 측에서 에러 응답을 주면 그대로 전달
        raise HTTPException(status_code=r.status_code, detail=data)

    return data


# ==============================
# 2) owner_id 기준 메시지 검색
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
    특정 owner_id의 모든 threads에 속한 messages 조회 + (선택) content 부분 검색.
    - owner_id: 필수. 이 유저의 threads에 속한 messages만 가져온다.
    - q: 선택. content에 q가 포함된 메시지만 필터 (부분 검색).
    - limit, offset: 페이징.
    """
    try:
        data = search_messages_by_owner(
            get_supabase(),  # app.db.supabase.get_supabase()
            owner_id=owner_id,
            q=q,
            limit=limit,
            offset=offset,
        )
        return data
    except Exception as e:
        # 내부 에러는 500으로 래핑
        raise HTTPException(
            status_code=500,
            detail=f"search_messages_by_owner failed: {e}",
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
# 4) OpenAPI 서버 URL 커스터마이즈 (팀 코드 유지)
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
