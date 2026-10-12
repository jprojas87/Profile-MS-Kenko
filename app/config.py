from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["dev", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = Field(
        ..., description="Ej.: postgresql+psycopg://user:pass@host:5432/profile"
    )

    jwt_algorithm: Literal["HS256", "RS256"] = "HS256"
    jwt_secret: SecretStr | None = None
    jwt_public_key: str | None = None
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    @model_validator(mode="after")
    def _check_jwt_key_material(self) -> "Settings":
        if self.jwt_algorithm == "HS256" and (
            not self.jwt_secret or len(self.jwt_secret.get_secret_value()) < 32
        ):
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres con JWT_ALGORITHM=HS256")
        if self.jwt_algorithm == "RS256" and not self.jwt_public_key:
            raise ValueError("JWT_PUBLIC_KEY es obligatorio cuando JWT_ALGORITHM=RS256")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
