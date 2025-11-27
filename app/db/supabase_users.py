from __future__ import annotations

from typing import Dict, Optional

import requests

from app.core.config import settings


def _service_headers() -> Dict[str, str]:
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required to look up users by email")
    return {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def get_user_id_by_email(email: str) -> Optional[str]:
    """
    Look up a Supabase auth user id by email using the admin endpoint.
    Returns None if not found.
    """
    if not email:
        return None
    base = settings.SUPABASE_URL.rstrip("/")
    url = f"{base}/auth/v1/admin/users"
    headers = _service_headers()
    resp = requests.get(f"{url}?email={email}", headers=headers, timeout=10)
    resp.raise_for_status()
    users = resp.json().get("users") if resp.text else []
    for user in users or []:
        if (user.get("email") or "").lower() == email.lower():
            return user.get("id")
    return None


def get_users_by_ids(user_ids: list[str]) -> Dict[str, Dict[str, str]]:
    """
    Fetch multiple Supabase auth users by ids.
    Returns mapping: {user_id: {"email": "...", "id": "..."}}
    """
    if not user_ids:
        return {}
    base = settings.SUPABASE_URL.rstrip("/")
    url = f"{base}/auth/v1/admin/users"
    headers = _service_headers()
    out: Dict[str, Dict[str, str]] = {}
    # Supabase admin users endpoint allows filtering with id.in
    query = ",".join(user_ids)
    resp = requests.get(f"{url}?id=in.({query})", headers=headers, timeout=10)
    resp.raise_for_status()
    users = resp.json().get("users") if resp.text else []
    for user in users or []:
        uid = user.get("id")
        if uid:
            out[uid] = {"id": uid, "email": user.get("email")}
    return out
