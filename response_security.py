"""Defensive browser response headers for the public Nimi app."""


def build_security_headers(is_https: bool = False) -> dict[str, str]:
    """Return headers that do not interfere with Chainlit's scripts or sockets."""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "frame-ancestors 'self' https://dashboard.blitz.cloud https://*.blitz.cloud https://*.prod.page",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "X-Permitted-Cross-Domain-Policies": "none",
    }
    if is_https:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers
