from datetime import datetime
from pydantic import BaseModel, EmailStr, constr

from ..models import UserRole

"""
Schemas Pydantic para autenticación.

Estos modelos definen:
- `LoginRequest`: body esperado en login.
- `Token`: respuesta del login (access_token JWT).
- `UserCreate`: payload opcional de registro.
- `UserRead`: respuesta normalizada para devolver info del usuario.
"""


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: EmailStr
    exp: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: constr(min_length=8)
    role: UserRole = UserRole.USER


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

