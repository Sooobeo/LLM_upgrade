# main.py
from fastapi import FastAPI, Body, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime, timezone
import os, time, traceback, json, base64, re, urllib.request, urllib.error
from urllib.parse import urlparse
from fastapi.routing import APIRoute
import connection
import query

app = FastAPI(
    title="GPT conversation history Log Server",
    version="0.1.0",
    description="Conversation history logging backend (FastAPI + Supabase)",
)

#Access control
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#request logger for debuging and llgging,
class _ReqLogger(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.time()
        try:
            body_bytes = await request.body()
            preview = body_bytes[:300]
            print(f"[REQ] {request.method} {request.url.path} body={preview!r}")
        except Exception as e:
            print(f"[REQ] {request.method} {request.url.path} (read body failed: {e})")
        
        resp = await call_next(request)
        dt = (time.time() - t0) * 1000
        print(f"[RESP] {request.method} {request.url.path} -> {resp.status_code} ({dt:.1f}ms)")
        return resp

app.add_middleware(_ReqLogger)

#api for UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes
    )
    schema["servers"] = [{"url": "http://127.0.0.1:8000"}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi


#message classification by speaker and contents
def normalize_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    #parse wanted data from json responce
    title = raw.get("title").strip()
    if not title:
        raise ValueError("title must not be empty")
    
    owner_id = raw.get("owner_id").strip()
    if not owner_id:
        raise ValueError("owner_id must not be empty")
    
    messages = raw.get("messages")
    if not messages:
        raise ValueError("messages must not be empty")


    norm_msgs: List[Dict[str, Any]] = []
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            raise ValueError(f"messages[{i}] must be an object")
        role = str(m.get("role", "")).strip().lower()
        content = str(m.get("content", "")).strip()
        if role not in ("user", "assistant", "system"):
            raise ValueError(f"messages[{i}].role invalid")
        if not content:
            raise ValueError(f"messages[{i}].content must not be empty")

        norm_msgs.append({"role": role, "content": content})

    return {"title": title, "owner_id": owner_id, "messages": norm_msgs}


@app.post("/ingest")
def ingest(raw: Dict[str, Any] = Body(...)):
    try:
        payload = normalize_payload(raw)
        sb = connection.get_supabase()
        thread_id = query.insert_thread(sb, payload)
        messages_data = query.insert_messages(sb, thread_id, payload["messages"])
        return {"thread_id": thread_id, "messages_data": messages_data}
    except (ValueError, connection.ConfigError) as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Value/Config Error: {e}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.get("/threads/{thread_id}")
def get_thread(thread_id: str):
    try:
        sb = connection.get_supabase()
        data = query.fetch_thread(sb, thread_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch_thread failed: {e}")

@app.get("/threads")
def get_threads(owner_id: str, limit: int, offset: int):
    try:
        sb = connection.get_supabase()
        data = query.list_threads(sb, owner_id=owner_id, limit=limit, offset=offset)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"list_threads failed: {e}")

#to only check this server is alive or not
@app.get("/health")
def health():
    return {"status": "ok"}

#load env. value
@app.get("/_env")
def env_check():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") #for dev, use SUPABASE_ANON_KEY for publishing

    return {
        "SUPABASE_URL_set": bool(url),
        "SUPABASE_KEY": len(key)*"*",
    }


#db testing with minimal information
@app.post("/ingest_min")
def ingest_min():
    try:
        sb = connection.get_supabase()
        tid = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        t = {"id": tid, "title": "PING", "owner_id": "test", "created_at": now}
        r = sb.table("threads").insert(t).execute()
        if getattr(r, "error", None):
            raise RuntimeError(f"threads insert error: {r.error}")
        return {"thread_id": tid, "status": "saved(min)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ingest_min failed: {e}")

#---------------------------
#for dev

#to check env. value is valid
@app.get("/_env_dump")
def env_dump():
    out = {}
    for k, v in os.environ.items():
        if k.startswith("SUPABASE"):
            out[k] = len(v) if v else "Null"
    return out

#to check if request to server was correct as desired
@app.post("/_echo_raw")
async def echo_raw(req: Request):
    try:
        payload = await req.json()
    except Exception:
        payload = None
    return {"path": str(req.url.path), "payload": payload}

#sitemap
@app.get("/_routes")
def routes():
    return {"paths": [r.path for r in app.routes if isinstance(r, APIRoute)]}

#return api's value
@app.get("/_key_hint")
def key_hint():
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip() #for dev, use SUPABASE_ANON_KEY for publishing

    return {"len": len(key)}

#supabase's URL-safe Base64 to standard base64 converter
def _b64url_decode(s: str) -> bytes:
    s = s.replace('-', '+').replace('_', '/')
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s + pad)

#offline check if JWT key matches with URL
@app.get("/_sb_jwt")
def sb_jwt():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip() #for dev, use SUPABASE_ANON_KEY for publishing

    parsed = urlparse(url) if url else None
    # ParseResult(scheme='https', netloc='[key].supabase.co', path='', params='', query='', fragment='')
    host = parsed.netloc if parsed else ""
    m = re.match(r"^([^.]+)\.supabase\.co$", host)
    url_ref = m.group(1) if m else None

    parts = key.split(".")
    jwt_info = {}
    if len(parts) >= 2:
        try:
            payload = json.loads(_b64url_decode(parts[1]).decode("utf-8", "ignore"))
            iss = payload.get("iss", "")
            mm = re.match(r"^https?://([^.]+)\.supabase\.co", iss)
            iss_ref = mm.group(1) if mm else None
            jwt_info = {"iss": iss, "iss_ref": iss_ref, "aud": payload.get("aud")}
        except Exception as e:
            jwt_info = {"error": f"jwt_decode_failed: {e}"}
    else:
        jwt_info = {"error": "key doesn't match with JWT format"}

    ok = bool(url_ref and jwt_info.get("iss_ref") and url_ref == jwt_info["iss_ref"])
    return {
        "match": ok,
        "url_ref": url_ref, 
        "key_len": len(key), 
        "jwt": jwt_info
    }

#online testing
@app.get("/_sb_probe")
def sb_probe():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip() #for dev, use SUPABASE_ANON_KEY for publishing

    if not url or not key:
        return {"ok": False, "why": "missing url or key", "url_set": bool(url), "key_len": len(key)}
    
    rest_url = f"{url}/rest/v1/threads?select=id&limit=1"
    req = urllib.request.Request(
        rest_url, 
        headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return {"ok": True, "rest_status": r.getcode(), "hint": "Successfully connected and authenticated."}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        hint = "Authentication failed (401/403) or Table not found (404)."
        if e.code == 401:
            hint = "Authentication failed. Check SERVICE_ROLE_KEY or ANON_KEY."
        elif e.code == 404:
            hint = "URL/Endpoint is wrong, or 'threads' table does not exist."
        elif e.code == 403:
             hint = "Forbidden. RLS (Row Level Security) might be blocking access."
        return {"ok": False, "rest_status": e.code, "body_preview": body[:300], "hint": hint}
    except Exception as e:
         return {"ok": False, "error_type": type(e).__name__, "detail": str(e), "hint": "Network error or invalid SUPABASE_URL."}