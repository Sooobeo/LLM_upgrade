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


# OpenAPI 서버 URL 커스터마이즈 (선택)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes
    )
    schema["servers"] = [{"url": settings.OPENAPI_SERVER_URL}]
    app.openapi_schema = schema
    return schema
app.openapi = custom_openapi
