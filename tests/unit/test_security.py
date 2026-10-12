import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import Settings
from app.core.security import decode_access_token
from app.domain.exceptions import AuthenticationFailedError
from tests.factories import TEST_JWT_SECRET, make_token

SECRET = TEST_JWT_SECRET


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    return Settings(_env_file=None, jwt_secret=SECRET)  # type: ignore[call-arg]


def test_valid_token_returns_user_id(settings: Settings) -> None:
    user_id = uuid.uuid4()
    token = make_token(user_id)

    assert decode_access_token(token, settings) == user_id


def test_expired_token_is_rejected(settings: Settings) -> None:
    token = make_token(uuid.uuid4(), expires_in=timedelta(minutes=-1))

    with pytest.raises(AuthenticationFailedError):
        decode_access_token(token, settings)


def test_wrong_signature_is_rejected(settings: Settings) -> None:
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, "otro-secreto-con-al-menos-32-bytes!!!", algorithm="HS256")

    with pytest.raises(AuthenticationFailedError):
        decode_access_token(token, settings)


def test_unsigned_token_is_rejected(settings: Settings) -> None:
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, None, algorithm="none")

    with pytest.raises(AuthenticationFailedError):
        decode_access_token(token, settings)


def test_token_without_subject_is_rejected(settings: Settings) -> None:
    payload = {"exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    with pytest.raises(AuthenticationFailedError):
        decode_access_token(token, settings)


def test_subject_must_be_uuid(settings: Settings) -> None:
    token = make_token("no-es-uuid")

    with pytest.raises(AuthenticationFailedError):
        decode_access_token(token, settings)


def test_issuer_is_validated_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    settings = Settings(_env_file=None, jwt_secret=SECRET, jwt_issuer="kenko-auth")  # type: ignore[call-arg]

    wrong_issuer = make_token(uuid.uuid4(), iss="otro-emisor")
    right_issuer = make_token(uuid.uuid4(), iss="kenko-auth")

    with pytest.raises(AuthenticationFailedError):
        decode_access_token(wrong_issuer, settings)
    assert decode_access_token(right_issuer, settings)
