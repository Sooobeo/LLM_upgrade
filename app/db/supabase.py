import requests
from typing import Dict, Any, Optional
from app.core.config import settings

_BASE = settings.SUPABASE_URL.rstrip("/")
_HEADERS = {
    "apikey": settings.SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}

def exchange_google_id_token(id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=id_token"
    payload = {"provider": "google", "id_token": id_token}
    if nonce:
        payload["nonce"] = nonce
    r = requests.post(url, headers=_HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def exchange_pkce_code(code: str, code_verifier: str, redirect_to: Optional[str]=None) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=pkce"
    payload = {"code": code, "code_verifier": code_verifier}
    if redirect_to:
        payload["redirect_to"] = redirect_to
    r = requests.post(url, headers=_HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def refresh_with_token(refresh_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=refresh_token"
    payload = {"refresh_token": refresh_token}
    r = requests.post(url, headers=_HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def get_userinfo(access_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/user"
    headers = {**_HEADERS, "Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def logout(access_token: str):
    url = f"{_BASE}/auth/v1/logout"
    headers = {**_HEADERS, "Authorization": f"Bearer {access_token}"}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()
