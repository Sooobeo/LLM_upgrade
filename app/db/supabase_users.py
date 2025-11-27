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
