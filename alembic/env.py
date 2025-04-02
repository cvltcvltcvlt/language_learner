from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
from models import Base
from config import Database

config = context.config

# Настройка логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подключаем метаданные моделей
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Запускаем миграции в оффлайн-режиме"""
    url = Database.DATABASE_URL.replace("asyncpg", "psycopg2")  # Меняем драйвер!
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Запускаем миграции в онлайн-режиме"""
    sync_url = Database.DATABASE_URL.replace("asyncpg", "psycopg2")  # Меняем драйвер!
    connectable = create_engine(sync_url, poolclass=pool.NullPool)  # Синхронный движок!

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
