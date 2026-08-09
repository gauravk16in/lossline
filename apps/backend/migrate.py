"""Run Alembic under a PostgreSQL advisory lock during deployment builds."""
from __future__ import annotations
import os
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config

url = os.environ.get("DIRECT_DATABASE_URL", "")
if not url:
    raise SystemExit("DIRECT_DATABASE_URL is required for migrations")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
engine = create_engine(url)
config = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
with engine.connect() as connection:
    connection.execute(text("SELECT pg_advisory_lock(hashtext('lossline_alembic'))"))
    try:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    finally:
        connection.execute(text("SELECT pg_advisory_unlock(hashtext('lossline_alembic'))"))
