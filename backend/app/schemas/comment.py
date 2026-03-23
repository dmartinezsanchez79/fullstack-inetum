from datetime import datetime

from pydantic import BaseModel

"""
Schemas Pydantic para comentarios.

`CommentCreate` define el contenido que el cliente envía.
`CommentRead` define el formato que el API devuelve (incluye author_email para el mini chat).
"""


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

