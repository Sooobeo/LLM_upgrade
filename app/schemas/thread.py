from typing import List, Optional, Literal
from pydantic import BaseModel, Field

AllowedRole = Literal["user", "assistant", "system", "tool"]

class MessageIn(BaseModel):
    role: AllowedRole
    content: str = Field(..., min_length=1)

class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=1)
    messages: List[MessageIn] = Field(..., min_length=1)

class ThreadCreateResp(BaseModel):
    thread_id: str
    status: Literal["saved"]

class ThreadSummary(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int
    last_message_preview: Optional[str] = None

class ThreadsListResp(BaseModel):
    threads: List[ThreadSummary]

class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str

class ThreadDetailResp(BaseModel):
    id: str
    title: str
    created_at: str
    messages: List[MessageOut]

class MessageRow(BaseModel):
    index: int
    role: Literal["user", "assistant"]
    content: str
    created_at: str

class MessagesResp(BaseModel):
    messages: List[MessageRow]

class AddMessagesBody(BaseModel):
    messages: List[MessageIn] = Field(..., min_length=1)

class AddMessagesResp(BaseModel):
    thread_id: str
    added_count: int
    status: Literal["saved"]
