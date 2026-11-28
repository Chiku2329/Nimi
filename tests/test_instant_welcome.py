from pathlib import Path


def test_chat_start_sends_welcome_before_settings_handshake():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(
        encoding="utf-8"
    )
    start = source.index("@cl.on_chat_start")
    end = source.index("@cl.on_chat_resume", start)
    handler = source[start:end]
    welcome_send = handler.index(").send()")
    settings_setup = handler.index("await setup_settings()")
    assert welcome_send < settings_setup
    assert 'cl.user_session.set("settings", normalize_settings({}))' in handler
