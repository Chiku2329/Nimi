"""Compatibility guard for Chainlit's client-supplied session identifier.

CVE-2026-86099 affects Chainlit <= 2.12.0. Chainlit uses the session id as a
filesystem directory name. Until Nimi migrates to a maintained, fixed release,
validate ids both when sessions are created and whenever their files directory
is resolved.
"""
import uuid
from pathlib import Path

from chainlit.session import BaseSession


def canonical_session_id(value: object) -> str:
    """Return a canonical UUID or reject the untrusted client value."""
    if not isinstance(value, str) or len(value) != 36:
        raise ConnectionRefusedError("Invalid session identifier.")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise ConnectionRefusedError("Invalid session identifier.") from None
    canonical = str(parsed)
    if canonical != value.lower():
        raise ConnectionRefusedError("Invalid session identifier.")
    return canonical


def apply_chainlit_session_guard() -> None:
    """Validate ids at construction and at the filesystem path boundary."""
    if getattr(BaseSession, "_nimi_session_id_guard", False):
        return

    original_init = BaseSession.__init__

    def guarded_init(self, *args, **kwargs):
        if "id" in kwargs:
            kwargs["id"] = canonical_session_id(kwargs["id"])
        elif args:
            args = (canonical_session_id(args[0]), *args[1:])
        else:
            raise ConnectionRefusedError("Missing session identifier.")
        original_init(self, *args, **kwargs)

    def guarded_files_dir(self):
        from chainlit.config import FILES_DIRECTORY

        session_id = canonical_session_id(getattr(self, "id", None))
        root = Path(FILES_DIRECTORY).resolve()
        candidate = root / session_id
        if candidate.parent != root or candidate.is_symlink():
            raise ConnectionRefusedError("Invalid session file directory.")
        return candidate

    BaseSession.__init__ = guarded_init
    BaseSession.files_dir = property(guarded_files_dir)
    BaseSession._nimi_session_id_guard = True
