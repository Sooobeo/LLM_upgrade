from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str = Field(..., example="f3c2ab18-9e4d-4e0e-9a53-4c90c2a12e0d")
    email: Optional[EmailStr] = Field(None, example="user@example.com")


class ExtensionFileOut(BaseModel):
    id: int = Field(..., example=1)
    name: str = Field(..., example="파일_이름_예시")
    description: Optional[str] = Field(None, example="설명")
    created_at: datetime = Field(..., example="2025-11-26T05:00:00Z")


class ExtensionFileListResp(BaseModel):
    items: List[ExtensionFileOut]
