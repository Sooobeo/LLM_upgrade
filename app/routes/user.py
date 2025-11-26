from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.db.deps import get_access_token, get_current_user
from app.repository.extension_files import list_extension_files_for_user
from app.schemas.user import ExtensionFileListResp, UserOut

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Return the current authenticated user's basic profile.
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserOut(id=user_id, email=user.get("email"))


@router.get("/extension-files", response_model=ExtensionFileListResp)
async def list_extension_files(
    user: Dict[str, Any] = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """
    List extension file records belonging to the authenticated user.
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        items = list_extension_files_for_user(user_id, access_token)
    except Exception as exc:
        # Surface a controlled 500 error rather than letting lower-level exceptions bypass CORS handling.
        raise HTTPException(status_code=500, detail=f"Failed to load extension files: {exc}")
    return {"items": items}
