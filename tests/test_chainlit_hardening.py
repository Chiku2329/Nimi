import unittest
import uuid

from chainlit.session import BaseSession
from chainlit_hardening import apply_chainlit_session_guard, canonical_session_id


class SessionIdGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apply_chainlit_session_guard()

    def make_session(self, session_id):
        return BaseSession(
            id=session_id,
            client_type="webapp",
            thread_id=None,
            user=None,
            token=None,
            user_env={},
        )

    def test_accepts_canonical_uuid(self):
        value = str(uuid.uuid4())
        self.assertEqual(canonical_session_id(value), value)
        self.assertEqual(self.make_session(value).id, value)

    def test_rejects_path_traversal_at_session_boundary(self):
        for value in ("../../data", "/etc", "..%2f..%2fdata", "a" * 36, None):
            with self.subTest(value=value):
                with self.assertRaises(ConnectionRefusedError):
                    canonical_session_id(value)
                with self.assertRaises(ConnectionRefusedError):
                    self.make_session(value)

    def test_rejects_noncanonical_uuid(self):
        with self.assertRaises(ConnectionRefusedError):
            canonical_session_id("{" + str(uuid.uuid4()) + "}")


if __name__ == "__main__":
    unittest.main()
