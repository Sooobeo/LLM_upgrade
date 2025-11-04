from fastapi import Response
from datetime import timedelta
from app.core.config import settings

# 리프레시 쿠키 이름 통일
REFRESH_COOKIE_NAME = "refresh_token"

def set_refresh_cookie(response: Response, refresh_token: str, remember: bool = False):
    max_age = 60*60*24*30 if remember else 60*60*24*7  # 30일 or 7일
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # "lax" or "none"
        max_age=max_age,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )
