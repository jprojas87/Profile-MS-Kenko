import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import jwt

from app.config import get_settings
from app.db.models.profile import Profile
from app.domain.enums import DocumentType

TEST_JWT_SECRET = "test-secret-with-at-least-32-bytes!!"


def make_token(
    user_id: uuid.UUID | str,
    *,
    expires_in: timedelta = timedelta(minutes=15),
    **claims: Any,
) -> str:
    settings = get_settings()
    assert settings.jwt_secret is not None
    now = datetime.now(UTC)
    payload: dict[str, Any] = {"sub": str(user_id), "iat": now, "exp": now + expires_in}
    payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def make_profile(**overrides: Any) -> Profile:
    values: dict[str, Any] = {
        "user_id": uuid.uuid4(),
        "email": "maria.gomez@example.com",
        "first_name": "María Fernanda",
        "last_name": "Gómez Rojas",
        "document_type": DocumentType.CC,
        "document_number": "1020304050",
        "birth_date": date(1995, 3, 21),
        "gender": "female",
        "phone": "+573001234567",
        "address_line": "Cra 15 # 93-60 Apto 402",
        "city": "Bogotá",
    }
    values.update(overrides)
    return Profile(**values)
