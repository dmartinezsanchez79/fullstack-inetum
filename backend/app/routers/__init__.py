"""
Reexporta routers disponibles para conectarlos en `app.main`.

`main.py` hace:
    app.include_router(auth.router)
    app.include_router(tickets.router)
"""

from .auth import router as auth
from .tickets import router as tickets

__all__ = ["auth", "tickets"]
