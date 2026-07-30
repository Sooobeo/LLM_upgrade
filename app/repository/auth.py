from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

from app.db import supabase as sb
from app.schemas.auth import AccessOnlyResp, GoogleExchangeResp, MeResp


def exchange_google_id_token(id_token: str) -> Tuple[GoogleExchangeResp, str]:
    try:
        data = sb.exchange_google_id_token(id_token)
        refresh = data.get("refresh_token")
        if not refresh:
            raise HTTPException(
                status_code=502,
                detail={"code": "SUPABASE_EXCHANGE_FAILED", "message": "No refresh token from Supabase"},
            )
        user = data.get("user") or {}
        response = GoogleExchangeResp(
            access_token=data.get("access_token"),
            token_type=data.get("token_type", "bearer"),
            expires_in=int(data.get("expires_in", 3600)),
            user={
                "id": user.get("id"),
                "email": user.get("email"),
                "provider": user.get("app_metadata", {}).get("provider", "google"),
                "created_at": user.get("created_at"),
            },
            issued_at=datetime.now(timezone.utc).isoformat(),
        )
        return response, refresh
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={"code": "SUPABASE_EXCHANGE_FAILED", "message": "Failed to exchange token with Supabase"},
        )


def refresh_with_cookie(refresh_token: str) -> Tuple[AccessOnlyResp, Optional[str]]:
    try:
        data = sb.refresh_with_token(refresh_token)
        response = AccessOnlyResp(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=int(data.get("expires_in", 3600)),
        )
        return response, data.get("refresh_token")
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired"},
        )


def current_user_profile(user_json: Dict[str, Any]) -> MeResp:
    identities = user_json.get("identities") or []
    user_metadata = user_json.get("user_metadata") or {}
    meta: Dict[str, Any] = {
        "name": user_metadata.get("name") or user_metadata.get("full_name"),
        "avatar_url": user_metadata.get("avatar_url"),
        "nickname": user_metadata.get("nickname"),
    }
    if identities:
        identity_data = identities[0].get("identity_data", {})
        meta["name"] = meta.get("name") or identity_data.get("name")
        meta["avatar_url"] = meta.get("avatar_url") or identity_data.get("avatar_url")
    meta = {key: value for key, value in meta.items() if value is not None}
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
    data = sb.signup_with_password(email, password, nickname)
    user = data.get("user") or {}
    user_id = user.get("id")
    if not user_id:
        raise ValueError("Supabase sign-up failed")
    return {
        "access_token": data.get("access_token"),
        "token_type": data.get("token_type"),
        "user_id": user_id,
        "email": email,
        "nickname": nickname,
    }
