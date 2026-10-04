import hashlib
import http.client
import shutil
import subprocess
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


def test_history_fetch_verifies_git_output_and_preserves_cache_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = b"1234567|2026-10-03|One commit\n"
    payload = expected
    source = assets.Manifest(
        repository="owner/repo",
        revision="a" * 40,
        examples={"intro": ("history",)},
        files={
            "history": assets.File(
                path="history/commits.txt",
                history=True,
                sha256=hashlib.sha256(expected).hexdigest(),
            )
        },
    )
    commands: list[tuple[str, ...]] = []

    def run(
        command: tuple[str, ...], *, check: bool, capture_output: bool, timeout: int
    ) -> subprocess.CompletedProcess[bytes]:
        assert check
        assert capture_output
        assert timeout > 0
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(assets, "manifest", lambda: source)
    monkeypatch.setattr(shutil, "which", lambda _: "git")
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("FFRAMES_EXAMPLE_CACHE", str(tmp_path))
    assets.fetch("intro")
    target = assets.files("intro")["history"]
    assert target.read_bytes() == expected
    assert any(
        "--filter=blob:none" in command and source.revision in command for command in commands
    )
    assert commands[-1][-1] == source.revision
    commands.clear()
    assets.fetch("intro")
    assert not commands
    target.write_bytes(b"previous cache")
    payload = b"bad output"
    with pytest.raises(ValueError, match="SHA-256"):
        assets.fetch("intro")
    assert target.read_bytes() == b"previous cache"
    assert list(target.parent.iterdir()) == [target]
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(FileNotFoundError, match="Git is required"):
        assets.fetch("intro")
