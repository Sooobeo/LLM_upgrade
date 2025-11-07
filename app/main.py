# app/main.py
<<<<<<< HEAD
from fastapi import FastAPI, Body, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime, timezone
import os, time, traceback

# 내부 모듈
from app.db import get_supabase  # .env 로딩/클라이언트 생성 포함(우회 로더 지원)
from app.repository import (
    insert_thread_and_messages,
    fetch_thread,
    list_threads,
)

# -----------------------------------------------------------------------------
# FastAPI 앱 & 미들웨어
# -----------------------------------------------------------------------------
app = FastAPI(
    title="GPT Log Server",
    version="0.1.0",
    description="Conversation logging backend (FastAPI + Supabase)",
)

# 개발 편의를 위한 CORS (배포 전 tighten 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # TODO: 배포 시 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 로그 (검증 전에도 찍힘)
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

# Swagger 서버 URL 고정(캐시/혼동 방지)
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

# -----------------------------------------------------------------------------
# 헬스/진단 라우트
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/_env")
def env_check():
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return {
        "ok": bool(url and key),
        "SUPABASE_URL": bool(url),
        "SUPABASE_KEY_len": len(key) if key else 0,
    }

@app.get("/_env_dump")
def env_dump():
    # 민감값은 길이만 확인할 수 있게 마스킹
    out = {}
    for k, v in os.environ.items():
        if k.startswith("SUPABASE"):
            out[k] = f"{'*' * len(v)}" if v else ""
    return out

@app.post("/_echo_raw")
async def echo_raw(req: Request):
    try:
        payload = await req.json()
    except Exception:
        payload = None
    return {"path": str(req.url.path), "payload": payload}

# 최소 DB 삽입 프로브 (키/권한/스키마 빠르게 확인)
@app.post("/ingest_min")
def ingest_min():
    try:
        sb = get_supabase()
        tid = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        t = {"id": tid, "title": "PING", "owner_id": "diag", "created_at": now}
        r = sb.table("threads").insert(t).execute()
        if getattr(r, "error", None):
            raise RuntimeError(f"threads insert error: {r.error}")
        return {"thread_id": tid, "status": "saved(min)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ingest_min failed: {e}")

