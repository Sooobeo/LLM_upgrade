from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.core.security import clear_refresh_cookie, require_trusted_origin, set_refresh_cookie
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
    refresh_token: str = Field(..., min_length=20, max_length=4096)


class GoogleLoginUrlResponse(BaseModel):
    authorize_url: str


def _google_authorize_url(redirect_to: Optional[str] = None) -> str:
    if settings.missing_required_settings:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AUTH_NOT_CONFIGURED",
                "message": "로그인 서버의 Supabase 설정이 누락되었습니다.",
            },
        )

    base = settings.SUPABASE_URL.rstrip("/")
    query = {"provider": "google"}
    if redirect_to:
        parsed = urlsplit(redirect_to)
        redirect_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not settings.is_allowed_origin(redirect_origin)
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_REDIRECT",
                    "message": "현재 사이트 주소가 Google 로그인 허용 목록에 없습니다.",
                },
            )
        oauth_redirect_to = redirect_to
        if settings.APP_ENV.value == "prod" and settings.GOOGLE_OAUTH_REDIRECT_URL:
            configured_redirect = settings.GOOGLE_OAUTH_REDIRECT_URL.strip()
            configured = urlsplit(configured_redirect)
            configured_origin = (
                f"{configured.scheme}://{configured.netloc}".rstrip("/")
            )
            if (
                configured.scheme != "https"
                or not configured.netloc
                or not settings.is_allowed_origin(configured_origin)
            ):
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "INVALID_OAUTH_CONFIG",
                        "message": "Google 로그인 callback 설정이 올바르지 않습니다.",
                    },
                )
            oauth_redirect_to = configured_redirect
        query["redirect_to"] = oauth_redirect_to
    return f"{base}/auth/v1/authorize?{urlencode(query)}"


@router.get(
    "/google/url",
    response_model=GoogleLoginUrlResponse,
    include_in_schema=False,
)
def google_login_url_route(redirect_to: Optional[str] = None):
    """Return the hosted OAuth URL so the frontend can handle loading/errors."""
    return GoogleLoginUrlResponse(
        authorize_url=_google_authorize_url(redirect_to),
    )


@router.get("/google/login", include_in_schema=False)
def google_login_route(redirect_to: Optional[str] = None):
    """
    Redirect to the Supabase-hosted Google OAuth page.
    Frontend hits /auth/google/login -> Supabase Google login page.
    If redirect_to is provided, Supabase will send the user there after login
    (must be allowed in Supabase project redirect settings).
    """
    return RedirectResponse(
        url=_google_authorize_url(redirect_to),
        status_code=302,
    )


@router.post("/google/exchange-id-token", response_model=GoogleExchangeResp, status_code=200)
def google_exchange_id_token_route(body: GoogleExchangeBody, request: Request, response: Response):
    require_trusted_origin(request)
    resp, refresh_token = exchange_google_id_token(body.id_token)
    set_refresh_cookie(response, refresh_token=refresh_token, remember=False)
    return resp


@router.get("/me", response_model=MeResp)
def me_route(user: Dict[str, Any] = Depends(get_current_user)):
    return current_user_profile(user)


@router.post("/refresh", response_model=AccessOnlyResp)
def refresh_route(request: Request, response: Response):
    require_trusted_origin(request)
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
def google_set_session(body: GoogleRefreshBody, request: Request, response: Response):
    """
    Set refresh cookie from Supabase-provided refresh_token (after hosted OAuth redirect).
    Frontend should send refresh_token parsed from the Supabase redirect hash.
    """
    require_trusted_origin(request)
    resp, new_refresh = refresh_with_cookie(body.refresh_token)
    set_refresh_cookie(response, new_refresh or body.refresh_token, remember=False)
    return resp


@router.post("/logout")
def logout_route(request: Request, response: Response, authorization: Optional[str] = Header(None)):
    require_trusted_origin(request)
    access_token = None
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1]
    revoke_if_possible(access_token)
    clear_refresh_cookie(response)
    return {"ok": True}


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/login/password", response_model=AccessOnlyResp)
async def login_with_password(payload: PasswordLoginRequest, request: Request, response: Response):
    """
    Login with email/password using Supabase Auth password grant.
    """

    require_trusted_origin(request)
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

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect."},
        )

    data = resp.json()
    refresh_token = data.get("refresh_token")
    access_token = data.get("access_token")
    if not refresh_token or not access_token:
        raise HTTPException(status_code=502, detail="Authentication provider returned an invalid response.")
    set_refresh_cookie(response, refresh_token, remember=False)
    return AccessOnlyResp(
        access_token=access_token,
        token_type=data.get("token_type", "bearer"),
        expires_in=int(data.get("expires_in", 3600)),
    )


@router.post("/signup/password", response_model=SignupPasswordResp)
def signup_password(body: SignupPasswordReq, request: Request):
    require_trusted_origin(request)
    try:
        data = signup_with_password(body.email, body.password, body.nickname)
        return data
    except ValueError:
        raise HTTPException(status_code=400, detail="Unable to create account.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to create account.")
