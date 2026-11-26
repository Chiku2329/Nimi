from pathlib import Path


def test_startup_splash_has_short_fail_open_timeout():
    script = (Path(__file__).resolve().parents[1] / "public" / "pwa.js").read_text(
        encoding="utf-8"
    )
    assert "window.setTimeout(finish, 900)" in script
    assert "window.setTimeout(finish, 8000)" not in script


def test_startup_splash_tracks_visible_app_shell():
    script = (Path(__file__).resolve().parents[1] / "public" / "pwa.js").read_text(
        encoding="utf-8"
    )
    assert 'root.querySelector("main")' in script
    assert "window.ResizeObserver" in script
    assert "window.requestAnimationFrame(check)" in script