# -----------------------------------------------------------------------------
# 유틸: 요청 바디 수동 정규화 (alias/Pydantic 이슈 우회)
# -----------------------------------------------------------------------------
def _normalize_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    - 최상위: ownerId/owner_id 모두 허용 → owner_id로 정규화
    - messages[*]: role/content 검증 + role은 DB에 user/assistant만 저장
    - 공백/빈문자 방지
    """
    if not isinstance(raw, dict):
        raise ValueError("JSON body must be an object")

    title = (raw.get("title") or "").strip()
    owner_id = (raw.get("owner_id") or raw.get("ownerId") or "").strip()
    messages = raw.get("messages") or []

    if not title:
        raise ValueError("title must not be empty")
    if not owner_id:
        raise ValueError("owner_id must not be empty (ownerId/owner_id allowed)")

    norm_msgs: List[Dict[str, Any]] = []
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            raise ValueError(f"messages[{i}] must be an object")
        role = str(m.get("role", "")).strip().lower()
        content = str(m.get("content", "")).strip()
        if role not in ("user", "assistant", "system", "tool"):
            raise ValueError(f"messages[{i}].role invalid")
        if not content:
            raise ValueError(f"messages[{i}].content must not be empty")
        # DB에는 user/assistant만 저장
        role = "user" if role == "user" else "assistant"
        norm_msgs.append({"role": role, "content": content})

    return {"title": title, "owner_id": owner_id, "messages": norm_msgs}

# -----------------------------------------------------------------------------
# 핵심 API
# -----------------------------------------------------------------------------
@app.post("/ingest")
def ingest(raw: Dict[str, Any] = Body(...)):
    """
    NOTE: Pydantic alias 이슈를 우회하기 위해 raw dict로 받고 직접 정규화한다.
    Swagger/확장 모두 ownerId/owner_id 어느 쪽이든 허용.
    """
    try:
        payload = _normalize_payload(raw)  # ← 여기서 owner_id 보장
        thread_id = insert_thread_and_messages(get_supabase(), payload)
        return {"thread_id": thread_id, "status": "saved"}
    except Exception as e:
        print("[/ingest] ERROR:", repr(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threads/{thread_id}")
def get_thread(thread_id: str):
    try:
        data = fetch_thread(get_supabase(), thread_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch_thread failed: {e}")

@app.get("/threads")
def get_threads(owner_id: str, limit: int = 10, offset: int = 0):
    try:
        data = list_threads(get_supabase(), owner_id=owner_id, limit=limit, offset=offset)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"list_threads failed: {e}")




# --- DEBUG: service_role/anon 키의 JWT payload를 디코드해서 URL과 매칭 확인 ---
import os, json, base64, re
from urllib.parse import urlparse

def _b64url_decode(s: str) -> bytes:
    s = s.replace('-', '+').replace('_', '/')
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s + pad)

@app.get("/_sb_jwt")
def sb_jwt():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (
        (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        or (os.getenv("SUPABASE_KEY") or "").strip()
        or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    )
    if not url or not key:
        return {"ok": False, "why": "missing url or key"}

    # URL에서 ref 추출: https://<ref>.supabase.co
    parsed = urlparse(url)
    host = parsed.netloc
    m = re.match(r"^([^.]+)\.supabase\.co$", host)
    url_ref = m.group(1) if m else None

    # 키가 JWT면 payload(두번째 조각)를 파싱
    parts = key.split(".")
    jwt_info = {}
    if len(parts) >= 2:
        try:
            payload = json.loads(_b64url_decode(parts[1]).decode("utf-8", "ignore"))
            iss = payload.get("iss", "")
            # iss 예: "https://<ref>.supabase.co/"
            iss_ref = None
            mm = re.match(r"^https?://([^.]+)\.supabase\.co", iss)
            if mm:
                iss_ref = mm.group(1)
            jwt_info = {"iss": iss, "iss_ref": iss_ref, "aud": payload.get("aud")}
        except Exception as e:
            jwt_info = {"error": f"jwt_decode_failed: {e}"}
    else:
        jwt_info = {"error": "key_not_jwt_like"}

    return {
        "ok": bool(url_ref and jwt_info.get("iss_ref") and url_ref == jwt_info["iss_ref"]),
        "url": url,
        "url_ref": url_ref,
        "key_len": len(key),
        "jwt": jwt_info,
        "hint": "ok=True여야 URL과 키의 프로젝트가 일치합니다. False면 URL 또는 KEY를 같은 프로젝트에서 다시 복사하세요.",
    }

# --- debug routes ---
from fastapi.routing import APIRoute

@app.get("/_routes")
def routes():
    return {"paths":[r.path for r in app.routes if isinstance(r, APIRoute)]}

# --- DEBUG ROUTES (확정 진단용) ---
import os, json, base64, re, urllib.request, urllib.error
from urllib.parse import urlparse
from fastapi.routing import APIRoute

@app.get("/_routes")
def routes():
    return {"paths": [r.path for r in app.routes if isinstance(r, APIRoute)]}

@app.get("/_key_hint")
def key_hint():
    key = (
        (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        or (os.getenv("SUPABASE_KEY") or "").strip()
        or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    )
    return {"len": len(key), "starts_with_eyJ": key.startswith("eyJ"), "dot_count": key.count(".")}

def _b64url_decode(s: str) -> bytes:
    s = s.replace('-', '+').replace('_', '/')
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s + pad)

@app.get("/_sb_jwt")
def sb_jwt():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (
        (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        or (os.getenv("SUPABASE_KEY") or "").strip()
        or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    )
    parsed = urlparse(url) if url else None
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
        jwt_info = {"error": "key_not_jwt_like"}

    return {
        "ok": bool(url_ref and jwt_info.get("iss_ref") and url_ref == jwt_info["iss_ref"]),
        "url_ref": url_ref, "key_len": len(key), "jwt": jwt_info
    }

@app.get("/_sb_probe")
def sb_probe():
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (
        (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        or (os.getenv("SUPABASE_KEY") or "").strip()
        or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    )
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
=======
from fastapi import FastAPI, HTTPException
import os, httpx

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/google/exchange-id-token")
async def exchange_id_token(payload: dict):
    # 기대 바디: { provider, id_token, client_id, (nonce?) }
    required = ["provider", "id_token", "client_id"]
    if any(k not in payload for k in required):
        raise HTTPException(status_code=400, detail={"error":"missing fields","got":list(payload.keys())})

    SUPABASE_URL = os.environ.get("SUPABASE_URL")    # e.g. https://<project>.supabase.co
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="missing env SUPABASE_URL / SUPABASE_ANON_KEY")

    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=id_token"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json=payload)

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=data)

    return data
>>>>>>> 014db905644aa82de750fb26a1e5f02c9d2cde07
