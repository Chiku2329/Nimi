from pathlib import Path


def test_pwa_marks_real_chainlit_composer():
    js = (Path(__file__).resolve().parents[1] / "public" / "pwa.js").read_text(
        encoding="utf-8"
    )
    assert 'getElementById("chat-input")' in js
    assert 'getElementById("submit-button")' in js
    assert 'classList.add("nimi-composer")' in js


def test_css_styles_real_chainlit_composer_and_controls():
    css = (Path(__file__).resolve().parents[1] / "public" / "nimi-theme.css").read_text(
        encoding="utf-8"
    )
    assert ".nimi-composer #chat-input" in css
    assert ".nimi-composer #submit-button" in css
    assert "gap: 12px !important" in css
    assert "min-width: 44px !important" in css
