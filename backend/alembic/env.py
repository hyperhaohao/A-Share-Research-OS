"""Alembic environment for A-Share Research OS (sync migrations)."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from app.config import get_settings
from app.storage.orm import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# All ORM metadata for autogenerate support.
target_metadata = Base.metadata


def _database_url() -> str:
    import os

    return os.environ.get("ASRO_DATABASE_URL") or get_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DBAPI connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite-friendly ALTERs
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # noqa: ANN001
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
