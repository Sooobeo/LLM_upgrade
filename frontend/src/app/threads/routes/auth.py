# app/routes/auth.py

from pydantic import BaseModel
import httpx
from fastapi import APIRouter, HTTPException
from app.core.config import settings

from app.db.supabase import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])

class PasswordSignupRequest(BaseModel):
    nickname: str
    email: str
    password: str


@router.post("/signup/password")
async def signup_with_password(payload: PasswordSignupRequest):
    """
    1) Supabase Auth signUp
    2) nickname은 profiles 테이블에 저장(있을 때)
    """

    SUPABASE_URL = (settings.SUPABASE_URL or "").rstrip("/")
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(500, "Missing SUPABASE_URL / SUPABASE_ANON_KEY")

    signup_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }

    body = {
        "email": payload.email,
        "password": payload.password,
        # ✅ Supabase user_metadata에 nickname 저장
        "data": { "nickname": payload.nickname },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(signup_url, headers=headers, json=body)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, detail=data)

    return data

class SignupRequest(BaseModel):
    nickname: str
    email: str
    password: str

@router.post("/signup/password")
async def signup_with_password(payload: SignupRequest):
    """
    1) Supabase Auth에 회원가입(signUp)
    2) raw_user_meta_data에 nickname 저장
    3) trigger가 profiles를 자동 생성/저장
    """
    SUPABASE_URL = (settings.SUPABASE_URL or "").rstrip("/")
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="Missing Supabase settings")

    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }

    json_body = {
        "email": payload.email,
        "password": payload.password,
        "data": {               # ✅ user_metadata로 들어감
            "nickname": payload.nickname
        }
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=json_body)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=data)

    return data

# 회원가입 요청 스키마
class SignUpRequest(BaseModel):
    email: str
    password: str
    nickname: str


@router.post("/signup", summary="회원가입 (email/password + nickname)")
async def signup(payload: SignUpRequest):
    """
    1) Supabase Auth에 email/password로 sign-up
    2) 반환된 user.id로 user_profiles에 nickname insert
    """

    SUPABASE_URL = settings.SUPABASE_URL.rstrip("/")
    ANON = settings.SUPABASE_ANON_KEY

    # 1) Auth sign-up
    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {
        "apikey": ANON,
        "Authorization": f"Bearer {ANON}",
        "Content-Type": "application/json"
    }

    body = {
        "email": payload.email,
        "password": payload.password
    }

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(url, headers=headers, json=body)

    data = res.json()

    if res.status_code >= 400:
        raise HTTPException(res.status_code, detail=data)

    user = data.get("user")
    if not user:
        raise HTTPException(500, "Supabase sign-up returned no user")

    user_id = user["id"]

    # 2) profile insert
    sb = get_supabase()
    prof = (
        sb.table("user_profiles")
        .insert({"id": user_id, "nickname": payload.nickname})
        .execute()
    )

    return {
        "user_id": user_id,
        "email": payload.email,
        "nickname": payload.nickname
    }

