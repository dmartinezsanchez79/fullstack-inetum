"""
Rutas de tickets y comentarios.

Responsabilidades:
- Controlar acceso por rol (USER/AGENT) usando dependencias.
- CRUD de tickets con reglas de negocio.
- Historial de comentarios por ticket (tipo mini chat).
- Exportación a Excel para AGENT.
"""

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from openpyxl import Workbook
from sqlalchemy import func
from sqlmodel import Session, col, select, delete

from ..deps import get_current_active_user, get_current_agent, get_db
from ..models import Comment, Ticket, TicketPriority, TicketStatus, User, UserRole
from ..schemas.comment import CommentCreate, CommentRead
from ..schemas.ticket import PaginatedTickets, TicketCreate, TicketRead, TicketUpdate

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _tickets_query(current_user: User, status_filter, priority_filter, search):
    """Query base con filtros (sin paginación ni orden)."""
    query = select(Ticket)
    if current_user.role == UserRole.USER:
        query = query.where(Ticket.created_by_id == current_user.id)
    if status_filter is not None:
        query = query.where(Ticket.status == status_filter)
    if priority_filter is not None:
        query = query.where(Ticket.priority == priority_filter)
    if search:
        like_pattern = f"%{search}%"
        query = query.where(
            col(Ticket.title).ilike(like_pattern)
            | col(Ticket.description).ilike(like_pattern)
        )
    return query


@router.post(
    "", response_model=TicketRead, status_code=status.HTTP_201_CREATED
)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TicketRead:
    """Crea un ticket. Regla: solo `USER` puede crear."""
    if current_user.role != UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios finales (USER) pueden crear tickets",
        )
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        created_by_id=current_user.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return TicketRead.from_orm(ticket)


