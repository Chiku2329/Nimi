"""Private, persistent local blob storage for Chainlit elements.

Files live under the app's persistent DATA_DIR volume. Access URLs are short-lived
HMAC-signed URLs; the storage directory is never exposed as a public static path.
"""

import asyncio
import hashlib
import hmac
import mimetypes
import os
import time
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlencode

from chainlit.data.storage_clients.base import BaseStorageClient, storage_expiry_time


MAX_OBJECT_KEY_CHARS = 2048
MAX_FILE_BYTES = 20 * 1024 * 1024
_URL_PREFIX = "/private-storage/"


def _signing_key() -> bytes:
    """Derive a storage-only key without reusing the guest-cookie signing key."""
    secret = (
        os.environ.get("NIMI_STORAGE_SECRET", "").strip()
        or os.environ.get("NIMI_GUEST_SECRET", "").strip()
        or os.environ.get("CHAINLIT_AUTH_SECRET", "").strip()
    )
    if len(secret) < 32:
        raise RuntimeError(
            "Private attachment storage requires NIMI_STORAGE_SECRET, "
            "NIMI_GUEST_SECRET, or CHAINLIT_AUTH_SECRET (at least 32 characters)."
        )
    return hmac.new(
        secret.encode("utf-8"), b"nimi-private-storage-url-v1", hashlib.sha256
    ).digest()


class PrivateLocalStorageClient(BaseStorageClient):
    """Chainlit storage provider backed by the app's persistent local volume."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._key = _signing_key()
        self.expiry_seconds = max(60, int(storage_expiry_time))

    def _safe_path(self, object_key: str) -> Path:
        if (
            not isinstance(object_key, str)
            or not object_key
            or len(object_key) > MAX_OBJECT_KEY_CHARS
            or "\x00" in object_key
            or "\\" in object_key
        ):
            raise ValueError("Invalid storage object key.")

        key = PurePosixPath(object_key)
        if key.is_absolute() or not key.parts or any(
            part in ("", ".", "..") for part in key.parts
        ):
            raise ValueError("Invalid storage object key.")

        path = (self.root / Path(*key.parts)).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise ValueError("Storage object key escapes the storage directory.") from None
        return path

    def _signature(self, object_key: str, expires: int) -> str:
        payload = f"{expires}\n{object_key}".encode("utf-8")
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    async def upload_file(
        self,
        object_key: str,
        data: bytes | str,
        mime: str = "application/octet-stream",
        overwrite: bool = True,
        content_disposition: str | None = None,
    ) -> dict:
        return await asyncio.to_thread(
            self._upload_file_sync, object_key, data, overwrite
        )

    def _upload_file_sync(self, object_key: str, data: bytes | str, overwrite: bool) -> dict:
        path = self._safe_path(object_key)
        payload = data.encode("utf-8") if isinstance(data, str) else data
        if not isinstance(payload, bytes) or len(payload) > MAX_FILE_BYTES:
            raise ValueError("Attachment is invalid or exceeds the storage size limit.")

        path.parent.mkdir(parents=True, exist_ok=True)
        if not overwrite and path.exists():
            return {}

        # Write to a temporary sibling and atomically replace the destination.
        temporary = path.with_name(f".{path.name}.{os.urandom(8).hex()}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if not overwrite and path.exists():
                return {}
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

        # Do not return a public URL. SQLAlchemyDataLayer stores objectKey and
        # asks get_read_url() for a short-lived URL when an owner opens history.
        return {"object_key": object_key}

    async def delete_file(self, object_key: str) -> bool:
        return await asyncio.to_thread(self._delete_file_sync, object_key)

    def _delete_file_sync(self, object_key: str) -> bool:
        path = self._safe_path(object_key)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            return False

        parent = path.parent
        while parent != self.root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        return True

    async def get_read_url(self, object_key: str) -> str:
        # Validate the key before minting a signed URL.
        self._safe_path(object_key)
        expires = int(time.time()) + self.expiry_seconds
        signature = self._signature(object_key, expires)
        encoded_key = quote(object_key, safe="/")
        query = urlencode({"expires": expires, "signature": signature})
        return f"{_URL_PREFIX}{encoded_key}?{query}"

    def resolve_signed_file(self, object_key: str, expires: int, signature: str) -> Path:
        """Verify a read URL and return its file path; raise on any invalid request."""
        if not isinstance(expires, int):
            raise ValueError("Invalid or expired attachment URL.")
        now = int(time.time())
        if expires < now or expires > now + self.expiry_seconds + 60:
            raise ValueError("Invalid or expired attachment URL.")

        expected = self._signature(object_key, expires)
        if not isinstance(signature, str) or not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid or expired attachment URL.")

        path = self._safe_path(object_key)
        if not path.is_file():
            raise FileNotFoundError("Attachment not found.")
        return path

    async def close(self) -> None:
        return None


_STORAGE_CLIENT: PrivateLocalStorageClient | None = None


def get_storage_client(root: str | Path | None = None) -> PrivateLocalStorageClient:
    """Return the process-wide storage client shared by Chainlit and FastAPI."""
    global _STORAGE_CLIENT
    configured_root = (
        Path(root)
        if root is not None
        else Path(os.environ.get("NIMI_STORAGE_DIR") or Path(os.environ.get("DATA_DIR", ".")) / "elements")
    ).expanduser().resolve()

    if _STORAGE_CLIENT is None:
        _STORAGE_CLIENT = PrivateLocalStorageClient(configured_root)
    elif _STORAGE_CLIENT.root != configured_root:
        raise RuntimeError("Nimi storage was initialized with a different directory.")
    return _STORAGE_CLIENT


def attachment_media_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"
