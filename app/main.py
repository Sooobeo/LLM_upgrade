from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from app.core.config import settings
from app.routes import auth, health, thread, user

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


@app.get("/")
def root():
    return {"ok": True, "service": "thread-api"}


# CORS (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(thread.router)
app.include_router(auth.router)
app.include_router(user.router)


# ==============================
# 1) Google ID Token exchange
#    POST /auth/google/exchange-id-token
# ==============================
@app.post("/auth/google/exchange-id-token")
async def exchange_id_token(payload: dict):
    """
    Exchange Google ID Token with Supabase Auth.
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

    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    supabase_anon_key = settings.SUPABASE_ANON_KEY

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=500,
            detail="missing settings.SUPABASE_URL / settings.SUPABASE_ANON_KEY",
        )

    url = f"{supabase_url}/auth/v1/token?grant_type=id_token"
    headers = {
        "Content-Type": "application/json",
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {supabase_anon_key}",
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
# 2) owner_id-based search (disabled placeholder)
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
    Placeholder: search messages by owner (currently disabled).
    """
    raise HTTPException(
        status_code=501,
        detail="search_messages_by_owner not implemented (/messages disabled)",
    )


# ==============================
# 3) Environment check
#    GET /_env_check
# ==============================
@app.get("/_env_check")
def env_check():
    """
    Quick env check for Supabase keys.
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
# 4) OpenAPI server URL customization
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
