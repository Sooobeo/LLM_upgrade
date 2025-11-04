from __future__ import annotations
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response
from typing import Any, Dict, Optional
from app.core.security import set_refresh_cookie, clear_refresh_cookie
from app.db.deps import get_current_user
from app.schemas.auth import (
    GoogleExchangeBody, GoogleExchangeResp, MeResp, AccessOnlyResp
)
from app.repository.auth import (
    exchange_google_id_token, current_user_profile,
    refresh_with_cookie, revoke_if_possible
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/google/exchange-id-token", response_model=GoogleExchangeResp, status_code=200)
def google_exchange_id_token_route(body: GoogleExchangeBody, response: Response):
    resp, refresh_token = exchange_google_id_token(body.id_token)
    set_refresh_cookie(response, refresh_token=refresh_token, remember=False)
    return resp

@router.get("/me", response_model=MeResp)
def me_route(user: Dict[str, Any] = Depends(get_current_user)):
    return current_user_profile(user)

@router.post("/refresh", response_model=AccessOnlyResp)
def refresh_route(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token cookie missing"})

    resp, new_refresh = refresh_with_cookie(refresh_token)
    if new_refresh:
        set_refresh_cookie(response, new_refresh, remember=False)
    return resp

@router.post("/logout")
def logout_route(response: Response, authorization: Optional[str] = Header(None)):
    access_token = None
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1]
    revoke_if_possible(access_token)
    clear_refresh_cookie(response)
    return {"ok": True}
