"""Shared per-guest and global request limits for public Nimi."""

import os
import sqlite3
import time

REQUESTS_PER_MINUTE = 10
GLOBAL_REQUESTS_PER_MINUTE = 120
_GLOBAL_KEY = "__nimi_global_request_bucket__"


def _next_count(cursor, user_key, window_start, placeholder):
    cursor.execute(
        f"""
        INSERT INTO nimi_rate_limits (user_key, window_start, request_count)
        VALUES ({placeholder}, {placeholder}, 1)
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
    cursor.execute(
        f"SELECT request_count FROM nimi_rate_limits WHERE user_key = {placeholder}",
        (user_key,),
    )
    return cursor.fetchone()[0]


def allow_chat_request(user_key: str, now: float | None = None) -> bool:
    """Atomically enforce both per-guest and shared global minute limits.

    The global bucket prevents trivial rate-limit evasion by repeatedly clearing
    anonymous cookies. PostgreSQL is shared across replicas; SQLite is used only
    for a single-instance local deployment. Database failures propagate so the
    caller can fail closed.
    """
    if (
        not isinstance(user_key, str)
        or not user_key
        or len(user_key) > 128
        or user_key == _GLOBAL_KEY
    ):
        raise ValueError("A valid guest identifier is required.")

    timestamp = int(time.time() if now is None else now)
    window_start = timestamp - (timestamp % 60)

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        import psycopg2

        with psycopg2.connect(database_url) as con:
            with con.cursor() as cur:
                guest_count = _next_count(cur, user_key, window_start, "%s")
                global_count = _next_count(cur, _GLOBAL_KEY, window_start, "%s")
                if global_count % 100 == 0:
                    cur.execute(
                        "DELETE FROM nimi_rate_limits WHERE window_start < %s",
                        (timestamp - 3600,),
                    )
    else:
        data_dir = os.environ.get("DATA_DIR", ".")
        db_path = os.path.join(data_dir, "chat.db")
        with sqlite3.connect(db_path, timeout=10) as con:
            guest_count = _next_count(con, user_key, window_start, "?")
            global_count = _next_count(con, _GLOBAL_KEY, window_start, "?")
            if global_count % 100 == 0:
                con.execute(
                    "DELETE FROM nimi_rate_limits WHERE window_start < ?",
                    (timestamp - 3600,),
                )

    return (
        guest_count <= REQUESTS_PER_MINUTE
        and global_count <= GLOBAL_REQUESTS_PER_MINUTE
    )
