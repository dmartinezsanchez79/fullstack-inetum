from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Portal de Incidencias"
    secret_key: str = "CHANGE_ME_SUPER_SECRET_KEY"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["*"]


settings = Settings()

