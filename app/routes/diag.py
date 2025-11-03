import os, json, base64, re, urllib.request, urllib.error
from urllib.parse import urlparse
from fastapi import APIRouter
from uuid import uuid4
from datetime import datetime, timezone
from app.db.deps import get_sb

router = APIRouter(tags=["diag"])

@router.get("/_env")
def env_check():
    url = os.getenv("SUPABASE_URL")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY"))
    return {"ok": bool(url and key), "SUPABASE_URL": bool(url), "SUPABASE_KEY_len": len(key) if key else 0}

@router.get("/_env_dump")
def env_dump():
    out = {}
    for k, v in os.environ.items():
        if k.startswith("SUPABASE"):
            out[k] = f"{'*'*len(v)}" if v else ""
    return out

@router.post("/_echo_raw")
async def echo_raw(payload: dict | None = None):
    return {"payload": payload}

@router.post("/ingest_min")
def ingest_min():
    sb = get_supabase()
    tid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    t = {"id": tid, "title": "PING", "owner_id": "diag", "created_at": now}
    r = sb.table("threads").insert(t).execute()
    if getattr(r, "error", None):
        return {"ok": False, "error": str(r.error)}
    return {"thread_id": tid, "status": "saved(min)"}

def _b64url_decode(s: str) -> bytes:
    s = s.replace('-', '+').replace('_', '/')
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s + pad)

@router.get("/_key_hint")
def key_hint():
    key = ((os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
           or (os.getenv("SUPABASE_KEY") or "").strip()
           or (os.getenv("SUPABASE_ANON_KEY") or "").strip())
    return {"len": len(key), "starts_with_eyJ": key.startswith("eyJ"), "dot_count": key.count(".")}

@router.get("/_sb_jwt")
def sb_jwt():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = ((os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
           or (os.getenv("SUPABASE_KEY") or "").strip()
           or (os.getenv("SUPABASE_ANON_KEY") or "").strip())
    if not url or not key:
        return {"ok": False, "why": "missing url or key"}
    parsed = urlparse(url)
    host = parsed.netloc
    m = re.match(r"^([^.]+)\.supabase\.co$", host)
    url_ref = m.group(1) if m else None
    parts = key.split(".")
    if len(parts) < 2:
        return {"ok": False, "error": "key_not_jwt_like"}
    try:
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8", "ignore"))
        mm = re.match(r"^https?://([^.]+)\.supabase\.co", payload.get("iss", ""))
        iss_ref = mm.group(1) if mm else None
        return {"ok": bool(url_ref and iss_ref and url_ref == iss_ref), "url_ref": url_ref, "jwt": {"iss": payload.get("iss"), "aud": payload.get("aud")}}
    except Exception as e:
        return {"ok": False, "error": f"jwt_decode_failed: {e}"}

@router.get("/_sb_probe")
def sb_probe():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = ((os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
           or (os.getenv("SUPABASE_KEY") or "").strip()
           or (os.getenv("SUPABASE_ANON_KEY") or "").strip())
    if not url or not key:
        return {"ok": False, "why": "missing url or key", "url": bool(url), "key_len": len(key)}
    rest = f"{url}/rest/v1/threads?select=id&limit=1"
    req = urllib.request.Request(rest, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return {"ok": True, "rest_status": r.getcode()}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        return {"ok": False, "rest_status": e.code, "body": body[:300]}
