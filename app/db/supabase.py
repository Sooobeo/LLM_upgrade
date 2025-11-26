from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
import requests
from supabase import Client, create_client

from app.core.config import settings


class ConfigError(RuntimeError):
    """환경 설정 관련 오류"""


class SupabaseAuthError(Exception):
    """Supabase 토큰 검증 실패용 커스텀 예외"""


def _get_env(name: str) -> Optional[str]:
    """settings에서 문자열 값을 읽어와 공백을 제거합니다."""
    v = getattr(settings, name, None)
    if isinstance(v, str):
        v = v.strip()
    return v or None


def _base_url() -> str:
    url = _get_env("SUPABASE_URL")
    if not url:
        raise ConfigError("SUPABASE_URL이 설정되어 있지 않습니다.")
    return url.rstrip("/")


def _base_headers() -> Dict[str, str]:
    anon = _get_env("SUPABASE_ANON_KEY")
    if not anon:
        raise ConfigError("SUPABASE_ANON_KEY가 설정되어 있지 않습니다.")
    return {"apikey": anon, "Content-Type": "application/json"}


@lru_cache(maxsize=2)
def get_supabase(service_role: bool = False) -> Client:
    """Supabase 파이썬 클라이언트 생성(캐시)."""
    url = _base_url()
    key_name = "SUPABASE_SERVICE_ROLE_KEY" if service_role else "SUPABASE_ANON_KEY"
    key = _get_env(key_name)
    if not key:
        raise ConfigError(f"{key_name}가 설정되어 있지 않습니다.")
    return create_client(url, key)


# ===== Auth / token helpers =====

def exchange_google_id_token(id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_base_url()}/auth/v1/token?grant_type=id_token"
    payload = {"provider": "google", "id_token": id_token}
    if nonce:
        payload["nonce"] = nonce
    r = requests.post(url, headers=_base_headers(), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def exchange_pkce_code(code: str, code_verifier: str, redirect_to: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_base_url()}/auth/v1/token?grant_type=pkce"
    payload: Dict[str, Any] = {"code": code, "code_verifier": code_verifier}
    if redirect_to:
        payload["redirect_to"] = redirect_to
    r = requests.post(url, headers=_base_headers(), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def refresh_with_token(refresh_token: str) -> Dict[str, Any]:
    url = f"{_base_url()}/auth/v1/token?grant_type=refresh_token"
    payload = {"refresh_token": refresh_token}
    r = requests.post(url, headers=_base_headers(), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def get_userinfo(access_token: str) -> Dict[str, Any]:
    url = f"{_base_url()}/auth/v1/user"
    headers = {**_base_headers(), "Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def logout(access_token: str) -> None:
    url = f"{_base_url()}/auth/v1/logout"
    headers = {**_base_headers(), "Authorization": f"Bearer {access_token}"}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()


def _auth_headers(access_token: str) -> Dict[str, str]:
    return {**_base_headers(), "Authorization": f"Bearer {access_token}"}


# ===== REST helpers =====

def rest_insert(table: str, rows: List[Dict[str, Any]], access_token: str) -> Dict[str, Any]:
    url = f"{_base_url()}/rest/v1/{table}"
    r = requests.post(url, headers=_auth_headers(access_token), json=rows, timeout=15)
    r.raise_for_status()
    return r.json() if r.text else {}


def rest_select(table: str, query: str, access_token: str) -> List[Dict[str, Any]]:
    url = f"{_base_url()}/rest/v1/{table}?{query}"
    r = requests.get(url, headers=_auth_headers(access_token), timeout=15)
    r.raise_for_status()
    return r.json()


def rest_delete(table: str, query: str, access_token: str) -> int:
    url = f"{_base_url()}/rest/v1/{table}?{query}"
    headers = {**_auth_headers(access_token), "Prefer": "return=representation"}
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


# ===== Access token validation =====
async def get_user_from_access_token(access_token: str) -> Dict[str, Any]:
    """
    Supabase access_token(JWT)을 넣으면 해당 유저 정보를 반환.
    토큰이 유효하지 않으면 SupabaseAuthError를 raise.
    """
    base_url = _base_url()
    api_key: Optional[str] = _get_env("SUPABASE_SERVICE_ROLE_KEY") or _get_env("SUPABASE_ANON_KEY")
    if not api_key:
        raise SupabaseAuthError("Supabase API 키가 설정되어 있지 않습니다.")

    url = f"{base_url}/auth/v1/user"
    headers = {"apikey": api_key, "Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise SupabaseAuthError(f"Supabase /auth/v1/user 호출 실패: {resp.status_code} {resp.text}")

    return resp.json()
