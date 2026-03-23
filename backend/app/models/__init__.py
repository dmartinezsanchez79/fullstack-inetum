"""
Barrel file para los modelos de dominio.

Reexporta clases desde `user.py`, `ticket.py` y `comment.py` para que el resto del
proyecto pueda importar con rutas más cortas:

    from ..models import User, Ticket
"""

from .user import User, UserRole
from .ticket import Ticket, TicketPriority, TicketStatus
from .comment import Comment

__all__ = [
    "User",
    "UserRole",
    "Ticket",
    "TicketPriority",
    "TicketStatus",
    "Comment",
]

