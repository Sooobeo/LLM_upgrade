from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

from app.db import supabase as sb
from app.schemas.auth import AccessOnlyResp, GoogleExchangeResp, MeResp


def exchange_google_id_token(id_token: str) -> Tuple[GoogleExchangeResp, str]:
    """Supabase로 Google ID 토큰을 교환하고 refresh_token을 함께 반환합니다."""
    try:
        data = sb.exchange_google_id_token(id_token)
        refresh = data.get("refresh_token")
        if not refresh:
            raise HTTPException(
                status_code=502,
                detail={"code": "SUPABASE_EXCHANGE_FAILED", "message": "No refresh_token from Supabase"},
            )

        access_token = data.get("access_token")
        token_type = data.get("token_type", "bearer")
        expires_in = int(data.get("expires_in", 3600))
        user = data.get("user", {}) or {}

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
            detail={"code": "SUPABASE_EXCHANGE_FAILED", "message": f"Failed to exchange token with Supabase: {e}"},
        )


def refresh_with_cookie(refresh_token: str) -> Tuple[AccessOnlyResp, Optional[str]]:
    """Refresh 토큰을 사용해 액세스 토큰을 재발급합니다."""
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
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired"},
        )


def current_user_profile(user_json: Dict[str, Any]) -> MeResp:
    identities = user_json.get("identities") or []
    meta: Dict[str, Any] = {}
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


def signup_with_password(email: str, password: str, nickname: str) -> Dict[str, Any]:
    """Supabase Auth 회원가입 후 profiles 테이블에 닉네임을 저장합니다."""
    client = sb.get_supabase(service_role=True)

    # 1) Supabase Auth signUp
    auth_res = client.auth.sign_up({"email": email, "password": password})
    if auth_res.user is None:
        raise ValueError("Supabase sign_up failed")

    user = auth_res.user
    session = auth_res.session  # 이메일 인증 OFF면 session이 올 수도 있음
    user_id = user.id

    # 2) profiles insert
    client.table("profiles").insert({"id": user_id, "email": email, "nickname": nickname}).execute()

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
