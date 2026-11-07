"""Database-backed per-guest request limits for public Nimi access."""

import os
import sqlite3
import time

REQUESTS_PER_MINUTE = 10


def allow_chat_request(user_key: str, now: float | None = None) -> bool:
    """Atomically allow at most REQUESTS_PER_MINUTE messages per guest per minute.

    Uses the shared PostgreSQL database when configured, otherwise the persistent
    SQLite database. Database errors intentionally propagate so callers can fail
    closed rather than silently disabling abuse protection.
    """
    if not isinstance(user_key, str) or not user_key or len(user_key) > 128:
        raise ValueError("A valid guest identifier is required.")

    timestamp = int(time.time() if now is None else now)
    window_start = timestamp - (timestamp % 60)

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        import psycopg2

        with psycopg2.connect(database_url) as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO nimi_rate_limits (user_key, window_start, request_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (user_key) DO UPDATE SET
                        window_start = EXCLUDED.window_start,
                        request_count = CASE
                            WHEN nimi_rate_limits.window_start = EXCLUDED.window_start
                            THEN nimi_rate_limits.request_count + 1
                            ELSE 1
                        END
                    RETURNING request_count
                    """,
                    (user_key, window_start),
                )
                count = cur.fetchone()[0]
        return count <= REQUESTS_PER_MINUTE

    data_dir = os.environ.get("DATA_DIR", ".")
    db_path = os.path.join(data_dir, "chat.db")
    with sqlite3.connect(db_path, timeout=10) as con:
        con.execute(
            """
            INSERT INTO nimi_rate_limits (user_key, window_start, request_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_key) DO UPDATE SET
                window_start = excluded.window_start,
                request_count = CASE
                    WHEN nimi_rate_limits.window_start = excluded.window_start
                    THEN nimi_rate_limits.request_count + 1
                    ELSE 1
                END
            """,
            (user_key, window_start),
        )
        count = con.execute(
            "SELECT request_count FROM nimi_rate_limits WHERE user_key = ?",
            (user_key,),
        ).fetchone()[0]
    return count <= REQUESTS_PER_MINUTE
