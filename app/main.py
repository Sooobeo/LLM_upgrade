import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.middleware import RequestGuardMiddleware, SecurityHeadersMiddleware
from app.routes import auth, comment, health, thread, user, debug

missing_required_settings = settings.missing_required_settings
if missing_required_settings:
    logging.getLogger(__name__).critical(
        "Missing required backend environment variables: %s",
        ", ".join(missing_required_settings),
    )

production_docs_enabled = settings.APP_ENV.value != "prod" or settings.ENABLE_PRODUCTION_API_DOCS
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs" if production_docs_enabled else None,
    redoc_url="/redoc" if production_docs_enabled else None,
    openapi_url="/openapi.json" if production_docs_enabled else None,
)


@app.get("/")
def root():
    return {"ok": True, "service": "thread-api"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestGuardMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

# Lightweight startup confirmation (dev/local only) to verify the loaded module and CORS setup.
if settings.APP_ENV in ("dev", "local"):
    logging.getLogger(__name__).info(
        "CORS middleware enabled for origins=%s (app.main:app)",
        settings.cors_origins,
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
app.include_router(comment.router)
app.include_router(comment.branch_router)
if settings.APP_ENV.value != "prod":
    app.include_router(debug.router)

    @app.get("/_env_check", include_in_schema=False)
    def env_check():
        return {
            "url_set": bool(settings.SUPABASE_URL),
            "has_anon_key": bool(settings.SUPABASE_ANON_KEY),
            "has_service_role": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
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
