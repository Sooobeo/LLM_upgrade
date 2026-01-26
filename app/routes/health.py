from fastapi import APIRouter

from app.services import llm_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/llm")
async def llm_health():
    return await llm_client.health_check()


@router.get("/llm/config")
def llm_config():
    return llm_client.describe_llm_config()
