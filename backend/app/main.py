"""
Punto de entrada de la aplicación FastAPI.

Responsabilidades:
- Configurar CORS y servir el frontend estático.
- En el arranque: crear tablas (SQLite) y sembrar datos demo.
- Registrar routers de autenticación y tickets.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, delete, select

from .core.config import settings
from .db import engine, init_db
from .models import Comment, Ticket
from .routers import auth, tickets
from .services.seed import seed_data

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    Hook de FastAPI que se ejecuta una sola vez al iniciar el servidor.
    Aquí inicializamos:
    1) La base de datos (tablas).
    2) Limpieza de datos huérfanos (comentarios cuyo ticket ya no existe).
    3) Semillas (usuarios demo y tickets de ejemplo).
    """
    init_db()
    with Session(engine) as session:
        # Limpieza: borra comentarios cuyo ticket ya no existe (evita “comentarios heredados”).
        session.exec(
            delete(Comment).where(~Comment.ticket_id.in_(select(Ticket.id)))
        )
        session.commit()
        seed_data(session)


app.include_router(auth)
app.include_router(tickets)

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_dir), html=True),
        name="frontend",
    )

