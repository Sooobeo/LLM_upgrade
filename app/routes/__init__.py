from fastapi import APIRouter
from .health import router as health_router
from .diag import router as diag_router
from .threads import router as threads_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(diag_router)
api_router.include_router(threads_router)
