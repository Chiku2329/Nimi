"""Signed, browser-bound guest identity for public Nimi access."""

import hashlib
import hmac
import os
import secrets
import time
from http.cookies import SimpleCookie

COOKIE_NAME = "nimi_guest"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _secret() -> bytes:
    guest_secret = os.environ.get("NIMI_GUEST_SECRET", "").strip()
    auth_secret = os.environ.get("CHAINLIT_AUTH_SECRET", "").strip()
    value = guest_secret or auth_secret
    if len(value) < 32:
        raise RuntimeError(
            "Set NIMI_GUEST_SECRET or CHAINLIT_AUTH_SECRET to a random secret "
            "of at least 32 characters before starting Nimi."
        )
    if guest_secret:
        return guest_secret.encode("utf-8")
    # Derive a separate key so guest-cookie signatures do not reuse the JWT key.
    return hmac.new(
        auth_secret.encode("utf-8"), b"nimi-guest-cookie-v1", hashlib.sha256
    ).digest()


def _sign(token: str) -> str:
    return hmac.new(_secret(), token.encode("ascii"), hashlib.sha256).hexdigest()


def make_guest_cookie() -> str:
    token = str(int(time.time())) + "." + secrets.token_urlsafe(32)
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
        token, separator, signature = morsel.value.rpartition(".")
        if not separator or not token or not signature:
            return None
        issued_text, timestamp_separator, random_part = token.partition(".")
        if not timestamp_separator or not random_part:
            return None
        issued_at = int(issued_text)
        now = int(time.time())
        if issued_at > now + 300 or now - issued_at > COOKIE_MAX_AGE:
            return None
        expected = _sign(token)
        if not hmac.compare_digest(signature, expected):
            return None
        return "guest_" + hashlib.sha256(token.encode("ascii")).hexdigest()
    except (ValueError, UnicodeError):
        return None
