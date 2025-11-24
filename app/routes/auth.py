from __future__ import annotations
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response
from typing import Any, Dict, Optional
from app.core.security import set_refresh_cookie, clear_refresh_cookie
from app.db.deps import get_current_user
from app.schemas.auth import (
    GoogleExchangeBody, GoogleExchangeResp, MeResp, AccessOnlyResp
)
from app.repository.auth import (
    exchange_google_id_token, current_user_profile,
    refresh_with_cookie, revoke_if_possible
)

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
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token cookie missing"})

    resp, new_refresh = refresh_with_cookie(refresh_token)
    if new_refresh:
        set_refresh_cookie(response, new_refresh, remember=False)
    return resp

@router.post("/logout")
def logout_route(response: Response, authorization: Optional[str] = Header(None)):
    access_token = None
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1]
    revoke_if_possible(access_token)
    clear_refresh_cookie(response)
    return {"ok": True}

from pydantic import BaseModel
import httpx
from app.core.config import settings

# 이메일/비밀번호 로그인용 요청 스키마
class PasswordLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login/password")
async def login_with_password(payload: PasswordLoginRequest):
    """
    이메일 + 비밀번호로 Supabase Auth에 로그인하는 엔드포인트.

    1) 프론트에서 /auth/login/password 에 {email, password} JSON으로 POST
    2) 여기서 Supabase /auth/v1/token?grant_type=password 로 proxy 호출
    3) Supabase가 돌려주는 access_token + user 정보를 그대로 프론트에 반환
    """

    SUPABASE_URL = (settings.SUPABASE_URL or "").rstrip("/")
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=500,
            detail="Supabase 설정(SUPABASE_URL / SUPABASE_ANON_KEY)이 비어 있습니다.",
        )

    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }

    json_body = {
        "email": payload.email,
        "password": payload.password,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=json_body)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        # Supabase가 주는 에러 그대로 전달
        raise HTTPException(status_code=resp.status_code, detail=data)

    # 예: Supabase 응답 예시
    # {
    #   "access_token": "...",
    #   "token_type": "bearer",
    #   "expires_in": 3600,
    #   "user": { "id": "...", ... }
    # }
    return data

# app/routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase import get_supabase
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class SignupPasswordBody(BaseModel):
    nickname: str
    email: str
    password: str

@router.post("/signup/password")
def signup_password(body: SignupPasswordBody):
    sb = get_supabase()

    # 1) Supabase Auth signUp
    try:
        auth_res = sb.auth.sign_up({
            "email": body.email,
            "password": body.password
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = auth_res.user
    if not user:
        raise HTTPException(status_code=400, detail="Signup failed: no user returned")

    user_id = user.id

    # 2) profiles 테이블에 nickname 저장
    try:
        sb.table("profiles").insert({
            "id": user_id,
            "nickname": body.nickname
        }).execute()
    except Exception as e:
        # profiles insert가 실패해도 auth 유저는 만들어졌으니
        # 원인만 안내
        raise HTTPException(status_code=500, detail=f"profile insert failed: {e}")

    return {
        "ok": True,
        "user_id": user_id,
        "email": body.email,
        "nickname": body.nickname
    }

# app/routes/auth.py
from fastapi import APIRouter, HTTPException
from app.schemas.auth import SignupPasswordReq, SignupPasswordResp
from app.repository.auth import signup_with_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup/password", response_model=SignupPasswordResp)
def signup_password(body: SignupPasswordReq):
    try:
        data = signup_with_password(body.email, body.password, body.nickname)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"signup failed: {e}")

# app/routes/auth.py

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import httpx
from app.core.config import settings
from app.db.supabase import get_supabase  # 이미 있으면 그대로

router = APIRouter(prefix="/auth", tags=["auth"])

class PasswordSignupRequest(BaseModel):
    email: str
    password: str
    nickname: str  # FE에서 받을 닉네임

@router.post("/signup/password")
async def signup_with_password(payload: PasswordSignupRequest):
    """
    1) Supabase Auth 회원가입
    2) profiles 테이블에 nickname 저장
    """
    SUPABASE_URL = (settings.SUPABASE_URL or "").rstrip("/")
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY
    SERVICE_ROLE = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(500, detail="Supabase URL/ANON_KEY missing")

    # 1) Supabase Auth signup
    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    body = {"email": payload.email, "password": payload.password}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=body)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        # Supabase가 주는 에러 그대로 전달
        raise HTTPException(status_code=resp.status_code, detail=data)

    # data 안에 user.id가 들어있음 (인증 메일 켜져 있으면 session은 없을 수도)
    user_id = data.get("user", {}).get("id")
    if not user_id:
        # 가입 OK인데 user가 안 들어오면 여기서 끝내도 됨
        return data

    # 2) profiles 저장
    # RLS 켜져 있으면 서비스롤로 넣는 게 안전
    if not SERVICE_ROLE:
        # 서비스롤 없으면 그냥 Auth 결과만 반환
        return data

    supabase_admin = get_supabase(service_role=True)  # 아래 get_supabase 수정 필요(2번)
    ins = (
        supabase_admin.table("profiles")
        .insert({"id": user_id, "email": payload.email, "nickname": payload.nickname})
        .execute()
    )

    return {
        **data,
        "profile_saved": True,
        "profile": ins.data[0] if ins.data else None,
    }
