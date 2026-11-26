"""Safe browser cache policy for public, immutable static assets."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

_PUBLIC_EXTENSIONS = {
    ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2"
}
_HASHED_BUNDLE = re.compile(r"-[0-9a-f]{8,}\.[^.]+$", re.IGNORECASE)


def cache_control_for_asset(path: str, versioned: bool = False) -> str | None:
    """Return cache policy only for public static files; never for app/API data."""
    suffix = PurePosixPath(path).suffix.lower()
    if path.startswith("/public/") and suffix in _PUBLIC_EXTENSIONS:
        return (
            "public, max-age=31536000, immutable"
            if versioned else "public, max-age=300"
        )
    if (
        path.startswith("/assets/")
        and suffix in {".css", ".js", ".svg", ".woff", ".woff2"}
        and _HASHED_BUNDLE.search(PurePosixPath(path).name)
    ):
        return "public, max-age=31536000, immutable"
    return None
