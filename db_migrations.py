"""Small, additive SQLite schema migrations for Nimi's Chainlit data layer."""

import sqlite3


def migrate_sqlite_schema(connection: sqlite3.Connection) -> None:
    """Add optional Chainlit step columns missing from older SQLite databases.

    This migration is deliberately additive: it never drops, renames, or
    rewrites existing tables or user data. It is safe to run at every startup.
    """
    rows = connection.execute('PRAGMA table_info("steps")').fetchall()
    if not rows:
        raise RuntimeError("The SQLite steps table was not initialized.")

    existing = {row[1] for row in rows}
    additions = {
        "modes": "TEXT",
        "autoCollapse": "INTEGER",
    }
    for column, sql_type in additions.items():
        if column not in existing:
            connection.execute(
                f'ALTER TABLE steps ADD COLUMN "{column}" {sql_type}'
            )
            existing.add(column)
