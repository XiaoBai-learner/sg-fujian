import io

import pytest

from sgtrace_app.modules.sources.materials.service import validate_upload


def test_validate_upload_accepts_text_and_normalizes_filename():
    metadata = validate_upload("业务/说明.md", "text/markdown", io.BytesIO("户号".encode()), 1024)
    assert metadata.name == "说明.md"
    assert metadata.category == "document"
    assert metadata.size_bytes == len("户号".encode())


def test_validate_upload_rejects_unsupported_or_oversized_content():
    with pytest.raises(ValueError, match="unsupported"):
        validate_upload("bad.exe", "application/octet-stream", io.BytesIO(b"1"), 1024)
    with pytest.raises(ValueError, match="maximum"):
        validate_upload("bad.txt", "text/plain", io.BytesIO(b"12345"), 4)


def test_validate_upload_rejects_invalid_utf8_text():
    with pytest.raises(ValueError, match="UTF-8"):
        validate_upload("bad.txt", "text/plain", io.BytesIO(b"\xff"), 1024)
