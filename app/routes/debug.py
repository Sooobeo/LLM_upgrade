from fastapi import APIRouter, Depends, Path
from urllib.parse import quote

from app.db import supabase as sb
from app.db.deps import get_access_token, get_current_user

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/threads/{thread_id}/assistant-headtail")
def assistant_headtail(
    thread_id: str = Path(..., min_length=10),
    user=Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    owner_id = user.get("id")
    if not owner_id:
        return {"error": "unauthenticated"}

    q_check = "&".join([f"id=eq.{quote(thread_id)}", f"owner_id=eq.{quote(owner_id)}", "select=id", "limit=1"])
    if not sb.rest_select("threads", q_check, access_token):
        return {"error": "thread not found or no access"}

    msgs = sb.rest_select(
        "messages",
        "&".join(
            [
                f"thread_id=eq.{quote(thread_id)}",
                "role=eq.assistant",
                "select=index,content",
                "order=index.asc",
            ]
        ),
        access_token,
    )
    if not msgs:
        return {"count": 0}
    return {
        "count": len(msgs),
        "first": {"index": msgs[0].get("index"), "preview": (msgs[0].get("content") or "")[:50]},
        "last": {"index": msgs[-1].get("index"), "preview": (msgs[-1].get("content") or "")[:50]},
    }
