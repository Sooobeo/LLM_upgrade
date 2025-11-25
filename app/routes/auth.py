from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.security import REFRESH_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from app.db.deps import get_current_user
from app.repository.auth import (
    current_user_profile,
    exchange_google_id_token,
    refresh_with_cookie,
    revoke_if_possible,
    signup_with_email_password,
)
from app.schemas.auth import AccessOnlyResp, GoogleExchangeBody, GoogleExchangeResp, MeResp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/exchange-id-token", response_model=GoogleExchangeResp, status_code=200)
def google_exchange_id_token_route(body: GoogleExchangeBody, response: Response):
    resp, refresh_token = exchange_google_id_token(body.id_token)
    set_refresh_cookie(response, refresh_token=refresh_token, remember=False)
    return resp


@router.get("/me", response_model=MeResp)
def me_route(user: Dict[str, Any] = Depends(get_current_user)):
    return current_user_profile(user)


@router.post("/refresh", response_model=AccessOnlyResp)
def refresh_route(request: Request, response: Response):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token cookie missing"},
        )

    payload, new_refresh = refresh_with_cookie(refresh_token)
    if new_refresh:
        set_refresh_cookie(response, new_refresh, remember=False)
    return payload


@router.post("/logout")
def logout_route(response: Response, authorization: Optional[str] = Header(None)):
    access_token = None
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1]
    revoke_if_possible(access_token)
    clear_refresh_cookie(response)
    return {"ok": True}


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login/password")
async def login_with_password(payload: PasswordLoginRequest):
    """
    Supabase password sign-in proxy.
    """
    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    supabase_anon_key = settings.SUPABASE_ANON_KEY

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase settings (SUPABASE_URL / SUPABASE_ANON_KEY) are missing.",
        )

    url = f"{supabase_url}/auth/v1/token?grant_type=password"
    headers = {
        "Content-Type": "application/json",
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {supabase_anon_key}",
    }
    body = {"email": payload.email, "password": payload.password}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=body)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=data)

    return data


class PasswordSignupRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str


@router.post("/signup/password")
async def signup_with_password(payload: PasswordSignupRequest):
    """
    Supabase password sign-up proxy with nickname stored in user metadata.
    """
    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    supabase_anon_key = settings.SUPABASE_ANON_KEY
    if not supabase_url or not supabase_anon_key:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL / SUPABASE_ANON_KEY")

    status, data = await signup_with_email_password(payload.email, payload.password, payload.nickname)
    if status >= 400:
        raise HTTPException(status_code=status, detail=data)
    return data
