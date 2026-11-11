import io
import os
import tempfile
import unittest
from types import SimpleNamespace

from PIL import Image
from docx import Document
from openpyxl import Workbook
from pptx import Presentation

from uploads import UploadRejected, validate_upload_batch


def make_bytes(writer):
    buffer = io.BytesIO()
    writer(buffer)
    return buffer.getvalue()


def png_bytes():
    return make_bytes(lambda buffer: Image.new("RGB", (2, 2), "white").save(buffer, format="PNG"))


def docx_bytes():
    def write(buffer):
        document = Document()
        document.add_paragraph("Word document content")
        document.save(buffer)
    return make_bytes(write)


def xlsx_bytes():
    def write(buffer):
        workbook = Workbook()
        workbook.active["A1"] = "Spreadsheet content"
        workbook.save(buffer)
    return make_bytes(write)


def pptx_bytes():
    def write(buffer):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        textbox = slide.shapes.add_textbox(0, 0, 3000000, 500000)
        textbox.text = "Presentation content"
        presentation.save(buffer)
    return make_bytes(write)


class UploadValidationTests(unittest.TestCase):
    def make_file(self, name, mime, content):
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(content)
        temp.close()
        self.addCleanup(lambda: os.path.exists(temp.name) and os.unlink(temp.name))
        return SimpleNamespace(name=name, mime=mime, path=temp.name)

    def test_accepts_valid_png(self):
        element = self.make_file("photo.png", "image/png", png_bytes())
        result = validate_upload_batch([element])
        self.assertEqual(result[0]["kind"], "image")

    def test_accepts_word_document_and_extracts_text(self):
        element = self.make_file(
            "notes.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_bytes(),
        )
        result = validate_upload_batch([element])
        self.assertIn("Word document content", result[0]["text"])

    def test_accepts_excel_workbook_and_extracts_cells(self):
        element = self.make_file(
            "data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            xlsx_bytes(),
        )
        result = validate_upload_batch([element])
        self.assertIn("Spreadsheet content", result[0]["text"])

    def test_accepts_powerpoint_and_extracts_slide_text(self):
        element = self.make_file(
            "slides.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            pptx_bytes(),
        )
        result = validate_upload_batch([element])
        self.assertIn("Presentation content", result[0]["text"])

    def test_accepts_json_and_source_code(self):
        for name, mime, content in (
            ("data.json", "application/json", b'{"ok": true}'),
            ("script.py", "text/x-python", b"print('hello')"),
        ):
            element = self.make_file(name, mime, content)
            result = validate_upload_batch([element])
            self.assertTrue(result[0]["text"])

    def test_rejects_mismatched_image_mime(self):
        element = self.make_file("photo.png", "text/plain", png_bytes())
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_fake_pdf(self):
        element = self.make_file("file.pdf", "application/pdf", b"not a pdf")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_binary_disguised_as_text(self):
        element = self.make_file("file.txt", "text/plain", b"hello\\x00world")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_unsupported_executable(self):
        element = self.make_file("program.exe", "application/octet-stream", b"MZ\\x00")
        with self.assertRaises(UploadRejected):
            validate_upload_batch([element])

    def test_rejects_too_many_files(self):
        elements = [self.make_file(f"{i}.txt", "text/plain", b"hello") for i in range(6)]
        with self.assertRaises(UploadRejected):
            validate_upload_batch(elements)

    def test_rejects_excessive_combined_extracted_text(self):
        elements = [self.make_file(f"{i}.txt", "text/plain", b"x" * 11000) for i in range(3)]
        with self.assertRaises(UploadRejected):
            validate_upload_batch(elements)


if __name__ == "__main__":
    unittest.main()
