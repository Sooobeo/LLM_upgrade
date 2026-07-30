from __future__ import annotations

from typing import List

from pydantic import BaseModel, EmailStr, Field


class WorkspaceMembersIn(BaseModel):
    emails: List[EmailStr] = Field(
        default_factory=list,
        max_length=50,
        json_schema_extra={"example": ["user1@example.com", "user2@example.com"]},
    )


class WorkspaceCreatedOut(BaseModel):
    thread_id: str
    is_workspace: bool = True
    added_members: List[str]
    not_found: List[str] = Field(default_factory=list)