@router.get("", response_model=PaginatedTickets)
def list_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status_filter: TicketStatus | None = Query(
        default=None, alias="status", description="Filtrar por estado"
    ),
    priority_filter: TicketPriority | None = Query(
        default=None, alias="priority", description="Filtrar por prioridad"
    ),
    search: str | None = Query(
        default=None, description="Buscar en título o descripción"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> PaginatedTickets:
    """Lista tickets con filtros (status, priority, search) y paginación.

    - USER ve solo sus tickets.
    - AGENT ve todos.
    """
    base_query = _tickets_query(
        current_user, status_filter, priority_filter, search
    )

    # Total: SQLAlchemy 2.0 no tiene .count() en Result; usamos count con los mismos filtros.
    count_stmt = select(func.count()).select_from(Ticket)
    if current_user.role == UserRole.USER:
        count_stmt = count_stmt.where(Ticket.created_by_id == current_user.id)
    if status_filter is not None:
        count_stmt = count_stmt.where(Ticket.status == status_filter)
    if priority_filter is not None:
        count_stmt = count_stmt.where(Ticket.priority == priority_filter)
    if search:
        like_pattern = f"%{search}%"
        count_stmt = count_stmt.where(
            col(Ticket.title).ilike(like_pattern)
            | col(Ticket.description).ilike(like_pattern)
        )
    total = db.exec(count_stmt).one()
    total = int(total[0]) if hasattr(total, "__getitem__") else int(total)

    query = base_query.order_by(Ticket.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    tickets = db.exec(query).all()
    items = [TicketRead.from_orm(t) for t in tickets]

    return PaginatedTickets(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        filters={
            "status": status_filter,
            "priority": priority_filter,
            "search": search,
        },
    )


@router.get("/export")
def export_tickets_excel(
    db: Session = Depends(get_db),
    current_agent: User = Depends(get_current_agent),
) -> Response:
    """
    Exporta todos los tickets a un Excel (solo AGENT).
    Ignora filtros/paginación: saca todas las incidencias.
    """
    tickets = db.exec(select(Ticket).order_by(Ticket.created_at.desc())).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Tickets"

    headers = [
        "ID",
        "Título",
        "Descripción",
        "Prioridad",
        "Estado",
        "Creado por (id)",
        "Creado por (email)",
        "Asignado a (id)",
        "Asignado a (email)",
        "Creado en",
        "Actualizado en",
    ]
    ws.append(headers)

    for t in tickets:
        created_by = db.get(User, t.created_by_id)
        assigned_to = db.get(User, t.assigned_to_id) if t.assigned_to_id else None
        ws.append(
            [
                t.id,
                t.title,
                t.description,
                t.priority.value,
                t.status.value,
                t.created_by_id,
                created_by.email if created_by else "",
                t.assigned_to_id or "",
                assigned_to.email if assigned_to else "",
                t.created_at.isoformat(sep=" ", timespec="seconds"),
                t.updated_at.isoformat(sep=" ", timespec="seconds"),
            ]
        )

    # Ajuste sencillo de ancho de columnas
    for column_cells in ws.columns:
        length = max(len(str(cell.value) if cell.value is not None else "") for cell in column_cells)
        col_letter = column_cells[0].column_letter
        ws.column_dimensions[col_letter].width = min(max(length + 2, 10), 60)

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"tickets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_ticket_or_404(db: Session, ticket_id: int) -> Ticket:
    """Obtiene un ticket o devuelve 404 si no existe."""
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def _ensure_can_access_ticket(ticket: Ticket, user: User) -> None:
    """Valida permisos de acceso al ticket.

    - AGENT: acceso completo
    - USER: solo si es el creador
    """
    if user.role == UserRole.AGENT:
        return
    if ticket.created_by_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver este ticket",
        )


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TicketRead:
    """Devuelve detalle del ticket si el usuario tiene permisos."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_can_access_ticket(ticket, current_user)
    creator = db.get(User, ticket.created_by_id)
    assignee = db.get(User, ticket.assigned_to_id) if ticket.assigned_to_id else None
    return TicketRead(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_by_id=ticket.created_by_id,
        assigned_to_id=ticket.assigned_to_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        created_by_email=creator.email if creator else None,
        assigned_to_email=assignee.email if assignee else None,
    )


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TicketRead:
    """Actualiza un ticket.

    En este proyecto: solo `AGENT` puede modificar `status`, `priority` y `assigned_to_id`.
    """
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_can_access_ticket(ticket, current_user)

    # Solo AGENT puede modificar tickets (estado, prioridad, asignación).
    if current_user.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los agentes pueden modificar tickets. Usa los comentarios para dar actualizaciones.",
        )

    if payload.status is not None:
        ticket.status = payload.status
    if payload.priority is not None:
        ticket.priority = payload.priority
    if payload.assigned_to_id is not None:
        agent = db.get(User, payload.assigned_to_id)
        if not agent or agent.role != UserRole.AGENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario asignado debe existir y ser AGENT",
            )
        ticket.assigned_to_id = payload.assigned_to_id

    from datetime import datetime

    ticket.updated_at = datetime.utcnow()
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return TicketRead.from_orm(ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_agent: User = Depends(get_current_agent),
) -> None:
    """Borra el ticket y también sus comentarios (evita huérfanos)."""
    ticket = _get_ticket_or_404(db, ticket_id)
    # Evita comentarios huérfanos: si borras un ticket, borramos sus comentarios.
    db.exec(delete(Comment).where(Comment.ticket_id == ticket.id))
    db.delete(ticket)
    db.commit()


@router.post("/{ticket_id}/comments", response_model=CommentRead, status_code=201)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CommentRead:
    """Añade un comentario a un ticket (creador del ticket o AGENT)."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_can_access_ticket(ticket, current_user)
    comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentRead(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_email=current_user.email,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/{ticket_id}/comments", response_model=list[CommentRead])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[CommentRead]:
    """Devuelve los comentarios del ticket en orden cronológico."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _ensure_can_access_ticket(ticket, current_user)
    comments = db.exec(
        select(Comment).where(Comment.ticket_id == ticket.id).order_by(Comment.created_at)
    ).all()
    result = []
    for c in comments:
        author = db.get(User, c.author_id)
        author_email = author.email if author else ""
        result.append(
            CommentRead(
                id=c.id,
                ticket_id=c.ticket_id,
                author_id=c.author_id,
                author_email=author_email,
                content=c.content,
                created_at=c.created_at,
            )
        )
    return result

