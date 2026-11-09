import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from file_storage import PrivateLocalStorageClient


class PrivateLocalStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(
            "os.environ",
            {"NIMI_STORAGE_SECRET": "s" * 48},
            clear=False,
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.storage = PrivateLocalStorageClient(self.temp_dir.name)

    def test_upload_and_signed_read_url_round_trip(self):
        async def run():
            result = await self.storage.upload_file(
                "guest-db-id/element-id/report.txt",
                b"private attachment",
                mime="text/plain",
            )
            self.assertEqual(
                result["object_key"], "guest-db-id/element-id/report.txt"
            )
            url = await self.storage.get_read_url(result["object_key"])
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            path = parsed.path.removeprefix("/private-storage/")
            expires = int(query["expires"][0])
            signature = query["signature"][0]
            resolved = self.storage.resolve_signed_file(path, expires, signature)
            self.assertEqual(resolved.read_bytes(), b"private attachment")

        asyncio.run(run())

    def test_tampered_signature_is_rejected(self):
        async def run():
            await self.storage.upload_file("user/element/file.txt", b"secret")
            url = await self.storage.get_read_url("user/element/file.txt")
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            signature = query["signature"][0]
            tampered = ("0" if signature[0] != "0" else "1") + signature[1:]
            with self.assertRaises(ValueError):
                self.storage.resolve_signed_file(
                    "user/element/file.txt",
                    int(query["expires"][0]),
                    tampered,
                )

        asyncio.run(run())

    def test_expired_url_is_rejected(self):
        with self.assertRaises(ValueError):
            self.storage.resolve_signed_file(
                "user/element/file.txt", int(time.time()) - 1, "invalid"
            )

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.storage._safe_path("../outside.txt")
        with self.assertRaises(ValueError):
            self.storage._safe_path("/absolute/path.txt")
        with self.assertRaises(ValueError):
            self.storage._safe_path(r"user\..\outside.txt")

    def test_delete_removes_file(self):
        async def run():
            await self.storage.upload_file("user/element/file.txt", b"delete me")
            self.assertTrue(await self.storage.delete_file("user/element/file.txt"))
            self.assertFalse(
                (Path(self.temp_dir.name) / "user/element/file.txt").exists()
            )

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
