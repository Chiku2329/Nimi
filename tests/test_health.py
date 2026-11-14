import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from health import check_database_ready


class ReadinessTests(unittest.TestCase):
    def test_sqlite_database_is_checked_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "chat.db")
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE sample (value TEXT)")
            self.assertTrue(check_database_ready(data_dir=directory))
            # A read-only health probe must not create application tables or rows.
            with sqlite3.connect(path) as connection:
                self.assertEqual(
                    connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),
                    [("sample",)],
                )

    def test_missing_sqlite_database_is_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "not initialized"):
                check_database_ready(data_dir=directory)

    def test_postgres_probe_uses_select_one_and_short_timeout(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        with patch("psycopg2.connect", return_value=connection) as connect:
            self.assertTrue(
                check_database_ready("postgresql+asyncpg://user:pass@db.example/nimi")
            )
        connect.assert_called_once_with(
            "postgresql://user:pass@db.example/nimi", connect_timeout=3
        )
        cursor.execute.assert_called_once_with("SELECT 1")


if __name__ == "__main__":
    unittest.main()
