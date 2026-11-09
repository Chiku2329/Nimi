"""FastAPI entry point that silently provisions private guest sessions."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from chainlit.server import _authenticate_user
from chainlit.user import User
from chainlit.utils import mount_chainlit

from chainlit_hardening import apply_chainlit_session_guard
from response_security import build_security_headers

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
        response = RedirectResponse(url="/guest-auth", status_code=303)
    else:
        response = await call_next(request)

    # Add defensive browser headers to normal responses and redirects alike.
    response.headers.update(build_security_headers(is_https=request.url.scheme == "https"))
    return response


@app.get("/favicon", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
async def nimi_favicon():
    # Chainlit does not expose a favicon setting in config.toml. Serve Nimi's
    # own infinity mark at the conventional browser favicon URLs instead.
    icon_path = Path(__file__).resolve().parent / "public" / "nimi-infinity.svg"
    return FileResponse(
        icon_path,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache, max-age=0"},
    )


@app.get("/favicon.png", include_in_schema=False)
async def nimi_favicon_png():
    icon_path = Path(__file__).resolve().parent / "public" / "icon-192.png"
    return FileResponse(
        icon_path,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, max-age=0"},
    )


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
