import json
import unittest
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader

from file_creation import FileCreationRejected, create_file


class FileCreationTests(unittest.TestCase):
    def test_creates_word_document(self):
        name, mime, data = create_file("docx", "notes", "Hello from Nimi")
        self.assertEqual(name, "notes.docx")
        doc = Document(__import__("io").BytesIO(data))
        self.assertIn("Hello from Nimi", [p.text for p in doc.paragraphs])

    def test_creates_pdf(self):
        _, mime, data = create_file("pdf", "report", "A generated report")
        reader = PdfReader(__import__("io").BytesIO(data))
        self.assertIn("A generated report", reader.pages[0].extract_text())

    def test_creates_excel_from_csv_rows(self):
        _, _, data = create_file("xlsx", "data", "Name,Score\nAda,95")
        workbook = load_workbook(__import__("io").BytesIO(data), read_only=True)
        self.assertEqual(workbook.active["A2"].value, "Ada")
        workbook.close()

    def test_creates_powerpoint(self):
        _, _, data = create_file("pptx", "slides", "Welcome\nFirst slide\n---\nSummary\nSecond slide")
        presentation = Presentation(__import__("io").BytesIO(data))
        self.assertEqual(len(presentation.slides), 2)

    def test_json_is_validated_and_pretty_printed(self):
        _, _, data = create_file("json", "data", '{"ok":true}')
        self.assertEqual(json.loads(data), {"ok": True})

    def test_rejects_invalid_json(self):
        with self.assertRaises(FileCreationRejected):
            create_file("json", "bad", "{not json}")

    def test_rejects_unknown_format(self):
        with self.assertRaises(FileCreationRejected):
            create_file("exe", "program", "not allowed")


if __name__ == "__main__":
    unittest.main()
