# app/repository/auth.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException
from app.db import supabase as sb
from app.schemas.auth import GoogleExchangeResp, AccessOnlyResp, MeResp

def exchange_google_id_token(id_token: str) -> Tuple[GoogleExchangeResp, str]:
    """
    return: (응답 스펙 객체, refresh_token)
    """
    try:
        data = sb.exchange_google_id_token(id_token)
        refresh = data.get("refresh_token")
        if not refresh:
            raise HTTPException(status_code=502, detail={"code": "SUPABASE_EXCHANGE_FAILED", "message": "No refresh_token from Supabase"})

        access_token = data.get("access_token")
        token_type   = data.get("token_type", "bearer")
        expires_in   = int(data.get("expires_in", 3600))
        user         = data.get("user", {}) or {}

        resp = GoogleExchangeResp(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            user={
                "id": user.get("id"),
                "email": user.get("email"),
                "provider": user.get("app_metadata", {}).get("provider", "google"),
                "created_at": user.get("created_at"),
            },
            issued_at=datetime.now(timezone.utc).isoformat(),
        )
        return resp, refresh
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "SUPABASE_EXCHANGE_FAILED", "message": f"Failed to exchange token with Supabase: {e}"}
        )

def refresh_with_cookie(refresh_token: str) -> Tuple[AccessOnlyResp, Optional[str]]:
    """
    return: (응답 스펙 객체, 새 refresh_token 있으면 그 값 / 없으면 None)
    """
    try:
        data = sb.refresh_with_token(refresh_token)
        resp = AccessOnlyResp(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=int(data.get("expires_in", 3600)),
        )
        return resp, data.get("refresh_token")  # 새 토큰 있을 수도, 없을 수도
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired"}
        )

def current_user_profile(user_json: Dict[str, Any]) -> MeResp:
    identities = user_json.get("identities") or []
    meta = {}
    if identities:
        prv = identities[0]
        meta = {
            "name": prv.get("identity_data", {}).get("name"),
            "avatar_url": prv.get("identity_data", {}).get("avatar_url"),
        }
    return MeResp(
        id=user_json.get("id"),
        email=user_json.get("email"),
        meta=meta or None,
    )

def revoke_if_possible(access_token: Optional[str]) -> None:
    if not access_token:
        return
    try:
        sb.logout(access_token)
    except Exception:
        pass

# app/repository/auth.py
import httpx
from app.core.config import settings

async def signup_with_email_password(email: str, password: str, nickname: str):
    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    anon_key = settings.SUPABASE_ANON_KEY

    url = f"{supabase_url}/auth/v1/signup"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
        "data": { "nickname": nickname },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json=payload)

    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}

# app/repository/auth.py
from app.db.supabase import get_supabase

def signup_with_password(email: str, password: str, nickname: str):
    sb = get_supabase()

    # 1) Supabase Auth signUp
    auth_res = sb.auth.sign_up({"email": email, "password": password})
    if auth_res.user is None:
        # supabase-py가 에러를 던질 수도 있고, user=None으로 올 수도 있음
        raise ValueError("Supabase sign_up failed")

    user = auth_res.user
    session = auth_res.session  # 이메일 인증 OFF면 session이 올 수도 있음

    user_id = user.id

    # 2) profiles insert
    # sign_up 직후에는 auth.uid()가 없으니 anon key + service role이 필요할 수 있음.
    # 지금은 backend에서 service role로 insert하는 방식으로 가자.
    insert_res = (
        sb.table("profiles")
        .insert({"id": user_id, "email": email, "nickname": nickname})
        .execute()
    )

    # 3) 응답 구성
    access_token = session.access_token if session else None
    token_type = session.token_type if session else None

    return {
        "access_token": access_token,
        "token_type": token_type,
        "user_id": user_id,
        "email": email,
        "nickname": nickname,
    }
