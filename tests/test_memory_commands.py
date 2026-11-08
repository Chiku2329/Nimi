"""Regression tests for user-facing private memory commands."""

import importlib
import os
import unittest
from unittest.mock import patch


class MemoryCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

    def test_forget_memory_by_number_removes_only_selected_item(self):
        with patch.object(
            self.app, "get_memories",
            return_value=["first private fact", "second private fact", "third private fact"],
        ), patch.object(self.app, "set_memories") as save:
            result = self.app.forget_memory_by_number("2")

        self.assertEqual(result, "Removed memory 2: second private fact")
        save.assert_called_once_with(["first private fact", "third private fact"])

    def test_forget_memory_rejects_missing_or_non_numeric_argument(self):
        with patch.object(self.app, "get_memories") as read, patch.object(
            self.app, "set_memories"
        ) as save:
            result = self.app.forget_memory_by_number("two")

        self.assertIn("/forget-memory 2", result)
        read.assert_not_called()
        save.assert_not_called()

    def test_forget_memory_rejects_out_of_range_number(self):
        with patch.object(self.app, "get_memories", return_value=["only fact"]), patch.object(
            self.app, "set_memories"
        ) as save:
            result = self.app.forget_memory_by_number("2")

        self.assertEqual(result, "Choose a number between 1 and 1.")
        save.assert_not_called()

    def test_forget_memory_handles_empty_list(self):
        with patch.object(self.app, "get_memories", return_value=[]), patch.object(
            self.app, "set_memories"
        ) as save:
            result = self.app.forget_memory_by_number("1")

        self.assertEqual(result, "You have no saved memories to remove.")
        save.assert_not_called()

    def test_keyword_forget_rejects_empty_keyword_without_writing(self):
        with patch.object(self.app, "get_memories", return_value=["private fact"]), patch.object(
            self.app, "set_memories"
        ) as save:
            result = self.app.forget("  ")

        self.assertIn("provide a word", result.lower())
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
