import os
from functools import lru_cache
from pathlib import Path


# 1) .env 로드 (python-dotenv 있으면 사용, 없으면 수동)
def _load_env():
    root = Path(__file__).resolve().parents[1]  # backend_moon
    env_path = root / ".env"
    loaded = False
    try:
        from dotenv import load_dotenv  # python-dotenv
        loaded = load_dotenv(dotenv_path=env_path)
        print(f"[dotenv] load_dotenv('{env_path}') -> {loaded}")
    except Exception as e:
        print(f"[dotenv] python-dotenv not available ({e}), fallback manual loader")
        # 수동 로더
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and os.getenv(k) is None:
                    os.environ[k] = v
            loaded = True
            print(f"[dotenv] manually loaded from {env_path}")
        else:
            print(f"[dotenv] not found at {env_path}")
    # 어떤 이름들이 보이는지 즉시 로그
    print(
        "[envcheck]",
        "URL:", bool(os.getenv("SUPABASE_URL")),
        "SERVICE_ROLE_LEN:", len(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""),
        "KEY_LEN:", len(os.getenv("SUPABASE_KEY") or ""),
        "ANON_LEN:", len(os.getenv("SUPABASE_ANON_KEY") or ""),
    )
    return loaded

_load_env()

@lru_cache(maxsize=1)
def get_supabase():
    from supabase import create_client, Client
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # 표준명
        or os.getenv("SUPABASE_KEY")            # 네가 쓰던 이름
        or os.getenv("SUPABASE_ANON_KEY")       # 개발용
    )
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / (SERVICE_ROLE_KEY|SUPABASE_KEY|ANON_KEY) 누락")
    return create_client(url, key)


# ✅ .env 강제 로드: backend/.env, 루트/.env 둘 다 탐색
try:
    from dotenv import load_dotenv, find_dotenv
    # 1) 현재 파일 기준으로 backend/.env 시도
    BACKEND_DIR = Path(__file__).resolve().parents[1]
    ENV_CANDIDATES = [
        BACKEND_DIR / ".env",             # backend/.env
        BACKEND_DIR / ".env.local",       # 선택
        Path(find_dotenv(".env")) if find_dotenv(".env") else None,  # 상위 탐색
    ]
    loaded_any = False
    for p in ENV_CANDIDATES:
        if p and p.exists():
            load_dotenv(dotenv_path=p, override=False)
            print(f"[dotenv] loaded: {p}")
            loaded_any = True
    if not loaded_any:
        # 마지막으로 현재 작업 디렉토리에서라도 찾아보기
        alt = Path.cwd() / ".env"
        if alt.exists():
            load_dotenv(dotenv_path=alt, override=False)
            print(f"[dotenv] loaded from CWD: {alt}")
        else:
            print("[dotenv] no .env found (checked:", ", ".join([str(x) for x in ENV_CANDIDATES if x]), ")")
except Exception as e:
    print("[dotenv] load failed:", repr(e))

from supabase import create_client, Client

class ConfigError(RuntimeError):
    pass

def _get_url_and_key():
    url = os.getenv("SUPABASE_URL")
    # ✅ 여러 이름 허용: SERVICE_ROLE_KEY → SUPABASE_KEY → ANON_KEY(개발용)
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return url, key

@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url, key = _get_url_and_key()
    print(f"[envcheck] URL set? {bool(url)}  KEY len: {len(key) if key else 0}")
    if not url or not key:
        raise ConfigError("SUPABASE_URL / (SERVICE_ROLE_KEY|SUPABASE_KEY|ANON_KEY) 누락")
    return create_client(url, key)
