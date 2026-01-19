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

class ChatBody(BaseModel):
    """
    /threads/{thread_id}/chat 요청 바디
    - content: 유저가 새로 보내는 메시지(1건)
    - model: (선택) 기본 모델(settings.LLM_MODEL) 대신 특정 모델로 호출
    - context_limit: (선택) 최근 N개 메시지를 컨텍스트로 사용
    """
    content: str = Field(..., min_length=1)
    model: Optional[str] = None
    context_limit: int = Field(default=50, ge=1, le=200)


class ChatResp(BaseModel):
    thread_id: str
    user_content: str
    assistant_content: str
    assistant_index: Optional[int] = None
    status: Literal["saved"] = "saved"