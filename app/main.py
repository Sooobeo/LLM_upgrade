from typing import Optional
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.routes import auth, comment, health, thread, user, debug

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
)

# Allow common local origins; regex catches any localhost/127.* with arbitrary port.
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
CORS_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


@app.get("/")
def root():
    return {"ok": True, "service": "thread-api"}


# CORS (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lightweight startup confirmation (dev/local only) to verify the loaded module and CORS setup.
if settings.APP_ENV in ("dev", "local"):
    logging.getLogger(__name__).info(
        "CORS middleware enabled for origins=%s regex=%s (app.main:app)", CORS_ORIGINS, CORS_ORIGIN_REGEX
    )
    try:
        from app.services.llm_client import describe_llm_config

        cfg = describe_llm_config()
        logging.getLogger(__name__).info(
            "LLM config primary host=%s model=%s fallback host=%s model=%s",
            cfg["primary"]["host"],
            cfg["primary"]["model"],
            cfg["fallback"]["host"],
            cfg["fallback"]["model"],
        )
    except Exception as exc:  # pragma: no cover - defensive startup diagnostics
        logging.getLogger(__name__).warning("LLM config unavailable at startup: %s", exc)

# Routers
app.include_router(health.router)
app.include_router(thread.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(debug.router)
app.include_router(comment.router)
app.include_router(comment.branch_router)


# ==============================
# 1) owner_id-based search (disabled placeholder)
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
# 2) Environment check
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
# 3) OpenAPI server URL customization
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
