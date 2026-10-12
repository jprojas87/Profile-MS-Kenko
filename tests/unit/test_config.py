import pytest
from pydantic import ValidationError

from app.config import Settings


def test_hs256_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rs256_requires_public_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.delenv("JWT_PUBLIC_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_hs256_rejects_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "demasiado-corto")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "x" * 32
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", secret)
    monkeypatch.setenv("ENVIRONMENT", "prod")

    settings = Settings(_env_file=None)

    assert settings.environment == "prod"
    assert settings.jwt_secret is not None
    assert settings.jwt_secret.get_secret_value() == secret
