"""Signed, browser-bound guest identity for public Nimi access."""

import hashlib
import hmac
import os
import secrets
from http.cookies import SimpleCookie

COOKIE_NAME = "nimi_guest"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _secret() -> bytes:
    value = os.environ.get("NIMI_GUEST_SECRET") or os.environ.get("CHAINLIT_AUTH_SECRET")
    if not value or len(value) < 32:
        raise RuntimeError(
            "Set NIMI_GUEST_SECRET (at least 32 characters) or a strong "
            "CHAINLIT_AUTH_SECRET before starting Nimi."
        )
    return value.encode("utf-8")


def _sign(token: str) -> str:
    return hmac.new(_secret(), token.encode("ascii"), hashlib.sha256).hexdigest()


def make_guest_cookie() -> str:
    token = secrets.token_urlsafe(32)
    return token + "." + _sign(token)


def guest_identifier_from_cookie(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    parsed = SimpleCookie()
    try:
        parsed.load(cookie_header)
        morsel = parsed.get(COOKIE_NAME)
        if morsel is None:
            return None
        token, separator, signature = morsel.value.partition(".")
        if not separator or not token or not signature:
            return None
        expected = _sign(token)
        if not hmac.compare_digest(signature, expected):
            return None
        return "guest_" + hashlib.sha256(token.encode("ascii")).hexdigest()
    except (ValueError, UnicodeError):
        return None
