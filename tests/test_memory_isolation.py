"""Regression tests for browser-scoped private memory isolation."""

import importlib
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class PrivateMemoryIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import the real app module with a harmless test key. No API requests
        # are made by these tests.
        cls.env = patch.dict(
            os.environ,
            {"API_KEY": "unit-test-only-not-a-real-key", "DATABASE_URL": ""},
            clear=False,
        )
        cls.env.start()
        cls.app = importlib.import_module("app")

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_data_dir = self.app.DATA_DIR
        self.app.DATA_DIR = self.temp_dir.name
        with sqlite3.connect(os.path.join(self.temp_dir.name, "chat.db")) as con:
            con.execute(
                """
                CREATE TABLE nimi_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_key TEXT NOT NULL,
                    fact TEXT NOT NULL
                )
                """
            )

    def tearDown(self):
        self.app.DATA_DIR = self.previous_data_dir
        self.temp_dir.cleanup()

    def memories_for(self, guest_id):
        with patch.object(self.app, "user_key", return_value=guest_id):
            return self.app.get_memories()

    def save_for(self, guest_id, facts):
        with patch.object(self.app, "user_key", return_value=guest_id):
            self.app.set_memories(facts)

    def test_guests_cannot_read_each_others_memories(self):
        self.save_for("guest_alpha", ["Alpha private fact"])
        self.save_for("guest_beta", ["Beta private fact"])

        self.assertEqual(self.memories_for("guest_alpha"), ["Alpha private fact"])
        self.assertEqual(self.memories_for("guest_beta"), ["Beta private fact"])

    def test_clearing_one_guests_memory_does_not_clear_another(self):
        self.save_for("guest_alpha", ["Alpha private fact"])
        self.save_for("guest_beta", ["Beta private fact"])

        self.save_for("guest_alpha", [])

        self.assertEqual(self.memories_for("guest_alpha"), [])
        self.assertEqual(self.memories_for("guest_beta"), ["Beta private fact"])

    def test_memory_updates_replace_only_the_current_guests_facts(self):
        self.save_for("guest_alpha", ["Old fact"])
        self.save_for("guest_beta", ["Other guest fact"])

        self.save_for("guest_alpha", ["Updated fact"])

        self.assertEqual(self.memories_for("guest_alpha"), ["Updated fact"])
        self.assertEqual(self.memories_for("guest_beta"), ["Other guest fact"])


    def test_memory_read_failure_is_not_mistaken_for_empty_memory(self):
        with sqlite3.connect(os.path.join(self.temp_dir.name, "chat.db")) as con:
            con.execute("DROP TABLE nimi_memories")
        with patch.object(self.app, "user_key", return_value="guest_alpha"):
            with self.assertRaises(sqlite3.OperationalError):
                self.app.get_memories()

    def test_memory_write_failure_is_reported_to_caller(self):
        with sqlite3.connect(os.path.join(self.temp_dir.name, "chat.db")) as con:
            con.execute("DROP TABLE nimi_memories")
        with patch.object(self.app, "user_key", return_value="guest_alpha"):
            with self.assertRaises(sqlite3.OperationalError):
                self.app.set_memories(["a private fact"])

    def test_memory_storage_enforces_item_and_character_limits(self):
        oversized = "x" * (self.app.MAX_MEMORY_FACT_CHARS + 1)
        self.save_for("guest_alpha", ["valid fact", oversized, " " * 2])
        self.assertEqual(self.memories_for("guest_alpha"), ["valid fact"])

    def test_memory_storage_caps_number_of_facts(self):
        facts = [f"fact {index}" for index in range(self.app.MAX_MEMORY_ITEMS + 10)]
        self.save_for("guest_alpha", facts)
        saved = self.memories_for("guest_alpha")
        self.assertEqual(len(saved), self.app.MAX_MEMORY_ITEMS)

    def test_memory_storage_caps_total_characters(self):
        facts = [f"{index}:" + ("x" * 490) for index in range(30)]
        self.save_for("guest_alpha", facts)
        saved = self.memories_for("guest_alpha")
        self.assertLessEqual(sum(len(fact) for fact in saved), self.app.MAX_MEMORY_TOTAL_CHARS)

    def test_remember_refuses_to_exceed_memory_item_limit(self):
        facts = [f"fact {index}" for index in range(self.app.MAX_MEMORY_ITEMS)]
        self.save_for("guest_alpha", facts)
        with patch.object(self.app, "user_key", return_value="guest_alpha"):
            result = self.app.remember("one more fact")
        self.assertIn("full", result.lower())
        self.assertEqual(self.memories_for("guest_alpha"), facts)

    def test_remember_rejects_oversized_fact(self):
        with patch.object(self.app, "user_key", return_value="guest_alpha"):
            result = self.app.remember("x" * (self.app.MAX_MEMORY_FACT_CHARS + 1))
        self.assertIn("too long", result.lower())
        self.assertEqual(self.memories_for("guest_alpha"), [])


if __name__ == "__main__":
    unittest.main()
