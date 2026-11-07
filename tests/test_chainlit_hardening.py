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


    def test_files_directory_is_confined_to_chainlit_root(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import chainlit.config

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(chainlit.config, "FILES_DIRECTORY", Path(directory)):
                value = str(uuid.uuid4())
                session = self.make_session(value)
                self.assertEqual(session.files_dir, Path(directory) / value)

    def test_files_directory_revalidates_mutated_session_id(self):
        session = self.make_session(str(uuid.uuid4()))
        session.id = "../../outside"
        with self.assertRaises(ConnectionRefusedError):
            _ = session.files_dir

    def test_files_directory_rejects_symlinked_session_folder(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import chainlit.config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            value = str(uuid.uuid4())
            (root / value).symlink_to(outside, target_is_directory=True)
            with patch.object(chainlit.config, "FILES_DIRECTORY", root):
                session = self.make_session(value)
                with self.assertRaises(ConnectionRefusedError):
                    _ = session.files_dir


if __name__ == "__main__":
    unittest.main()
