from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote

import requests

from app.db import supabase as sb


def list_extension_files_for_user(user_id: str, access_token: str) -> List[Dict[str, Any]]:
    """
    Fetch all extension file records for the given user_id from Supabase.
    """
    if not user_id:
        return []

    query = "&".join(
        [
            f"user_id=eq.{quote(user_id)}",
            "select=" + ",".join(["id", "name", "description", "created_at"]),
            "order=created_at.desc",
        ]
    )

    try:
        rows = sb.rest_select("extension_files", query, access_token)
    except requests.HTTPError as exc:
        # If the table does not exist or is not exposed, Supabase returns 404.
        if exc.response is not None and exc.response.status_code == 404:
            return []
        raise

    return [
        {
            "id": r.get("id"),
            "name": r.get("name") or "",
            "description": r.get("description"),
            "created_at": r.get("created_at"),
        }
        for r in rows
    ]
