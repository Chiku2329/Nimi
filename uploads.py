"""Safe, bounded extraction for files uploaded to public Nimi.

Supported content is extracted to text for the model, or passed as image input.
Unknown binary formats are rejected rather than blindly sent to a model.
"""
import io
import warnings
import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

MAX_UPLOAD_COUNT = 3
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 15 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_PDF_PAGES = 25
MAX_FILE_CHARS = 30_000
MAX_TOTAL_TEXT_CHARS = 30_000
MAX_IMAGE_PIXELS = 20_000_000
MAX_ARCHIVE_ENTRIES = 1_000
MAX_ARCHIVE_UNCOMPRESSED = 50 * 1024 * 1024
MAX_ARCHIVE_RATIO = 200
MAX_SPREADSHEET_CELLS = 10_000
MAX_SPREADSHEET_ROWS_PER_SHEET = 1_000
MAX_PRESENTATION_SLIDES = 100

_IMAGE_FORMATS = {
    ".png": ("PNG", "image/png"),
    ".jpg": ("JPEG", "image/jpeg"),
    ".jpeg": ("JPEG", "image/jpeg"),
    ".webp": ("WEBP", "image/webp"),
}
_OFFICE_MIMES = {
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
}
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".json", ".jsonl", ".xml", ".yaml", ".yml",
    ".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".py", ".pyw", ".java", ".kt", ".kts", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb", ".sh", ".bash", ".zsh", ".sql",
    ".log", ".ini", ".toml", ".cfg", ".conf", ".properties", ".gradle",
    ".swift", ".r", ".ipynb", ".vue", ".svelte", ".graphql", ".gql",
    ".dockerfile", ".makefile", ".bat", ".ps1", ".diff", ".patch",
}
_TEXT_APPLICATION_MIMES = {
    "application/json", "application/ld+json", "application/xml",
    "application/javascript", "application/x-javascript", "application/x-yaml",
    "application/yaml", "application/x-python-code", "application/sql",
    "application/x-sh", "application/toml",
}


class UploadRejected(ValueError):
    """An upload failed Nimi's server-side safety checks."""


def _read_bytes(element, name):
    path_value = getattr(element, "path", None)
    if not path_value:
        raise UploadRejected("An uploaded file could not be read.")
    path = Path(path_value)
    try:
        if path.is_symlink() or not path.is_file():
            raise UploadRejected("An uploaded file could not be read.")
        with path.open("rb") as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
    except UploadRejected:
        raise
    except OSError:
        raise UploadRejected("An uploaded file could not be read.") from None
    if not data or len(data) > MAX_FILE_BYTES:
        raise UploadRejected(f"{name} is empty or exceeds the 5 MB per-file limit.")
    return data


def _validate_image(data, suffix):
    """Decode supported raster formats and enforce a strict pixel budget."""
    image_format = _IMAGE_FORMATS[suffix][0]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=[image_format]) as image:
                if image.format != image_format:
                    raise UploadRejected("An image file failed content validation.")
                width, height = image.size
                if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                    raise UploadRejected("Images must not exceed 20 million pixels.")
                image.verify()
            with Image.open(io.BytesIO(data), formats=[image_format]) as image:
                image.load()
    except UploadRejected:
        raise
    except Exception:
        raise UploadRejected("An image file could not be safely decoded.") from None


