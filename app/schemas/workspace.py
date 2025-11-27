from __future__ import annotations

from typing import List

from pydantic import BaseModel, EmailStr, Field


class WorkspaceMembersIn(BaseModel):
    emails: List[EmailStr] = Field(default_factory=list, example=["user1@example.com", "user2@example.com"])


class WorkspaceCreatedOut(BaseModel):
    thread_id: str
    is_workspace: bool = True
    added_members: List[str]
    not_found: List[str] = Field(default_factory=list)
