import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.session import create_db_engine

ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://profile:profile@localhost:5432/profile_test"
)
# Los tests de integración usan una base dedicada; nunca apuntar a la base de desarrollo.
_TEST_DB_NAME = re.compile(r"^[a-z_]+_test$")

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def _reset_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def test_database() -> str:
    url = make_url(TEST_DATABASE_URL)
    assert url.database and _TEST_DB_NAME.match(url.database), (
        "TEST_DATABASE_URL debe apuntar a una base que termine en _test"
    )
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin_engine.dispose()
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def migrated_database(test_database: str) -> str:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return test_database


@pytest.fixture(scope="session")
def engine(migrated_database: str) -> Iterator[Engine]:
    db_engine = create_db_engine(migrated_database)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE profiles, processed_events"))
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
        session.commit()
    finally:
        session.close()
