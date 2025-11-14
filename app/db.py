# app/db.py
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH, override=False)


class ConfigError(RuntimeError):
    pass


def _get_env(name: str) -> str | None:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) else v


# ✅ 1) anon 클라이언트 (기본)
@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_ANON_KEY")
    print(f"[supabase anon] URL? {bool(url)}  ANON_LEN: {len(key) if key else 0}")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / SUPABASE_ANON_KEY 누락")
    return create_client(url, key)


# ✅ 2) service_role 클라이언트 (필요한 경우에만 명시적으로)
@lru_cache(maxsize=1)
def get_supabase_service() -> Client:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    print(f"[supabase service] URL? {bool(url)}  SR_LEN: {len(key) if key else 0}")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 누락")
    return create_client(url, key)


# ✅ 3) 기존 코드 안 깨지게: get_supabase()는 anon 반환
def get_supabase() -> Client:
    """
    기존 코드 호환용. 기본 anon 클라이언트 사용.
    """
    return get_supabase_anon()
