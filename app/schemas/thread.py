from typing import List, Optional, Literal
from pydantic import BaseModel, Field

AllowedRole = Literal["user", "assistant", "system", "tool"]

class MessageIn(BaseModel):
    role: AllowedRole
    content: str = Field(..., min_length=1, max_length=32_000)

class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    messages: List[MessageIn] = Field(default_factory=list, max_length=100)

class ThreadCreateResp(BaseModel):
    thread_id: str
    status: Literal["saved"]

class ThreadTitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

class ThreadTitleUpdateResp(BaseModel):
    thread_id: str
    title: str
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
    index: Optional[int] = None
    role: Literal["user", "assistant"]
    content: str
    created_at: str

class ThreadDetailResp(BaseModel):
    id: str
    title: str
    created_at: str
    is_workspace: bool
    can_rename: bool = False
    messages: List[MessageOut]
    parent_thread_id: Optional[str] = None
    context_preview: Optional[str] = None

class MessageRow(BaseModel):
    index: int
    role: Literal["user", "assistant"]
    content: str
    created_at: str

class MessagesResp(BaseModel):
    messages: List[MessageRow]

class AddMessagesBody(BaseModel):
    messages: List[MessageIn] = Field(..., min_length=1, max_length=100)

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
    content: str = Field(..., min_length=1, max_length=32_000)
    model: Optional[str] = Field(default=None, max_length=100)
    context_limit: int = Field(default=50, ge=1, le=200)


class ChatResp(BaseModel):
    thread_id: str
    user_content: str
    assistant_content: str
    assistant_index: Optional[int] = None
    status: Literal["saved"] = "saved"

# Backward-compatible aliases
class ChatRequest(ChatBody):
    pass

class ChatResponse(ChatResp):
    pass


class BranchCreate(BaseModel):
    model: Optional[str] = Field(default=None, max_length=100)


class BranchCreateResp(BaseModel):
    thread_id: str
    title: str
    parent_thread_id: str
    context_preview: str = Field(..., max_length=20)
    status: Literal["saved"] = "saved"


class BranchNode(BaseModel):
    id: str
    thread_id: str
    title: str
    parent_thread_id: Optional[str] = None
    context_preview: Optional[str] = Field(default=None, max_length=20)
    created_at: str
    is_deleted: bool = False
    is_tutorial: bool = False
    can_manage: bool = False
    children: List["BranchNode"] = Field(default_factory=list)


class BranchesResp(BaseModel):
    roots: List[BranchNode]


class BookmarkIn(BaseModel):
    message_index: int = Field(..., ge=0)


class BookmarkOut(BaseModel):
    thread_id: str
    message_index: int
    created_at: Optional[str] = None


class BookmarksResp(BaseModel):
    bookmarks: List[BookmarkOut]


class BookmarkDeleteResp(BaseModel):
    ok: bool
    message_index: int
