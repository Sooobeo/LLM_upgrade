import requests
from typing import Dict, Any, Optional, List
from app.core.config import settings

_BASE = settings.SUPABASE_URL.rstrip("/")
_HEADERS_BASE = {
    "apikey": settings.SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}

def exchange_google_id_token(id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=id_token"
    payload = {"provider": "google", "id_token": id_token}
    if nonce:
        payload["nonce"] = nonce
    r = requests.post(url, headers=_HEADERS_BASE, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def exchange_pkce_code(code: str, code_verifier: str, redirect_to: Optional[str]=None) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=pkce"
    payload = {"code": code, "code_verifier": code_verifier}
    if redirect_to:
        payload["redirect_to"] = redirect_to
    r = requests.post(url, headers=_HEADERS_BASE, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def refresh_with_token(refresh_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=refresh_token"
    payload = {"refresh_token": refresh_token}
    r = requests.post(url, headers=_HEADERS_BASE, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def get_userinfo(access_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/user"
    headers = {**_HEADERS_BASE, "Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def logout(access_token: str):
    url = f"{_BASE}/auth/v1/logout"
    headers = {**_HEADERS_BASE, "Authorization": f"Bearer {access_token}"}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()

def _auth_headers(access_token: str) -> Dict[str, str]:
    return {**_HEADERS_BASE, "Authorization": f"Bearer {access_token}"}

def rest_insert(table: str, rows: List[Dict[str, Any]], access_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/rest/v1/{table}"
    r = requests.post(url, headers=_auth_headers(access_token), json=rows, timeout=15)
    r.raise_for_status()
    return r.json() if r.text else {}

def rest_select(table: str, query: str, access_token: str) -> List[Dict[str, Any]]:
    # query 예: "owner_id=eq.<uuid>&select=id,title,created_at&order=created_at.desc&limit=20&offset=0"
    url = f"{_BASE}/rest/v1/{table}?{query}"
    r = requests.get(url, headers=_auth_headers(access_token), timeout=15)
    r.raise_for_status()
    return r.json()

def rest_delete(table: str, query: str, access_token: str) -> int:

    url = f"{_BASE}/rest/v1/{table}?{query}"
    headers = {
        **_auth_headers(access_token),
        "Prefer": "return=representation"  # ← 삭제된 행 목록을 JSON으로 반환
    }
    r = requests.delete(url, headers=headers, timeout=15)
    r.raise_for_status()
    if not r.text:
        return 0
    try:
        data = r.json()
        if isinstance(data, list):
            return len(data)
    except Exception:
        pass
    return 0