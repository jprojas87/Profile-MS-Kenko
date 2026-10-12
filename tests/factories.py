import uuid
from datetime import date
from typing import Any

from app.db.models.profile import Profile
from app.domain.enums import DocumentType


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
