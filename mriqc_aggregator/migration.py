from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_migrations(connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
