import sqlite3
import unittest

from db_migrations import migrate_sqlite_schema


class SQLiteMigrationTests(unittest.TestCase):
    def make_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE steps (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                threadId TEXT NOT NULL,
                parentId TEXT,
                streaming INTEGER NOT NULL,
                waitForAnswer INTEGER,
                isError INTEGER,
                metadata TEXT,
                tags TEXT,
                input TEXT,
                output TEXT,
                createdAt TEXT,
                command TEXT,
                start TEXT,
                end TEXT,
                generation TEXT,
                showInput TEXT,
                language TEXT,
                indent INTEGER,
                defaultOpen INTEGER
            );
            INSERT INTO steps (id, name, type, threadId, streaming, output)
            VALUES ('step-1', 'hello', 'assistant_message', 'thread-1', 0, 'preserve me');
            """
        )
        return connection

    def test_adds_missing_chainlit_columns_without_losing_rows(self):
        connection = self.make_connection()
        try:
            migrate_sqlite_schema(connection)
            columns = {
                row[1] for row in connection.execute('PRAGMA table_info("steps")')
            }
            self.assertIn("modes", columns)
            self.assertIn("autoCollapse", columns)
            row = connection.execute(
                "SELECT output FROM steps WHERE id = 'step-1'"
            ).fetchone()
            self.assertEqual(row[0], "preserve me")
        finally:
            connection.close()

    def test_migration_is_idempotent(self):
        connection = self.make_connection()
        try:
            migrate_sqlite_schema(connection)
            migrate_sqlite_schema(connection)
            columns = [
                row[1] for row in connection.execute('PRAGMA table_info("steps")')
            ]
            self.assertEqual(columns.count("modes"), 1)
            self.assertEqual(columns.count("autoCollapse"), 1)
        finally:
            connection.close()

    def test_preserves_existing_optional_column_values(self):
        connection = self.make_connection()
        try:
            connection.execute(
                'ALTER TABLE steps ADD COLUMN "autoCollapse" INTEGER'
            )
            connection.execute(
                "UPDATE steps SET autoCollapse = 1 WHERE id = 'step-1'"
            )
            migrate_sqlite_schema(connection)
            value = connection.execute(
                "SELECT autoCollapse FROM steps WHERE id = 'step-1'"
            ).fetchone()[0]
            self.assertEqual(value, 1)
        finally:
            connection.close()

    def test_fails_clearly_if_steps_table_is_missing(self):
        connection = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(RuntimeError, "steps table"):
                migrate_sqlite_schema(connection)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
