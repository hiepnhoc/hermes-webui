"""Regression tests for configured upload limits and multipart envelope overhead."""

from io import BytesIO

import api.config as config
from api.upload import parse_multipart


def _multipart_file(data: bytes, *, boundary: bytes = b"upload-limit-boundary") -> tuple[bytes, str]:
    body = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="exact.bin"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        + data
        + b"\r\n--"
        + boundary
        + b"--\r\n"
    )
    return body, f"multipart/form-data; boundary={boundary.decode()}"


def test_file_at_exact_limit_allows_multipart_envelope(monkeypatch):
    """The configured limit applies to file bytes, not multipart metadata."""
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 8)
    body, content_type = _multipart_file(b"12345678")

    _, files = parse_multipart(BytesIO(body), content_type, len(body))

    assert files["file"] == ("exact.bin", b"12345678")
