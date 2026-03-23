"""
Persistencia y acceso a SQLite.

Este archivo centraliza:
- La conexión a la base de datos (`engine`) apuntando al archivo `app.db`.
- La creación automática de tablas (`init_db()`).
- La provisión de sesiones (`get_session()`) para que FastAPI pueda inyectarlas con `Depends`.
- Ajustes para SQLite, como `PRAGMA foreign_keys=ON`.
"""

from pathlib import Path
from collections.abc import Generator
from datetime import datetime
from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine

BASE_DIR = Path(__file__).resolve().parents[2]  # .../inetum
DB_PATH = BASE_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    # Asegura integridad referencial en SQLite
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db() -> None:
    """Create all tables."""
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# Actualiza automáticamente `updated_at` en Ticket cuando hay cambios persistentes.
# Esto evita olvidos de actualizar la marca temporal en distintos puntos del código.
@event.listens_for(Session, "before_flush")
def _auto_update_ticket_timestamp(session, flush_context, instances) -> None:
    try:
        # Importar aquí para evitar importaciones circulares al cargar modelos.
        from .models import Ticket

        for obj in session.dirty:
            # session.dirty incluye objetos no persistidos; filtramos por instancia.
            if isinstance(obj, Ticket):
                # Solo tocar si el objeto ya existe en la BD (tiene PK) para evitar
                # establecer updated_at en instancias nuevas hasta que se inserten.
                if getattr(obj, "id", None) is not None:
                    obj.updated_at = datetime.utcnow()
    except Exception:
        # Protegemos el listener: no queremos que una excepción rompa el flush.
        pass

