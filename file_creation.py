"""Bounded, in-memory creation of common user-requested office files."""
import csv
import io
import json
import re
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches, Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from html import escape

MAX_CREATE_CHARS = 30_000
MAX_CREATED_BYTES = 5 * 1024 * 1024
SUPPORTED_FORMATS = {"docx", "pdf", "xlsx", "pptx", "csv", "txt", "md", "json", "html"}


class FileCreationRejected(ValueError):
    """A requested file could not be safely created."""


def _safe_filename(filename, extension):
    raw = Path(str(filename or "document")).name
    raw = re.sub(r"[^A-Za-z0-9._ -]", "_", raw).strip(" .")
    if not raw:
        raw = "document"
    if raw.lower().endswith("." + extension):
        raw = raw[: -(len(extension) + 1)]
    raw = raw[:100].rstrip(" .") or "document"
    return f"{raw}.{extension}"


def _as_text(content):
    if not isinstance(content, str) or not content.strip():
        raise FileCreationRejected("Please provide non-empty content for the file.")
    if len(content) > MAX_CREATE_CHARS:
        raise FileCreationRejected("File content is limited to 30,000 characters.")
    return content


def create_file(file_format, filename, content):
    """Create a downloadable document without executing or evaluating user content."""
    fmt = str(file_format or "").lower().lstrip(".")
    if fmt not in SUPPORTED_FORMATS:
        raise FileCreationRejected(
            "Supported output formats: DOCX, PDF, XLSX, PPTX, CSV, TXT, MD, JSON and HTML."
        )
    text = _as_text(content)
    output = io.BytesIO()

    try:
        if fmt == "docx":
            doc = Document()
            for block in re.split(r"\n\s*\n", text):
                paragraph = doc.add_paragraph()
                paragraph.add_run(block)
            doc.save(output)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        elif fmt == "pdf":
            styles = getSampleStyleSheet()
            story = []
            for line in text.splitlines():
                if not line.strip():
                    story.append(Spacer(1, 3 * mm))
                else:
                    story.append(Paragraph(escape(line), styles["BodyText"]))
                    story.append(Spacer(1, 2 * mm))
            SimpleDocTemplate(
                output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                topMargin=18 * mm, bottomMargin=18 * mm,
            ).build(story)
            mime = "application/pdf"

        elif fmt == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Nimi Data"
            try:
                rows = list(csv.reader(io.StringIO(text)))
            except csv.Error:
                rows = [[line] for line in text.splitlines()]
            if not rows:
                rows = [[text]]
            for row in rows[:1000]:
                sheet.append([cell[:2000] for cell in row[:50]])
            # Keep untrusted text as text: openpyxl otherwise treats leading "="
            # values as formulas when Excel opens the generated workbook.
            for row in sheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        cell.data_type = "s"
            for column in sheet.columns:
                letter = column[0].column_letter
                max_width = max((len(str(cell.value or "")) for cell in column), default=10)
                sheet.column_dimensions[letter].width = min(max(max_width + 2, 12), 40)
            workbook.save(output)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        elif fmt == "pptx":
            presentation = Presentation()
            chunks = [chunk.strip() for chunk in re.split(r"\n\s*---+\s*\n", text) if chunk.strip()]
            for index, chunk in enumerate(chunks[:50]):
                lines = chunk.splitlines()
                title = lines[0].lstrip("# ").strip()[:120] if lines else f"Slide {index + 1}"
                body = "\n".join(lines[1:]) if len(lines) > 1 else ""
                slide = presentation.slides.add_slide(presentation.slide_layouts[1])
                slide.shapes.title.text = title or f"Slide {index + 1}"
                slide.placeholders[1].text = body[:3000]
            if not presentation.slides:
                slide = presentation.slides.add_slide(presentation.slide_layouts[1])
                slide.shapes.title.text = "Nimi Presentation"
                slide.placeholders[1].text = text[:3000]
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            presentation.save(output)

        elif fmt == "csv":
            # CSV files may be opened directly in spreadsheet software. Prefix
            # formula-like text with an apostrophe to prevent formula injection,
            # while preserving ordinary signed numeric values.
            rows = list(csv.reader(io.StringIO(text), strict=True))
            safe_rows = []
            numeric = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
            for row in rows:
                safe_row = []
                for value in row:
                    candidate = value.lstrip(" \t\r\n")
                    if (
                        candidate.startswith(("=", "+", "-", "@"))
                        and not numeric.fullmatch(candidate)
                    ):
                        value = "'" + value
                    safe_row.append(value)
                safe_rows.append(safe_row)
            csv_output = io.StringIO(newline="")
            csv.writer(csv_output, lineterminator="\n").writerows(safe_rows)
            output.write(csv_output.getvalue().encode("utf-8-sig"))
            mime = "text/csv; charset=utf-8"

        elif fmt == "json":
            parsed = json.loads(text)
            output.write(json.dumps(parsed, ensure_ascii=False, indent=2).encode("utf-8"))
            mime = "application/json"

        elif fmt == "html":
            # HTML is delivered as a file only; it is never rendered by Nimi.
            output.write(text.encode("utf-8"))
            mime = "text/html; charset=utf-8"

        else:
            output.write(text.encode("utf-8"))
            mime = "text/markdown; charset=utf-8" if fmt == "md" else "text/plain; charset=utf-8"

    except FileCreationRejected:
        raise
    except Exception as exc:
        raise FileCreationRejected(f"Nimi could not create a valid {fmt.upper()} file. Check the content and try again.") from None

    data = output.getvalue()
    if not data or len(data) > MAX_CREATED_BYTES:
        raise FileCreationRejected("The generated file is empty or exceeds the 5 MB output limit.")
    return _safe_filename(filename, fmt), mime, data
