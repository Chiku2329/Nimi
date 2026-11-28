from pathlib import Path


def test_composer_has_separate_send_control_and_inset_textarea():
    css = (Path(__file__).resolve().parents[1] / "public" / "nimi-theme.css").read_text(
        encoding="utf-8"
    )
    assert 'form:has(textarea) button[type="submit"]' in css
    assert "flex: 0 0 44px" in css
    assert "box-shadow: none !important" in css
    assert "gap: 10px !important" in css


def test_composer_has_dark_light_and_mobile_styles():
    css = (Path(__file__).resolve().parents[1] / "public" / "nimi-theme.css").read_text(
        encoding="utf-8"
    )
    assert ".dark form:has(textarea)" in css
    assert ".light form:has(textarea)" in css
    assert "@media (max-width: 768px)" in css
