from __future__ import annotations
from fastapi import Depends, Header, HTTPException
from app.db.supabase import get_userinfo
from typing import Any, Dict, Optional
from app.db.supabase import get_user_from_access_token, SupabaseAuthError


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Authorization: Bearer <Supabase access_token>을 받아서
    Supabase /auth/v1/user로 검증 후 유저 정보 반환.
    """

    if not authorization:
        # 헤더 자체가 없는 경우
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_ACCESS_TOKEN",
                "message": "Authorization 헤더가 없습니다.",
            },
        )

    # "Bearer xxx.yyy.zzz" 형식인지 확인
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
                "message": "액세스 토큰이 비어 있습니다.",
            },
        )

    try:
        supabase_user = await get_user_from_access_token(access_token)
    except SupabaseAuthError as e:
        # Supabase가 토큰을 인정하지 않는 경우
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "유효하지 않은 액세스 토큰입니다.",
                "debug": str(e),  # 운영에서는 빼도 됨
            },
        )

    # supabase_user 예시 구조(간략):
    # {
    #   "id": "uuid",
    #   "aud": "authenticated",
    #   "email": "xxx@yyy",
    #   "phone": null,
    #   "app_metadata": {...},
    #   "user_metadata": {...},
    #   "created_at": "...",
    #   ...
    # }

    # 나중에 repository/auth.current_user_profile에서 이 구조에 맞게 읽어 사용
    user: Dict[str, Any] = {
        "id": supabase_user.get("id"),
        "email": supabase_user.get("email"),
        "raw": supabase_user,  # 필요하면 전체 보관
    }
    return user


async def get_access_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    return authorization.split(" ", 1)[1]