from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_to_id: int | None = None


class TicketRead(BaseModel):
    id: int
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_by_id: int
    assigned_to_id: int | None
    created_at: datetime
    updated_at: datetime
    created_by_email: str | None = None
    assigned_to_email: str | None = None

    class Config:
        from_attributes = True


class PaginatedTickets(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int
    filters: dict[str, Any]

