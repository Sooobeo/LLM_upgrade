from fastapi import APIRouter, Depends

from app.db.deps import get_current_user
from app.services import llm_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/llm")
async def llm_health(_user=Depends(get_current_user)):
    return await llm_client.health_check()


@router.get("/llm/config")
def llm_config(_user=Depends(get_current_user)):
    return llm_client.describe_llm_config()
