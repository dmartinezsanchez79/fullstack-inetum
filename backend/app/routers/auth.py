"""
Rutas de autenticación.

Endpoints:
- POST /api/auth/login -> devuelve access_token (JWT).
- GET  /api/auth/me    -> devuelve información del usuario autenticado.
- POST /api/auth/register -> registro (opcional en este proyecto).

Las rutas dependen de SQLModel para consultar la base de datos y de `core.security`
para verificar/hacer hash de contraseñas y firmar JWT.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..core.config import settings
from ..core.security import create_access_token, get_password_hash, verify_password
from ..db import get_session
from ..deps import get_current_user_read
from ..models import User, UserRole
from ..schemas.auth import LoginRequest, Token, UserCreate, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_session)) -> UserRead:
    """Crea un usuario si el email no existe."""
    existing = db.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead.from_orm(user)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_session)) -> Token:
    """Autentica usuario y devuelve un JWT (access_token)."""
    user = db.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def read_me(current_user: UserRead = Depends(get_current_user_read)) -> UserRead:
    """Devuelve el usuario actual (según el JWT)."""
    return current_user

