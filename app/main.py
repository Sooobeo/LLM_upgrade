from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.routes import health, auth, thread


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
)

# CORS configuration kept permissive for now; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(thread.router)
app.include_router(auth.router)


@app.get("/_env_check")
def env_check():
    """
    Quick environment check for Supabase configuration.
    Do not expose in production environments without protection.
    """
    url = settings.SUPABASE_URL
    anon = settings.SUPABASE_ANON_KEY
    service_role = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    return {
        "url_set": bool(url),
        "anon_len": len(anon) if anon else 0,
        "has_service_role": bool(service_role),
    }


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
