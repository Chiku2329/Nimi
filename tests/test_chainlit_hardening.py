import unittest
import uuid

from chainlit_hardening import canonical_session_id


class SessionIdGuardTests(unittest.TestCase):
    def test_accepts_canonical_uuid(self):
        value = str(uuid.uuid4())
        self.assertEqual(canonical_session_id(value), value)

    def test_rejects_path_traversal(self):
        for value in ("../../data", "/etc", "..%2f..%2fdata", "a" * 36, None):
            with self.subTest(value=value):
                with self.assertRaises(ConnectionRefusedError):
                    canonical_session_id(value)

    def test_rejects_noncanonical_uuid(self):
        with self.assertRaises(ConnectionRefusedError):
            canonical_session_id("{" + str(uuid.uuid4()) + "}")


if __name__ == "__main__":
    unittest.main()
