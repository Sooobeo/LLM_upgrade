from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
import requests
from supabase import Client, create_client

from app.core.config import settings

# Base REST settings
_BASE = settings.SUPABASE_URL.rstrip("/")
_HEADERS_BASE = {
    "apikey": settings.SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}


class ConfigError(RuntimeError):
    pass


class SupabaseAuthError(Exception):
    """Raised when validating an access token with Supabase fails."""


def _get_env(name: str) -> Optional[str]:
    """
    Fetch setting value as a stripped string.
    name: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
    """
    value = getattr(settings, name, None)
    if isinstance(value, str):
        value = value.strip()
    return value or None


@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / SUPABASE_ANON_KEY missing")
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_service() -> Client:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing")
    return create_client(url, key)


def get_supabase(service_role: bool = False) -> Client:
    """Compatibility wrapper to fetch anon (default) or service role client."""
    return get_supabase_service() if service_role else get_supabase_anon()


# --- REST helpers -----------------------------------------------------------
def exchange_google_id_token(id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=id_token"
    payload: Dict[str, Any] = {"provider": "google", "id_token": id_token}
    if nonce:
        payload["nonce"] = nonce
    resp = requests.post(url, headers=_HEADERS_BASE, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def exchange_pkce_code(code: str, code_verifier: str, redirect_to: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=pkce"
    payload: Dict[str, Any] = {"code": code, "code_verifier": code_verifier}
    if redirect_to:
        payload["redirect_to"] = redirect_to
    resp = requests.post(url, headers=_HEADERS_BASE, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def refresh_with_token(refresh_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/token?grant_type=refresh_token"
    payload = {"refresh_token": refresh_token}
    resp = requests.post(url, headers=_HEADERS_BASE, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_userinfo(access_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/auth/v1/user"
    headers = {**_HEADERS_BASE, "Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def logout(access_token: str) -> None:
    url = f"{_BASE}/auth/v1/logout"
    headers = {**_HEADERS_BASE, "Authorization": f"Bearer {access_token}"}
    resp = requests.post(url, headers=headers, timeout=15)
    resp.raise_for_status()


def _auth_headers(access_token: str) -> Dict[str, str]:
    return {**_HEADERS_BASE, "Authorization": f"Bearer {access_token}"}


def rest_insert(table: str, rows: List[Dict[str, Any]], access_token: str) -> Dict[str, Any]:
    url = f"{_BASE}/rest/v1/{table}"
    resp = requests.post(url, headers=_auth_headers(access_token), json=rows, timeout=15)
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def rest_select(table: str, query: str, access_token: str) -> List[Dict[str, Any]]:
    url = f"{_BASE}/rest/v1/{table}?{query}"
    resp = requests.get(url, headers=_auth_headers(access_token), timeout=15)
    resp.raise_for_status()
    return resp.json()


def rest_delete(table: str, query: str, access_token: str) -> int:
    url = f"{_BASE}/rest/v1/{table}?{query}"
    headers = {**_auth_headers(access_token), "Prefer": "return=representation"}
    resp = requests.delete(url, headers=headers, timeout=15)
    resp.raise_for_status()
    if not resp.text:
        return 0
    try:
        data = resp.json()
        if isinstance(data, list):
            return len(data)
    except Exception:
        pass
    return 0


# --- Auth helpers -----------------------------------------------------------
async def get_user_from_access_token(access_token: str) -> Dict[str, Any]:
    """
    Validate a Supabase access_token and return the user payload.
    Raises SupabaseAuthError on failure.
    """
    supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
    if not supabase_url:
        raise SupabaseAuthError("SUPABASE_URL is not configured.")

    api_key: Optional[str] = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None) or settings.SUPABASE_ANON_KEY
    if not api_key:
        raise SupabaseAuthError("Supabase API key is missing.")

    url = f"{supabase_url}/auth/v1/user"
    headers = {"apikey": api_key, "Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise SupabaseAuthError(f"Supabase /auth/v1/user call failed: {resp.status_code} {resp.text}")

    return resp.json()
