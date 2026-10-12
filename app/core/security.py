import uuid
from typing import Any

import jwt

from app.config import Settings
from app.domain.exceptions import AuthenticationFailedError

INVALID_TOKEN_MESSAGE = "Token no válido"


def _verification_key(settings: Settings) -> str:
    if settings.jwt_algorithm == "HS256" and settings.jwt_secret is not None:
        return settings.jwt_secret.get_secret_value()
    if settings.jwt_algorithm == "RS256" and settings.jwt_public_key:
        return settings.jwt_public_key
    raise RuntimeError("Clave JWT no configurada para el algoritmo elegido")


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Valida un JWT emitido por Authentication y devuelve el userId (claim sub)."""
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            _verification_key(settings),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer or None,
            audience=settings.jwt_audience or None,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationFailedError(INVALID_TOKEN_MESSAGE) from exc

    try:
        return uuid.UUID(str(claims["sub"]))
    except ValueError as exc:
        raise AuthenticationFailedError(INVALID_TOKEN_MESSAGE) from exc
