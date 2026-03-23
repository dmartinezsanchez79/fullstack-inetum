"""
Dependencias comunes para FastAPI.

FastAPI permite declarar dependencias con `Depends(...)`. Esto permite:
- Centralizar la lógica de autenticación (JWT).
- Centralizar la lógica de roles (USER/AGENT).
- Centralizar el acceso a la base de datos (Session SQLModel).

Las funciones de este archivo se reutilizan en los endpoints de `routers/`.
"""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session, select

from .core.security import decode_access_token
from .db import get_session
from .models import User, UserRole
from .schemas.auth import UserRead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator[Session, None, None]:
    """Obtiene una sesión SQLModel/SQLAlchemy para consultar y persistir datos."""
    yield from get_session()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Devuelve el usuario asociado al JWT recibido en `Authorization: Bearer ...`."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Asegura que el usuario esté activo (`is_active=True`)."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


def get_current_agent(current_user: User = Depends(get_current_active_user)) -> User:
    """Asegura que el usuario tenga rol `AGENT`."""
    if current_user.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes: se requiere rol AGENT",
        )
    return current_user


def get_current_user_read(user: User = Depends(get_current_active_user)) -> UserRead:
    """Convierte el modelo `User` (BD) en el esquema `UserRead` (API)."""
    return UserRead.from_orm(user)

