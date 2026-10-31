import pytest
from alembic import command
from sqlalchemy import Engine, inspect

from tests.integration.conftest import alembic_config

pytestmark = pytest.mark.integration

IDENTITY_TABLES = {"users", "oauth_identities", "refresh_tokens"}


def test_upgrade_creates_identity_tables(engine: Engine):
    tables = set(inspect(engine).get_table_names())

    assert IDENTITY_TABLES <= tables


def test_migrations_match_the_models(engine: Engine):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.core.database import Base
    from app.modules.identity.infrastructure import models  # noqa: F401

    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert diff == []


def test_downgrade_removes_tables_and_upgrade_restores_them(engine: Engine):
    command.downgrade(alembic_config(), "base")
    try:
        assert not IDENTITY_TABLES & set(inspect(engine).get_table_names())
    finally:
        command.upgrade(alembic_config(), "head")

    assert IDENTITY_TABLES <= set(inspect(engine).get_table_names())
