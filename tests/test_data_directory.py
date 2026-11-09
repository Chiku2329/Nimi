import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_directory import resolve_data_dir


class DataDirectoryTests(unittest.TestCase):
    def test_uses_configured_directory_when_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"DATA_DIR": directory}, clear=True):
                self.assertEqual(resolve_data_dir(), str(Path(directory).resolve()))

    def test_fails_closed_instead_of_falling_back_when_configured_path_is_unavailable(self):
        with patch.dict(os.environ, {"DATA_DIR": "/unavailable/nimi-data"}, clear=True):
            with patch("data_directory.Path.mkdir", side_effect=PermissionError("read-only")):
                with self.assertRaisesRegex(RuntimeError, "Refusing to fall back"):
                    resolve_data_dir()

    def test_default_directory_is_still_supported_for_local_development(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                # The default is the current working directory.
                self.assertEqual(resolve_data_dir(), str(Path(".").resolve()))


if __name__ == "__main__":
    unittest.main()
