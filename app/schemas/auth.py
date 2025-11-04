from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class GoogleExchangeBody(BaseModel):
    id_token: str = Field(..., min_length=10)

class AccessPayload(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserLite(BaseModel):
    id: str
    email: Optional[str] = None
    provider: Optional[str] = None
    created_at: Optional[str] = None

class GoogleExchangeResp(AccessPayload):
    user: UserLite
    issued_at: str

class AccessOnlyResp(AccessPayload):
    pass

class MeResp(BaseModel):
    id: str
    email: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
