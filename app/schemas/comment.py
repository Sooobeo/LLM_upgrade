from typing import Optional

from pydantic import BaseModel, Field, model_validator

class CommentCreate(BaseModel):
    message_index: int = Field(..., ge=0, lt=2_147_483_647)
    content: str = Field(..., min_length=1, max_length=4000)

class CommentResponse(BaseModel):
    id: str
    thread_id: str
    message_index: int
    user_id: str
    content: str
    created_at: str


class BranchCommentCreate(BaseModel):
    thread_id: str
    content: str = Field(..., min_length=1, max_length=4000)
    position_x: float = Field(..., ge=-10000, le=10000)
    position_y: float = Field(..., ge=-10000, le=10000)


class BranchCommentUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    position_x: Optional[float] = Field(default=None, ge=-10000, le=10000)
    position_y: Optional[float] = Field(default=None, ge=-10000, le=10000)

    @model_validator(mode="after")
    def require_change(self):
        if (
            self.content is None
            and self.position_x is None
            and self.position_y is None
        ):
            raise ValueError("At least one field must be provided")
        if (self.position_x is None) != (self.position_y is None):
            raise ValueError("position_x and position_y must be provided together")
        return self


class BranchCommentResponse(BaseModel):
    id: str
    thread_id: str
    user_id: str
    author_id: str
    can_edit: bool = False
    content: str
    position_x: float
    position_y: float
    created_at: Optional[str] = None
