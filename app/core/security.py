from fastapi import HTTPException, Request, Response

from app.core.config import settings

# 리프레시 쿠키 이름 통일
REFRESH_COOKIE_NAME = "refresh_token"

def set_refresh_cookie(response: Response, refresh_token: str, remember: bool = False):
    max_age = 60*60*24*30 if remember else 60*60*24*7  # 30일 or 7일
    cookie_options = {
        "key": REFRESH_COOKIE_NAME,
        "value": refresh_token,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "max_age": max_age,
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        cookie_options["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(
        **cookie_options,
    )

def clear_refresh_cookie(response: Response):
    cookie_options = {
        "key": REFRESH_COOKIE_NAME,
        "path": "/",
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.COOKIE_DOMAIN:
        cookie_options["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(**cookie_options)


def require_trusted_origin(request: Request) -> None:
    origin = (request.headers.get("origin") or "").rstrip("/")
    fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
    if fetch_site == "cross-site" or (origin and origin not in settings.cors_origins):
        raise HTTPException(
            status_code=403,
            detail={"code": "UNTRUSTED_ORIGIN", "message": "Request origin is not allowed."},
        )
