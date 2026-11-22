"""Read-only dependency checks for Nimi's operational health endpoints."""

import os
import sqlite3
from pathlib import Path


def check_database_ready(database_url: str | None = None, data_dir: str | None = None) -> bool:
    """Return true only when the configured chat database answers SELECT 1.

    This function performs no schema changes and does not inspect user records.
    """
    url = (database_url if database_url is not None else os.environ.get("DATABASE_URL", "")).strip()
    if url:
        import psycopg2

        # The application uses asyncpg's SQLAlchemy URL elsewhere; psycopg2
        # needs the standard PostgreSQL scheme for this short read-only probe.
        conninfo = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        with psycopg2.connect(conninfo, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)

    directory = Path(data_dir if data_dir is not None else os.environ.get("DATA_DIR", ".")).expanduser()
    database_path = directory / "chat.db"
    if not database_path.is_file():
        raise RuntimeError("Nimi's local chat database is not initialized.")

    # Open in SQLite read-only mode: a health probe must not create or mutate it.
    uri = database_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=2) as connection:
        row = connection.execute("SELECT 1").fetchone()
    return row == (1,)
