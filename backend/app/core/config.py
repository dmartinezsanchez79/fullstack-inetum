"""
Configuración central del backend.

Se basa en `pydantic-settings` (`BaseSettings`) para permitir que la configuración
se lea desde variables de entorno (y opcionalmente un fichero `.env`).
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración centralizada leída desde variables de entorno y `.env`.

    Valores por defecto adecuados para desarrollo. En producción debe establecerse
    SECRET_KEY y ajustar CORS/otros mediante variables de entorno.
    """

    app_name: str = "Portal de Incidencias"
    secret_key: str = Field("CHANGE_ME_SUPER_SECRET_KEY", env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

