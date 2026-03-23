"""
Seguridad: hash de contraseñas y JWT.

Este módulo se encarga de:
- `get_password_hash`: transformar una contraseña en un hash (no se guarda en claro).
- `verify_password`: comparar contraseña introducida vs hash almacenado.
- `create_access_token`: firmar un JWT con un payload.
- `decode_access_token`: decodificar/verificar el JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from .config import settings

# Por problemas con la build de bcrypt en tu entorno,
# usamos pbkdf2_sha256 (seguro y sin límite de 72 bytes).
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si `plain_password` corresponde al `hashed_password`."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña con el esquema configurado."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """
    Crea un JWT firmado.

    `data` se mete dentro del token (payload) y se añade siempre:
    - `exp`: fecha de expiración
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y verifica la firma del JWT. Lanza error si es inválido/expirado."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return payload

