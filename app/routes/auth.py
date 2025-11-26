from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import clear_refresh_cookie, set_refresh_cookie
from app.db.deps import get_current_user
from app.repository.auth import (
    current_user_profile,
    exchange_google_id_token,
    refresh_with_cookie,
    revoke_if_possible,
    signup_with_password,
)
from app.schemas.auth import (
    AccessOnlyResp,
    GoogleExchangeBody,
    GoogleExchangeResp,
    MeResp,
    SignupPasswordReq,
    SignupPasswordResp,
)

router = APIRouter(prefix="/auth", tags=["auth"])

class GoogleRefreshBody(BaseModel):
    refresh_token: str


@router.get("/google/login", include_in_schema=False)
def google_login_route(redirect_to: Optional[str] = None):
    """
    Redirect to the Supabase-hosted Google OAuth page.
    Frontend hits /auth/google/login -> Supabase Google login page.
    If redirect_to is provided, Supabase will send the user there after login
    (must be allowed in Supabase project redirect settings).
    """
    base = settings.SUPABASE_URL.rstrip("/")
    query = {"provider": "google"}
    if redirect_to:
        query["redirect_to"] = redirect_to
    url = f"{base}/auth/v1/authorize?{urlencode(query)}"
    return RedirectResponse(url=url, status_code=302)


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
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token cookie missing"},
        )

    resp, new_refresh = refresh_with_cookie(refresh_token)
    if new_refresh:
        set_refresh_cookie(response, new_refresh, remember=False)
    return resp


@router.post("/google/set-session", response_model=AccessOnlyResp)
def google_set_session(body: GoogleRefreshBody, response: Response):
    """
    Set refresh cookie from Supabase-provided refresh_token (after hosted OAuth redirect).
    Frontend should send refresh_token parsed from the Supabase redirect hash.
    """
    resp, new_refresh = refresh_with_cookie(body.refresh_token)
    set_refresh_cookie(response, new_refresh or body.refresh_token, remember=False)
    return resp


@router.post("/logout")
def logout_route(response: Response, authorization: Optional[str] = Header(None)):
    access_token = None
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1]
    revoke_if_possible(access_token)
    clear_refresh_cookie(response)
    return {"ok": True}


class PasswordLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login/password")
async def login_with_password(payload: PasswordLoginRequest):
    """
    Login with email/password using Supabase Auth password grant.
    """

    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    anon_key = settings.SUPABASE_ANON_KEY

    if not supabase_url or not anon_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase configuration (SUPABASE_URL / SUPABASE_ANON_KEY) is missing.",
        )

    url = f"{supabase_url}/auth/v1/token?grant_type=password"
    headers = {
        "Content-Type": "application/json",
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
    }

    json_body = {"email": payload.email, "password": payload.password}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=json_body)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=data)

    return data


@router.post("/signup/password", response_model=SignupPasswordResp)
def signup_password(body: SignupPasswordReq):
    try:
        data = signup_with_password(body.email, body.password, body.nickname)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"signup failed: {e}")
