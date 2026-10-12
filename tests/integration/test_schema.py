from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

import app.db.models  # noqa: F401
from app.db.base import Base


def test_expected_tables_exist(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    assert {"profiles", "processed_events", "alembic_version"} <= tables


def test_migrations_match_models(engine: Engine) -> None:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)

    assert differences == []
