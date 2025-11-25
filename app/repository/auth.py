from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.db import supabase as sb
from app.schemas.auth import AccessOnlyResp, GoogleExchangeResp, MeResp


def exchange_google_id_token(id_token: str) -> Tuple[GoogleExchangeResp, str]:
    """
    Exchange a Google ID token with Supabase and return (response payload, refresh_token).
    """
    try:
        data = sb.exchange_google_id_token(id_token)
        refresh = data.get("refresh_token")
        if not refresh:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "SUPABASE_EXCHANGE_FAILED",
                    "message": "No refresh_token returned from Supabase",
                },
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
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "SUPABASE_EXCHANGE_FAILED",
                "message": f"Failed to exchange token with Supabase: {exc}",
            },
        )


def refresh_with_cookie(refresh_token: str) -> Tuple[AccessOnlyResp, Optional[str]]:
    """
    Refresh an access token using a refresh token stored in cookies.
    Returns (payload, maybe_new_refresh_token).
    """
    try:
        data = sb.refresh_with_token(refresh_token)
        resp = AccessOnlyResp(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=int(data.get("expires_in", 3600)),
        )
        return resp, data.get("refresh_token")  # Supabase may rotate refresh tokens
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": "Refresh token is invalid or expired",
            },
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
    return MeResp(id=user_json.get("id"), email=user_json.get("email"), meta=meta or None)


def revoke_if_possible(access_token: Optional[str]) -> None:
    if not access_token:
        return
    try:
        sb.logout(access_token)
    except Exception:
        pass


async def signup_with_email_password(email: str, password: str, nickname: str):
    """
    Sign up a user via Supabase email/password and attach nickname as user metadata.
    Returns (status_code, response_json)
    """
    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    anon_key = settings.SUPABASE_ANON_KEY

    url = f"{supabase_url}/auth/v1/signup"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json",
    }
    payload = {"email": email, "password": password, "data": {"nickname": nickname}}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=payload)

    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"raw": resp.text}
