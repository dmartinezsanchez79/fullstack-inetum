from __future__ import annotations

"""
Modelos de base de datos para comentarios.

Un `Comment`:
- pertenece a un `ticket` (ticket_id)
- tiene autor (author_id -> user.id)
- guarda contenido y fecha de creación.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class CommentBase(SQLModel):
    content: str


class Comment(CommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id")
    author_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

