from pydantic import BaseModel

class CommentCreate(BaseModel):
    message_index: int
    content: str

class CommentResponse(BaseModel):
    id: str
    thread_id: str
    message_index: int
    user_id: str
    content: str
    created_at: str