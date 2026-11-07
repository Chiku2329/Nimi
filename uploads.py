"""Strict server-side validation for files uploaded to public Nimi."""
import io
from pathlib import Path

from pypdf import PdfReader

MAX_UPLOAD_COUNT = 3
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 15 * 1024 * 1024
MAX_TEXT_BYTES = 1 * 1024 * 1024
MAX_PDF_PAGES = 25
MAX_FILE_CHARS = 30_000
MAX_TOTAL_TEXT_CHARS = 30_000

_ALLOWED = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".csv": {"text/csv", "text/plain"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}


class UploadRejected(ValueError):
    """An upload failed Nimi's server-side safety checks."""


def _read_upload(element):
    name = Path(str(getattr(element, "name", ""))).name
    suffix = Path(name).suffix.lower()
    mime = str(getattr(element, "mime", "") or "").split(";", 1)[0].strip().lower()
    path_value = getattr(element, "path", None)

    if suffix not in _ALLOWED or mime not in _ALLOWED[suffix]:
        raise UploadRejected("A file type is not supported.")
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
        raise UploadRejected("A file is empty or exceeds the 10 MB limit.")

    if suffix == ".pdf":
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
            text = "\n".join(extracted)[:MAX_FILE_CHARS]
        except UploadRejected:
            raise
        except Exception:
            raise UploadRejected("A PDF file could not be safely processed.") from None
        return {"name": name, "kind": "text", "mime": mime, "data": data, "text": text}

    if suffix in {".txt", ".md", ".csv"}:
        if len(data) > MAX_TEXT_BYTES:
            raise UploadRejected("Text files are limited to 1 MB.")
        if b"\x00" in data:
            raise UploadRejected("A text file contains invalid binary data.")
        try:
            text = data.decode("utf-8", errors="strict")[:MAX_FILE_CHARS]
        except UnicodeDecodeError:
            raise UploadRejected("Text files must use UTF-8 encoding.") from None
        return {"name": name, "kind": "text", "mime": mime, "data": data, "text": text}

    signatures = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not signatures.get(suffix, False):
        raise UploadRejected("An image file failed content validation.")
    return {"name": name, "kind": "image", "mime": mime, "data": data, "text": ""}


def validate_upload_batch(elements):
    """Validate count, each file, and aggregate request size before processing."""
    elements = list(elements or [])
    if len(elements) > MAX_UPLOAD_COUNT:
        raise UploadRejected("You can attach up to five files at a time.")

    validated = [_read_upload(element) for element in elements]
    if sum(len(item["data"]) for item in validated) > MAX_TOTAL_BYTES:
        raise UploadRejected("The combined upload size exceeds 15 MB.")
    if sum(len(item["data"]) for item in validated if item["kind"] == "image") > 10 * 1024 * 1024:
        raise UploadRejected("Combined images are limited to 10 MB per message.")
    if sum(len(item["text"]) for item in validated) > MAX_TOTAL_TEXT_CHARS:
        raise UploadRejected("Combined extracted text is limited to 30,000 characters per message.")
    return validated
