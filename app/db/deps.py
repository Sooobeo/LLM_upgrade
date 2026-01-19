from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import SupabaseAuthError, get_user_from_access_token

# Swagger/OpenAPI에서 Bearer 인증 스킴을 인식시키기 위해 HTTPBearer 사용
_bearer_scheme = HTTPBearer(auto_error=False)


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """
    Extract access_token from Authorization header.

    Contract (single source of truth):
      Authorization: Bearer <access_token>
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        # Swagger/Postman/FE 공통: 토큰이 없거나 형식이 다르면 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "MISSING_ACCESS_TOKEN",
                "message": "Authorization 헤더가 없습니다.",
            },
        )

    access_token = (credentials.credentials or "").strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "EMPTY_ACCESS_TOKEN",
                "message": "엑세스 토큰이 비어 있습니다.",
            },
        )

    return access_token


async def get_current_user(
    access_token: str = Depends(get_access_token),
) -> Dict[str, Any]:
    """
    Validate Supabase access_token via Supabase Auth (/auth/v1/user)
    and return a normalized user payload.

    This function must NOT parse headers/cookies directly.
    Token extraction responsibility is in get_access_token().
    """
    try:
        supabase_user = await get_user_from_access_token(access_token)
    except SupabaseAuthError:
        # 보안상 debug 세부 내용을 기본 응답에 포함하지 않는 것을 권장
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "유효하지 않거나 만료된 엑세스 토큰입니다.",
            },
        )

    user_id = supabase_user.get("id")
    if not user_id:
        # supabase 응답이 예상과 다르거나 비정상인 경우
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN_PAYLOAD",
                "message": "토큰에서 사용자 정보를 확인할 수 없습니다.",
            },
        )

    return {
        "id": user_id,
        "email": supabase_user.get("email"),
        "raw": supabase_user,
    }