def _validate_office_archive(data, required_part):
    """Reject malformed or suspiciously expansive OOXML ZIP containers."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise UploadRejected("An Office document contains too many internal files.")
            total_size = sum(item.file_size for item in entries)
            if total_size > MAX_ARCHIVE_UNCOMPRESSED:
                raise UploadRejected("An Office document expands beyond the 50 MB safety limit.")
            for item in entries:
                if item.file_size > 0 and item.compress_size == 0:
                    raise UploadRejected("An Office document failed archive validation.")
                if item.compress_size > 0 and item.file_size / item.compress_size > MAX_ARCHIVE_RATIO:
                    raise UploadRejected("An Office document has an unsafe compression ratio.")
            if required_part not in archive.namelist():
                raise UploadRejected("An Office document failed content validation.")
    except UploadRejected:
        raise
    except (zipfile.BadZipFile, OSError, ValueError):
        raise UploadRejected("An Office document could not be safely opened.") from None


def _trimmed_result(name, mime, data, text):
    return {
        "name": name, "kind": "text", "mime": mime, "data": data,
        "text": text[:MAX_FILE_CHARS],
    }


def _extract_docx(name, mime, data):
    _validate_office_archive(data, "word/document.xml")
    try:
        document = Document(io.BytesIO(data))
        parts = []
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text)
        for table_index, table in enumerate(document.tables, 1):
            parts.append(f"Table {table_index}:")
            for row in table.rows:
                parts.append(" | ".join(cell.text.replace("\n", " ").strip() for cell in row.cells))
                if sum(map(len, parts)) >= MAX_FILE_CHARS:
                    break
        return _trimmed_result(name, mime, data, "\n".join(parts))
    except UploadRejected:
        raise
    except Exception:
        raise UploadRejected("The Word document could not be safely processed.") from None


def _extract_xlsx(name, mime, data):
    _validate_office_archive(data, "xl/workbook.xml")
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False)
        parts = []
        cell_count = 0
        try:
            for sheet in workbook.worksheets[:50]:
                parts.append(f"Sheet: {sheet.title}")
                for row_number, row in enumerate(sheet.iter_rows(values_only=True), 1):
                    if row_number > MAX_SPREADSHEET_ROWS_PER_SHEET:
                        parts.append("[Remaining rows omitted by safety limit]")
                        break
                    values = ["" if value is None else str(value) for value in row]
                    cell_count += len(values)
                    if cell_count > MAX_SPREADSHEET_CELLS:
                        parts.append("[Remaining cells omitted by safety limit]")
                        break
                    if any(values):
                        parts.append(" | ".join(values))
                    if sum(map(len, parts)) >= MAX_FILE_CHARS:
                        break
                if cell_count > MAX_SPREADSHEET_CELLS or sum(map(len, parts)) >= MAX_FILE_CHARS:
                    break
        finally:
            workbook.close()
        return _trimmed_result(name, mime, data, "\n".join(parts))
    except UploadRejected:
        raise
    except Exception:
        raise UploadRejected("The Excel workbook could not be safely processed.") from None


def _extract_pptx(name, mime, data):
    _validate_office_archive(data, "ppt/presentation.xml")
    try:
        presentation = Presentation(io.BytesIO(data))
        if len(presentation.slides) > MAX_PRESENTATION_SLIDES:
            raise UploadRejected("PowerPoint files are limited to 100 slides.")
        parts = []
        for index, slide in enumerate(presentation.slides, 1):
            parts.append(f"Slide {index}:")
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    value = shape.text.strip()
                    if value:
                        parts.append(value)
                if getattr(shape, "has_table", False):
                    for row in shape.table.rows:
                        parts.append(" | ".join(cell.text.strip() for cell in row.cells))
                if sum(map(len, parts)) >= MAX_FILE_CHARS:
                    break
            if sum(map(len, parts)) >= MAX_FILE_CHARS:
                break
        return _trimmed_result(name, mime, data, "\n".join(parts))
    except UploadRejected:
        raise
    except Exception:
        raise UploadRejected("The PowerPoint presentation could not be safely processed.") from None


def _read_upload(element):
    name = Path(str(getattr(element, "name", ""))).name
    suffix = Path(name).suffix.lower()
    mime = str(getattr(element, "mime", "") or "").split(";", 1)[0].strip().lower()
    if not name or not suffix:
        raise UploadRejected("This file needs a supported file extension.")

    if suffix in _IMAGE_FORMATS:
        expected_mime = _IMAGE_FORMATS[suffix][1]
        if mime != expected_mime:
            raise UploadRejected(f"{name} has a file type that does not match its contents.")
        data = _read_bytes(element, name)
        _validate_image(data, suffix)
        return {"name": name, "kind": "image", "mime": mime, "data": data, "text": ""}

    if suffix == ".pdf":
        if mime not in {"application/pdf", "application/octet-stream"}:
            raise UploadRejected(f"{name} has a file type that does not match its contents.")
        data = _read_bytes(element, name)
        if b"%PDF-" not in data[:1024]:
            raise UploadRejected("A PDF file failed content validation.")
        try:
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > MAX_PDF_PAGES:
                raise UploadRejected("PDF files are limited to 25 pages.")
            extracted = []
            char_count = 0
            for page in reader.pages:
                if char_count >= MAX_FILE_CHARS:
                    break
                part = page.extract_text() or ""
                remaining = MAX_FILE_CHARS - char_count
                extracted.append(part[:remaining])
                char_count += min(len(part), remaining)
            return _trimmed_result(name, mime, data, "\n".join(extracted))
        except UploadRejected:
            raise
        except Exception:
            raise UploadRejected("A PDF file could not be safely processed.") from None

    if suffix in _OFFICE_MIMES:
        if mime not in _OFFICE_MIMES[suffix]:
            raise UploadRejected(f"{name} has a file type that does not match its contents.")
        data = _read_bytes(element, name)
        if suffix == ".docx":
            return _extract_docx(name, mime, data)
        if suffix == ".xlsx":
            return _extract_xlsx(name, mime, data)
        return _extract_pptx(name, mime, data)

    if suffix in _TEXT_EXTENSIONS:
        if not (mime.startswith("text/") or mime in _TEXT_APPLICATION_MIMES or mime == "application/octet-stream"):
            raise UploadRejected(f"{name} has a file type that does not match its contents.")
        data = _read_bytes(element, name)
        if len(data) > MAX_TEXT_BYTES:
            raise UploadRejected("Text and code files are limited to 2 MB.")
        if b"\x00" in data:
            raise UploadRejected("A text file contains invalid binary data.")
        try:
            text = data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            raise UploadRejected("Text and code files must use UTF-8 encoding.") from None
        return _trimmed_result(name, mime, data, text)

    raise UploadRejected(
        f"{name}: this format is not supported for content analysis yet. "
        "Try PDF, Word, Excel, PowerPoint, an image, or a text/code file."
    )


def validate_upload_batch(elements):
    """Validate count, each file, and aggregate request size before processing."""
    elements = list(elements or [])
    if len(elements) > MAX_UPLOAD_COUNT:
        raise UploadRejected("You can attach up to three files at a time.")

    validated = [_read_upload(element) for element in elements]
    if sum(len(item["data"]) for item in validated) > MAX_TOTAL_BYTES:
        raise UploadRejected("The combined upload size exceeds 15 MB.")
    if sum(len(item["data"]) for item in validated if item["kind"] == "image") > 10 * 1024 * 1024:
        raise UploadRejected("Combined images are limited to 10 MB per message.")
    if sum(len(item["text"]) for item in validated) > MAX_TOTAL_TEXT_CHARS:
        raise UploadRejected("Combined extracted text is limited to 30,000 characters per message.")
    return validated
