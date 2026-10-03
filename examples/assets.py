"""Fetch pinned upstream assets explicitly; rendering only reads the local cache."""

import argparse
import hashlib
import http.client
import os
import sys
import tomllib
from functools import cache
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import Annotated, Self
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class File(BaseModel):
    """One immutable upstream file with an integrity check."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @field_validator("path")
    @classmethod
    def check_path(cls, value: str) -> str:
        """Keep remote and cached paths relative and portable."""
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or path.as_posix() != value
            or ".." in path.parts
            or any(char in value for char in "\\:\0")
        ):
            msg = "asset path must be a normalized relative POSIX path"
            raise ValueError(msg)
        return value

    def matches(self, path: Path) -> bool:
        """Check cached bytes before returning or reusing an asset."""
        if not path.is_file():
            return False
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest() == self.sha256


class Manifest(BaseModel):
    """The sole source of upstream revision, asset paths and example dependencies."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    repository: Annotated[str, Field(pattern=r"^[\w.-]+/[\w.-]+$")]
    revision: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    files: dict[str, File]
    examples: dict[str, tuple[str, ...]]

    @model_validator(mode="after")
    def check_references(self) -> Self:
        """Reject missing asset names before any network operation."""
        if any(name not in self.files for names in self.examples.values() for name in names):
            msg = "example refers to an unknown asset"
            raise ValueError(msg)
        return self


@cache
def manifest() -> Manifest:
    """Load metadata once without touching the network."""
    return Manifest.model_validate(
        tomllib.loads(Path(__file__).with_name("upstream.toml").read_text(encoding="utf-8"))
    )


def cache_root() -> Path:
    """Use the operating system's user cache, independently of the checkout."""
    if custom := os.environ.get("FFRAMES_EXAMPLE_CACHE"):
        return Path(custom)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "fframes-py/examples"


def files(example: str) -> dict[str, Path]:
    """Resolve verified local assets; tell the caller how to fetch missing files."""
    source = manifest()
    result = {
        name: cache_root() / source.revision / source.files[name].path
        for name in source.examples[example]
    }
    for name, path in result.items():
        if not source.files[name].matches(path):
            msg = f"Missing or modified asset {name}; run python -m examples.assets {example}"
            raise FileNotFoundError(msg)
    return result


def fetch(example: str) -> None:
    """Download just one example's dependencies, verifying bytes before replacement."""
    source = manifest()
    for name in source.examples[example]:
        asset = source.files[name]
        destination = cache_root() / source.revision / asset.path
        if asset.matches(destination):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        connection = http.client.HTTPSConnection("raw.githubusercontent.com", timeout=30)
        temporary: Path | None = None
        try:
            url = quote(f"/{source.repository}/{source.revision}/{asset.path}", safe="/")
            connection.request("GET", url)
            response = connection.getresponse()
            if response.status != 200:
                msg = f"Asset download failed: HTTP {response.status} for {asset.path}"
                raise OSError(msg)
            with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
                while chunk := response.read(65536):
                    stream.write(chunk)
            if not asset.matches(temporary):
                msg = f"SHA-256 mismatch for {asset.path}"
                raise ValueError(msg)
            temporary.replace(destination)
        finally:
            connection.close()
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class Arguments(argparse.Namespace):
    """Typed command-line options for asset preparation."""

    example: str


def main() -> None:
    """Download a named example's assets into the shared user cache."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", choices=tuple(manifest().examples))
    arguments = parser.parse_args(namespace=Arguments())
    fetch(arguments.example)


if __name__ == "__main__":
    main()
