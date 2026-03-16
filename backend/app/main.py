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

