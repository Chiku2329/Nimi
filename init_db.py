import os
import sqlite3

from db_migrations import migrate_sqlite_schema
from data_directory import resolve_data_dir

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    "id" UUID PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL,
    "createdAt" TEXT
);
CREATE TABLE IF NOT EXISTS threads (
    "id" UUID PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" UUID,
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS steps (
    "id" UUID PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" UUID NOT NULL,
    "parentId" UUID,
    "streaming" BOOLEAN NOT NULL,
    "waitForAnswer" BOOLEAN,
    "isError" BOOLEAN,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "command" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" JSONB,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INT,
    "defaultOpen" BOOLEAN,
    "autoCollapse" BOOLEAN,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);
ALTER TABLE steps ADD COLUMN IF NOT EXISTS "modes" JSONB;
ALTER TABLE steps ADD COLUMN IF NOT EXISTS "autoCollapse" BOOLEAN;
CREATE TABLE IF NOT EXISTS elements (
    "id" UUID PRIMARY KEY,
    "threadId" UUID,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" UUID,
    "mime" TEXT,
    "props" JSONB
);
CREATE TABLE IF NOT EXISTS feedbacks (
    "id" UUID PRIMARY KEY,
    "forId" UUID NOT NULL,
    "threadId" UUID NOT NULL,
    "value" INT NOT NULL,
    "comment" TEXT
);
CREATE TABLE IF NOT EXISTS nimi_memories (
    "id" SERIAL PRIMARY KEY,
    "user_key" TEXT NOT NULL,
    "fact" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nimi_rate_limits (
    "user_key" TEXT PRIMARY KEY,
    "window_start" BIGINT NOT NULL,
    "request_count" INTEGER NOT NULL
);
"""

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    "id" TEXT PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" TEXT NOT NULL,
    "createdAt" TEXT
);
CREATE TABLE IF NOT EXISTS threads (
    "id" TEXT PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" TEXT,
    "userIdentifier" TEXT,
    "tags" TEXT,
    "metadata" TEXT,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS steps (
    "id" TEXT PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "parentId" TEXT,
    "streaming" INTEGER NOT NULL,
    "waitForAnswer" INTEGER,
    "isError" INTEGER,
    "metadata" TEXT,
    "tags" TEXT,
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "command" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" TEXT,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INTEGER,
    "defaultOpen" INTEGER,
    "autoCollapse" INTEGER,
    "modes" TEXT
);
CREATE TABLE IF NOT EXISTS elements (
    "id" TEXT PRIMARY KEY,
    "threadId" TEXT,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INTEGER,
    "language" TEXT,
    "forId" TEXT,
    "mime" TEXT,
    "props" TEXT
);
CREATE TABLE IF NOT EXISTS feedbacks (
    "id" TEXT PRIMARY KEY,
    "forId" TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "value" INTEGER NOT NULL,
    "comment" TEXT
);
CREATE TABLE IF NOT EXISTS nimi_memories (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "user_key" TEXT NOT NULL,
    "fact" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nimi_rate_limits (
    "user_key" TEXT PRIMARY KEY,
    "window_start" INTEGER NOT NULL,
    "request_count" INTEGER NOT NULL
);
"""


database_url = os.environ.get("DATABASE_URL", "").strip()

if database_url:
    import psycopg2

    con = psycopg2.connect(database_url)
    cur = con.cursor()
    cur.execute(PG_SCHEMA)
    con.commit()
    con.close()
    print("Postgres ready", flush=True)
else:
    data_dir = resolve_data_dir()
    con = sqlite3.connect(os.path.join(data_dir, "chat.db"))
    con.executescript(SQLITE_SCHEMA)
    migrate_sqlite_schema(con)
    con.commit()
    con.close()
    print("SQLite ready in", data_dir, flush=True)
