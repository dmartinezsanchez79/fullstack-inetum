from datetime import datetime

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str


class CommentRead(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    author_email: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

