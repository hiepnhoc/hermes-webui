"""Regression coverage for Vietnamese Edge TTS voices.

The backend must permit the two native vi-VN voices and the Settings UI must
make them selectable so voice mode can use Vietnamese speech end to end.
"""
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.routes as routes


ROOT = Path(__file__).resolve().parents[1]
VIETNAMESE_VOICES = [
    "vi-VN-HoaiMyNeural",
    "vi-VN-NamMinhNeural",
]


class _FakeHandler:
    def __init__(self, body: bytes, client="10.88.0.1"):
        self.command = "POST"
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.headers = {"Content-Length": str(len(body))}
        self.client_address = (client, 12345)
        self.status = None
        self.sent_headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        pass

    def payload(self):
        try:
            return json.loads(self.wfile.getvalue().decode("utf-8"))
        except Exception:
            return None


@pytest.fixture(autouse=True)
def _fresh_tts_limiter(monkeypatch):
    import api.auth as auth

    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    monkeypatch.delenv("HERMES_WEBUI_TRUST_FORWARDED_FOR", raising=False)
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter
    yield
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter


@pytest.mark.parametrize("voice", VIETNAMESE_VOICES)
def test_vietnamese_voice_reaches_edge_synthesis(monkeypatch, voice):
    captured = {}

    class FakeCommunicate:
        def __init__(self, text, selected_voice, **kwargs):
            captured.update(text=text, voice=selected_voice, kwargs=kwargs)

        def stream_sync(self):
            yield {"type": "audio", "data": b"vietnamese-audio"}

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=FakeCommunicate))
    body = json.dumps({"text": "Xin chào", "voice": voice, "engine": "edge"}).encode()
    client = f"10.88.0.{VIETNAMESE_VOICES.index(voice) + 1}"
    handler = _FakeHandler(body, client=client)

    routes._handle_tts(handler, None)

    assert handler.status == 200, handler.payload()
    assert captured["voice"] == voice


def test_vietnamese_voices_are_selectable_in_settings_ui():
    panels = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
    for voice in VIETNAMESE_VOICES:
        assert voice in panels
