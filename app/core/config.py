from __future__ import annotations
import os
from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class AppEnv(str, Enum):
    local = "local"
    dev   = "dev"
    prod  = "prod"

class Settings(BaseSettings):
    # --- 프로젝트 메타 ---
    PROJECT_NAME: str = "GPT Conversation History Log Server"
    PROJECT_VERSION: str = "0.1.0"
    DESCRIPTION: str = "Conversation history logging backend (FastAPI + Supabase)"
    OPENAPI_SERVER_URL: str = "http://127.0.0.1:8000"

    # --- 환경 구분 ---
    APP_ENV: AppEnv = Field(default=AppEnv.local)

    # --- Supabase ---
    SUPABASE_URL: str
    # A 모드에서 필수 (클라이언트 토큰 전달 + anon 키)
    SUPABASE_ANON_KEY: str

    # (선택) 서버에서 service_role도 쓸 일이 있을 때만 세팅
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # (선택) iss/aud 검증 커스터마이즈 시
    SUPABASE_JWT_AUD: str = "authenticated"

    # --- 쿠키/도메인 (프록시형 API 만들 때 사용) ---
    COOKIE_DOMAIN: str = "localhost"     # 예: "careon.io.kr"
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

    @field_validator("SUPABASE_URL")
    @classmethod
    def _strip_url(cls, v: str) -> str:
        return v.rstrip("/")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
