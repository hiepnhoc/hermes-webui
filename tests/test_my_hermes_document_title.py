"""Local branding regression tests for the production WebUI tab title."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
UI_JS = (ROOT / "static" / "ui.js").read_text(encoding="utf-8")
PANELS_JS = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")


def test_session_title_does_not_replace_browser_branding():
    start = UI_JS.index("function syncTopbar(){")
    body = UI_JS[start : start + 5000]
    assert "document.title=assistantDisplayName();" in body
    assert "document.title=sessionTitle+' \\u2014 '+assistantDisplayName();" not in body


def test_panel_title_does_not_replace_browser_branding():
    start = PANELS_JS.index("function syncAppTitlebar()")
    body = PANELS_JS[start : start + 2500]
    assert "document.title = bot || mainText;" in body
    assert "document.title = bot ? mainText + ' \\u2014 ' + bot : mainText;" not in body