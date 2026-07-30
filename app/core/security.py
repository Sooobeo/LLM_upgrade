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
    # The deployed frontend and API normally use different sites
    # (for example, Vercel -> Render), so Sec-Fetch-Site is legitimately
    # "cross-site". In that case the explicit Origin allow-list is the trust
    # boundary. Reject cross-site requests without an Origin as well as any
    # request whose Origin is not allow-listed.
    origin_is_allowed = bool(origin) and origin in settings.cors_origins
    if (origin and not origin_is_allowed) or (fetch_site == "cross-site" and not origin_is_allowed):
        raise HTTPException(
            status_code=403,
            detail={"code": "UNTRUSTED_ORIGIN", "message": "Request origin is not allowed."},
        )
