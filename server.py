"""FastAPI entry point that silently provisions private guest sessions."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from chainlit.server import _authenticate_user
from chainlit.user import User
from chainlit.utils import mount_chainlit

from chainlit_hardening import apply_chainlit_session_guard

from guest_auth import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    guest_identifier_from_cookie,
    make_guest_cookie,
)

# CVE-2026-86099 mitigation: validate client-supplied session ids before
# Chainlit can use them as filesystem directory names.
apply_chainlit_session_guard()

app = FastAPI()


@app.middleware("http")
async def send_login_page_to_guest_auth(request: Request, call_next):
    # Chainlit redirects unauthenticated visitors to /login. Send browser
    # navigations through the silent guest bootstrap instead of showing a form.
    if request.url.path.rstrip("/") == "/login" and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/guest-auth", status_code=303)
    response = await call_next(request)
    # Baseline browser protections; HTTPS termination is handled by Blitz.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    if request.url.path == "/guest-auth":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/guest-auth")
async def guest_auth(request: Request):
    cookie_header = request.headers.get("cookie", "")
    identifier = guest_identifier_from_cookie(cookie_header)
    new_cookie = None
    if identifier is None:
        new_cookie = make_guest_cookie()
        identifier = guest_identifier_from_cookie(f"{COOKIE_NAME}={new_cookie}")
    if identifier is None:
        # Fail closed; never fall back to a shared anonymous identity.
        return JSONResponse(
            {"error": "Guest authentication is unavailable. Please contact the site owner."},
            status_code=503,
        )

    response = await _authenticate_user(
        request,
        User(identifier=identifier, metadata={"role": "guest", "provider": "nimi"}),
        redirect_to_callback=True,
    )
    if new_cookie:
        response.set_cookie(
            key=COOKIE_NAME,
            value=new_cookie,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
    return response


mount_chainlit(app=app, target="app.py", path="/")
