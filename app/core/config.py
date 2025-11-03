from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GPT conversation history Log Server"
    PROJECT_VERSION: str = "0.1.0"
    DESCRIPTION: str = "Conversation history logging backend (FastAPI + Supabase)"
    OPENAPI_SERVER_URL: str = "http://127.0.0.1:8000"

    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None  # 배포용은 ANON_KEY 사용 고려

    class Config:
        env_file = ".env"

settings = Settings()
