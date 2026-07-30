from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str = Field(
        ...,
        json_schema_extra={"example": "f3c2ab18-9e4d-4e0e-9a53-4c90c2a12e0d"},
    )
    email: Optional[EmailStr] = Field(
        None,
        json_schema_extra={"example": "user@example.com"},
    )


class ExtensionFileOut(BaseModel):
    id: int = Field(..., json_schema_extra={"example": 1})
    name: str = Field(..., json_schema_extra={"example": "example_file"})
    description: Optional[str] = Field(
        None,
        json_schema_extra={"example": "Description"},
    )
    created_at: datetime = Field(
        ...,
        json_schema_extra={"example": "2025-11-26T05:00:00Z"},
    )


class ExtensionFileListResp(BaseModel):
    items: List[ExtensionFileOut]
