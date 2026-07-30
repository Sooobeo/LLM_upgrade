from __future__ import annotations

from enum import Enum

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    local = "local"
    dev = "dev"
    prod = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 로컬 개발에서는 프론트와 동일한 Supabase 공개 설정을 재사용합니다.
        # 실제 환경변수는 두 파일보다 항상 우선합니다.
        env_file=(".env", "frontend/.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 프로젝트 메타 ---
    PROJECT_NAME: str = "GPT Conversation History Log Server"
    PROJECT_VERSION: str = "0.1.0"
    DESCRIPTION: str = "Conversation history logging backend (FastAPI + Supabase)"
    OPENAPI_SERVER_URL: str = "http://127.0.0.1:8000"

    # --- 환경 구분 ---
    APP_ENV: AppEnv = Field(default=AppEnv.local)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver"
    MAX_REQUEST_BODY_BYTES: int = 1_048_576
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20
    LLM_RATE_LIMIT_PER_MINUTE: int = 30
    ENABLE_PRODUCTION_API_DOCS: bool = False

    # --- LLM Upstream ---
    LLM_PRIMARY_BASE_URL: str = "https://llm.ycc.club"
    LLM_PRIMARY_PATH: str = "/api/generate"
    LLM_FALLBACK_BASE_URL: str | None = None
    LLM_FALLBACK_PATH: str = "/api/generate"
    LLM_FALLBACK_KIND: str = "same_as_primary"  # same_as_primary | ollama | openai_compatible
    LLM_FALLBACK_MODEL: str | None = None
    LLM_REQUEST_TIMEOUT_SECS: int = 60
    LLM_TLS_VERIFY: bool = True
    LLM_CONNECT_TIMEOUT: float = 5.0
    LLM_READ_TIMEOUT: float = 120.0
    LLM_MAX_RETRIES: int = 2
    CHAT_DEBUG_ASSERTS: bool = False
    LLM_MODE: str = "chat"  # "chat" | "generate"

    # --- Supabase ---
    SUPABASE_URL: str = Field(
        validation_alias=AliasChoices("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"),
    )
    # A 모드에서 필수 (클라이언트 토큰 전달 + anon 키)
    SUPABASE_ANON_KEY: str = Field(
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"),
    )

    # (선택) 서버에서 service_role도 쓸 일이 있을 때만 세팅
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # (선택) iss/aud 검증 커스터마이즈 시
    SUPABASE_JWT_AUD: str = "authenticated"


    # --- LLM ---
    LLM_BASE_URL: str = "https://llm.ycc.club:443"
    LLM_MODEL: str = "gemma3:270m"
    LLM_TIMEOUT_SEC: int = 30
    LLM_SYSTEM_PROMPT: str = "You are a helpful assistant. Answer the user directly without repeating their question."

    # --- Google Gemini ---
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Google이 신규 키에 2.5 Flash 제공을 종료하여 호환 실행에 사용합니다.
    GEMINI_2_5_COMPAT_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECS: float = 120.0

    # --- 쿠키/도메인 (프록시형 API 만들 때 사용) ---
    # 비워 두면 host-only 쿠키가 되어 localhost에서도 정상 동작합니다.
    COOKIE_DOMAIN: str | None = None     # 배포 시 예: ".careon.io.kr"
    COOKIE_NAME: str = "sb-access"       # 프록시에서 access_token을 쿠키로 줄 때(선택)
    REFRESH_COOKIE_NAME: str = "sb-refresh"

    # === 파생 속성들 ===
    @property
    def cookie_secure(self) -> bool:
        # 배포(https)에서만 True
        return self.APP_ENV == AppEnv.prod

    @property
    def cookie_samesite(self) -> str:
        # 로컬 포트 다른 정도면 Lax로 충분, 서브도메인/크로스 도메인이면 "none"(https 필수)
        return "lax" if self.APP_ENV in (AppEnv.local, AppEnv.dev) else "none"

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip().rstrip("/") for value in self.CORS_ORIGINS.split(",") if value.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [value.strip() for value in self.TRUSTED_HOSTS.split(",") if value.strip()]

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def _normalize_app_env(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        aliases = {
            "development": AppEnv.dev.value,
            "production": AppEnv.prod.value,
        }
        return aliases.get(normalized, normalized)

    @field_validator("SUPABASE_URL")
    @classmethod
    def _strip_url(cls, v: str) -> str:
        return v.strip().rstrip("/")

settings = Settings()
