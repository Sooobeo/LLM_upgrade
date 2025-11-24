from __future__ import annotations
import httpx
from app.core.config import settings
import requests
from typing import Dict, Any, Optional, List
from app.core.config import settings
# app/db/supabase.py
from supabase import create_client
from app.core.config import settings

def get_supabase(service_role: bool = False):
    key = settings.SUPABASE_SERVICE_ROLE_KEY if service_role else settings.SUPABASE_ANON_KEY
    return create_client(settings.SUPABASE_URL, key)


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

import requests
from typing import Dict, Any, Optional, List

from app.core.config import settings

# =========================
#  기존 REST 기반 설정
# =========================
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
        "Prefer": "return=representation"
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


# =========================
#  ① 네 db.py 로직 이식: supabase-py 클라이언트
# =========================
from functools import lru_cache
from supabase import create_client, Client


class ConfigError(RuntimeError):
    pass


def _get_env(name: str) -> Optional[str]:
    """
    settings에서 값 가져오되, 문자열이면 strip까지.
    name 예: 'SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY'
    """
    v = getattr(settings, name, None)
    if isinstance(v, str):
        v = v.strip()
    return v or None


# ✅ 1) anon 클라이언트 (기본)
@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_ANON_KEY")
    print(f"[supabase anon] URL? {bool(url)}  ANON_LEN: {len(key) if key else 0}")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / SUPABASE_ANON_KEY 누락")
    return create_client(url, key)


# ✅ 2) service_role 클라이언트 (필요한 경우에만 명시적으로)
@lru_cache(maxsize=1)
def get_supabase_service() -> Client:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    print(f"[supabase service] URL? {bool(url)}  SR_LEN: {len(key) if key else 0}")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 누락")
    return create_client(url, key)


# ✅ 3) 기존 코드 호환용: get_supabase()는 anon 반환
def get_supabase() -> Client:
    """
    기존 코드 호환용. 기본 anon 클라이언트 사용.
    """
    return get_supabase_anon()

# app/db/supabase.py




class SupabaseAuthError(Exception):
    """Supabase 토큰 검증 실패용 커스텀 예외"""
    pass


async def get_user_from_access_token(access_token: str) -> Dict[str, Any]:
    """
    Supabase access_token(JWT)을 넣으면 해당 유저 정보를 반환.
    토큰이 유효하지 않으면 SupabaseAuthError를 raise.
    """
    SUPABASE_URL = (settings.SUPABASE_URL or "").rstrip("/")
    if not SUPABASE_URL:
        raise SupabaseAuthError("SUPABASE_URL이 설정되어 있지 않습니다.")

    # 가능하면 SERVICE_ROLE, 없으면 일단 ANON 키라도 사용
    api_key: Optional[str] = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None) or settings.SUPABASE_ANON_KEY
    if not api_key:
        raise SupabaseAuthError("Supabase API 키가 설정되어 있지 않습니다.")

    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {access_token}",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        # 401/403/404 등은 모두 '토큰이 유효하지 않다'로 처리
        raise SupabaseAuthError(f"Supabase /auth/v1/user 호출 실패: {resp.status_code} {resp.text}")

    data = resp.json()
    return data  # Supabase User 객체(JSON)
