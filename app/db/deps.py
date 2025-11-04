from fastapi import Header, HTTPException
from typing import Optional
from app.db.supabase import get_userinfo

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    access_token = authorization.split(" ", 1)[1]
    try:
        return get_userinfo(access_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

async def get_access_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    return authorization.split(" ", 1)[1]