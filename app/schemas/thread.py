# app/schemas/thread.py
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Pydantic v1/v2 차이 호환 ---
try:
    # pydantic v2
    from pydantic import field_validator
    V2 = True
except Exception:  # pragma: no cover
    # pydantic v1
    from pydantic import validator as field_validator  # type: ignore
    V2 = False


# 공통 베이스: alias 허용, 알 수 없는 필드 무시
class _Base(BaseModel):
    if V2:
        model_config = {
            "populate_by_name": True,  # alias(ownerId)로도, 필드명(owner_id)로도 받기
            "extra": "ignore",         # 모르는 필드는 무시
        }
    else:
        class Config:
            allow_population_by_field_name = True
            extra = "ignore"


# role은 넓게 받아서 나중에 정규화
AllowedRole = Literal["user", "assistant", "system", "tool"]


class MessageIn(_Base):
    role: AllowedRole
    content: str = Field(..., min_length=1)

    # role 정규화: 대소문자 허용 → 소문자화
    if V2:
        @field_validator("role")
        @classmethod
        def _role_lower_v2(cls, v: str) -> str:
            return v.lower()
    else:
        @field_validator("role", pre=True, always=True)  # type: ignore
        def _role_lower_v1(cls, v):
            return str(v).lower()

    # content 트림
    if V2:
        @field_validator("content")
        @classmethod
        def _content_strip_v2(cls, v: str) -> str:
            s = v.strip()
            if not s:
                raise ValueError("content cannot be empty")
            return s
    else:
        @field_validator("content", pre=True, always=True)  # type: ignore
        def _content_strip_v1(cls, v):
            s = str(v).strip()
            if not s:
                raise ValueError("content cannot be empty")
            return s


class IngestRequest(_Base):
    title: str = Field(..., min_length=1)
    # FE가 ownerId로 보내도 받고, 내부에선 owner_id로 사용
    owner_id: str = Field(..., alias="ownerId", min_length=1)
    messages: List[MessageIn] = Field(default_factory=list)

    # title/owner_id 공백 방지
    if V2:
        @field_validator("title", "owner_id")
        @classmethod
        def _strip_nonempty_v2(cls, v: str) -> str:
            s = v.strip()
            if not s:
                raise ValueError("must not be empty")
            return s
    else:
        @field_validator("title", "owner_id", pre=True, always=True)  # type: ignore
        def _strip_nonempty_v1(cls, v):
            s = str(v).strip()
            if not s:
                raise ValueError("must not be empty")
            return s


class IngestResponse(BaseModel):
    thread_id: str
    status: Literal["saved"]  # type: ignore[name-defined]


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str

class ThreadOut(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)  
    source_url: Optional[str] = None
    model: Optional[str] = None
    created_at: str
    messages: List["MessageOut"]