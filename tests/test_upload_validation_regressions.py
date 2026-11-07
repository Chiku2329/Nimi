import os
import tempfile
import unittest
from types import SimpleNamespace

from uploads import (
    MAX_FILE_BYTES,
    MAX_FILE_CHARS,
    UploadRejected,
    validate_upload_batch,
)


class UploadValidationTests(unittest.TestCase):
    def make_file(self, name, mime, content):
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(content)
        temp.close()
        self.addCleanup(lambda: os.path.exists(temp.name) and os.unlink(temp.name))
        return SimpleNamespace(name=name, mime=mime, path=temp.name)

    def test_accepts_valid_png_signature(self):
        element = self.make_file("photo.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"x" * 8)
        result = validate_upload_batch([element])
        self.assertEqual(result[0]["kind"], "image")

    def test_accepts_utf8_text(self):
        element = self.make_file("notes.txt", "text/plain", "hello — Nimi".encode("utf-8"))
        result = validate_upload_batch([element])
        self.assertEqual(result[0]["text"], "hello — Nimi")

    def test_rejects_mismatched_mime(self):
        element = self.make_file("photo.png", "text/plain", b"\x89PNG\r\n\x1a\n")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_fake_pdf(self):
        element = self.make_file("file.pdf", "application/pdf", b"not a pdf")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_bad_image_signature(self):
        element = self.make_file("photo.png", "image/png", b"not really a png")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_binary_disguised_as_text(self):
        element = self.make_file("file.txt", "text/plain", b"hello\x00world")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_invalid_utf8(self):
        element = self.make_file("file.txt", "text/plain", b"\xff\xfe\xfa")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_oversized_file(self):
        element = self.make_file("large.txt", "text/plain", b"x" * (MAX_FILE_BYTES + 1))
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_too_many_files(self):
        elements = [
            self.make_file(f"{i}.txt", "text/plain", b"hello")
            for i in range(4)
        ]
        with self.assertRaises(UploadRejected):
            validate_upload_batch(elements)

    def test_rejects_excessive_combined_extracted_text(self):
        elements = [
            self.make_file(f"{i}.txt", "text/plain", b"x" * 11000)
            for i in range(3)
        ]
        with self.assertRaises(UploadRejected):
            validate_upload_batch(elements)

    def test_truncates_single_text_file_to_character_limit(self):
        element = self.make_file("long.txt", "text/plain", b"x" * (MAX_FILE_CHARS + 100))
        result = validate_upload_batch([element])
        self.assertEqual(len(result[0]["text"]), MAX_FILE_CHARS)

    def test_rejects_symlink(self):
        target = self.make_file("target.txt", "text/plain", b"safe")
        link_path = target.path + ".link"
        os.symlink(target.path, link_path)
        self.addCleanup(lambda: os.path.lexists(link_path) and os.unlink(link_path))
        link = SimpleNamespace(name="linked.txt", mime="text/plain", path=link_path)
        with self.assertRaises(UploadRejected):
            validate_upload_batch([link])


if __name__ == "__main__":
    unittest.main()
