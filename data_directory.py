"""Resolve Nimi's persistent data directory without silent data loss.

If DATA_DIR is explicitly configured (for example, Blitz's /data volume), startup
must fail when that directory is unavailable. Falling back to the app directory
can split databases and attachments across ephemeral storage.
"""

import os
import tempfile
from pathlib import Path


def resolve_data_dir() -> str:
    configured = os.environ.get("DATA_DIR")
    requested = configured if configured else "."
    path = Path(requested).expanduser()

    try:
        path.mkdir(parents=True, exist_ok=True)
        descriptor, probe = tempfile.mkstemp(prefix=".nimi-write-check-", dir=path)
        os.close(descriptor)
        os.unlink(probe)
        return str(path.resolve())
    except OSError as error:
        source = "configured DATA_DIR" if configured else "default data directory"
        raise RuntimeError(
            f"Nimi cannot use its {source} ({path}). Refusing to fall back to "
            "ephemeral application storage because that could lose chats, "
            "memories, rate limits, and attachments."
        ) from error
