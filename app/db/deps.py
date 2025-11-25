from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, Request

from app.db.supabase import SupabaseAuthError, get_user_from_access_token


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Extract Supabase access_token from Authorization header (or fallback cookie)
    and return the Supabase user payload.
    """
    if not authorization:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            authorization = f"Bearer {cookie_token}"
        else:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "MISSING_ACCESS_TOKEN",
                    "message": "Authorization 헤더가 없습니다.",
                },
            )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_AUTH_HEADER",
                "message": "Authorization 헤더는 'Bearer <token>' 형식이어야 합니다.",
            },
        )

    access_token = parts[1].strip()
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "EMPTY_ACCESS_TOKEN",
                "message": "엑세스 토큰이 비어 있습니다.",
            },
        )

    try:
        supabase_user = await get_user_from_access_token(access_token)
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "유효하지 않은 엑세스 토큰입니다.",
                "debug": str(exc),
            },
        )

    return {
        "id": supabase_user.get("id"),
        "email": supabase_user.get("email"),
        "raw": supabase_user,
    }


async def get_access_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    return authorization.split(" ", 1)[1]
