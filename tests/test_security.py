import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from security import REQUESTS_PER_MINUTE, allow_chat_request


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "chat.db")
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE nimi_rate_limits (
                    user_key TEXT PRIMARY KEY,
                    window_start INTEGER NOT NULL,
                    request_count INTEGER NOT NULL
                )
                """
            )
        self.env = patch.dict(
            os.environ,
            {"DATA_DIR": self.temp_dir.name},
            clear=True,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_allows_limit_then_blocks_excess_requests(self):
        for _ in range(REQUESTS_PER_MINUTE):
            self.assertTrue(allow_chat_request("guest_a", now=120))
        self.assertFalse(allow_chat_request("guest_a", now=120))

    def test_limit_resets_in_next_minute(self):
        for _ in range(REQUESTS_PER_MINUTE + 1):
            allow_chat_request("guest_a", now=120)
        self.assertTrue(allow_chat_request("guest_a", now=180))

    def test_visitors_have_separate_limits(self):
        for _ in range(REQUESTS_PER_MINUTE):
            self.assertTrue(allow_chat_request("guest_a", now=120))
        self.assertTrue(allow_chat_request("guest_b", now=120))


if __name__ == "__main__":
    unittest.main()
