import hashlib
import http.client
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError

from examples import assets


@pytest.mark.parametrize("path", ["../escape", "/root/file", "C:/font.ttf", "x\\y", "a/../b"])
def test_manifest_cannot_escape_the_cache(path: str) -> None:
    with pytest.raises(ValidationError, match="relative POSIX"):
        assets.File(path=path, sha256="0" * 64)


def test_fetch_verifies_reuses_and_atomically_replaces_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"verified upstream file"
    source = assets.Manifest(
        repository="owner/repo",
        revision="a" * 40,
        files={
            "font": assets.File(path="media/font.ttf", sha256=hashlib.sha256(payload).hexdigest())
        },
        examples={"scene": ("font",)},
    )
    requests: list[str] = []

    class Response(BytesIO):
        status = 200

    class Connection:
        def __init__(self, host: str, timeout: int) -> None:
            assert (host, timeout) == ("raw.githubusercontent.com", 30)

        def request(self, method: str, url: str) -> None:
            assert method == "GET"
            requests.append(url)

        def getresponse(self) -> Response:
            return Response(payload)

        def close(self) -> None:
            pass

    monkeypatch.setattr(assets, "manifest", lambda: source)
    monkeypatch.setenv("FFRAMES_EXAMPLE_CACHE", str(tmp_path))
    monkeypatch.setattr(http.client, "HTTPSConnection", Connection)
    with pytest.raises(FileNotFoundError, match=r"examples\.assets scene"):
        assets.files("scene")
    assets.fetch("scene")
    destination = assets.files("scene")["font"]
    assert destination.read_bytes() == payload
    assets.fetch("scene")
    assert requests == [f"/owner/repo/{source.revision}/media/font.ttf"]
    destination.write_bytes(b"old file")
    payload = b"corrupted transfer"
    with pytest.raises(ValueError, match="SHA-256"):
        assets.fetch("scene")
    assert destination.read_bytes() == b"old file"
    assert list(destination.parent.iterdir()) == [destination]


def test_manifest_rejects_unknown_assets() -> None:
    with pytest.raises(ValidationError, match="unknown asset"):
        assets.Manifest(
            repository="owner/repo", revision="a" * 40, files={}, examples={"scene": ("absent",)}
        )
