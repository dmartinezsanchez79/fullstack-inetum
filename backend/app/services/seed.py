from sqlmodel import Session, select

from ..core.security import get_password_hash
from ..models import Comment, Ticket, TicketPriority, TicketStatus, User, UserRole


def _get_or_create_user(session: Session, email: str, full_name: str, role: UserRole) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        role=role,
        hashed_password=get_password_hash("Demo1234!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def seed_data(session: Session) -> None:
    # Usuarios demo (idempotente: solo se crean si faltan)
    user_demo = _get_or_create_user(
        session, email="user@demo.com", full_name="Usuario Demo", role=UserRole.USER
    )
    agent_demo = _get_or_create_user(
        session, email="agent@demo.com", full_name="Agente Demo", role=UserRole.AGENT
    )
    user1_demo = _get_or_create_user(
        session, email="user1@demo.com", full_name="Usuario 1 Demo", role=UserRole.USER
    )

    # Tickets de ejemplo solo si aún no hay ninguno
    existing_ticket = session.exec(select(Ticket).limit(1)).first()
    if existing_ticket:
        return

    tickets = [
        Ticket(
            title="Error al iniciar sesión",
            description="No puedo iniciar sesión en la aplicación.",
            priority=TicketPriority.HIGH,
            status=TicketStatus.OPEN,
            created_by_id=user_demo.id,
            assigned_to_id=agent_demo.id,
        ),
        Ticket(
            title="Solicitud de nueva funcionalidad",
            description="Me gustaría poder exportar los tickets a CSV.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.IN_PROGRESS,
            created_by_id=user_demo.id,
            assigned_to_id=agent_demo.id,
        ),
        Ticket(
            title="Pregunta sobre facturación",
            description="Necesito una copia de la última factura.",
            priority=TicketPriority.LOW,
            status=TicketStatus.RESOLVED,
            created_by_id=user_demo.id,
            assigned_to_id=agent_demo.id,
        ),
        Ticket(
            title="Prueba de ticket para user1",
            description="Ticket de ejemplo perteneciente a user1.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            created_by_id=user1_demo.id,
            assigned_to_id=agent_demo.id,
        ),
    ]

    session.add_all(tickets)
    session.commit()

    session.refresh(tickets[0])
    comment = Comment(
        ticket_id=tickets[0].id,
        author_id=agent_demo.id,
        content="Estamos revisando el problema de acceso.",
    )
    session.add(comment)
    session.commit()

