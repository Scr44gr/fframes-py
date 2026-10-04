# Releases

[Index](index.md)

## Versioning

Start with **fframes-py 0.1.0**, backed by **fframes 1.2.0**. The wrapper has its
own API, especially `fframes.compose`, so its version does not track the engine's.
`Cargo.toml` owns both versions; Maturin reads the package version from it.

Before 1.0, use patch releases for compatible fixes and minor releases for API
changes. Document breaking changes even during 0.x. Move to 1.0 when the public
Python API is stable. Record upstream upgrades in the release notes.

## Configure PyPI once

Create a GitHub environment named `pypi`, restrict deployment to release tags,
and configure any required reviewers. Then add a
[pending trusted publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
from your PyPI account with:

| Field | Value |
| --- | --- |
| PyPI project | `fframes-py` |
| Repository owner | `Scr44gr` |
| Repository | `fframes-py` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

If the project already exists in your account, add the same publisher under its
Publishing settings. No API token or GitHub secret is needed. A pending publisher
does not reserve the package name.

## Publish

1. Update the package version in `Cargo.toml`, refresh both lockfiles, and commit.
2. Wait for CI to pass on that commit and push the matching tag:

   ```sh
   git tag v0.1.0
   git push origin v0.1.0
   ```

`release.yml` rejects a tag that differs from the package version. It then calls
the existing CI workflow: one stable-ABI wheel per platform, one source archive,
and installed-wheel tests on Python 3.11–3.14. Only after all checks pass does
`uv publish --trusted-publishing always` upload those exact distributions.

Maturin repairs native dependencies and rejects wheel tags PyPI cannot accept.
Linux's minimum glibc version is encoded in its `manylinux` wheel tag; an older
distribution needs a source build. The current runner matrix covers Linux and
Windows x86-64 and macOS arm64. Other architectures need separate builds.

Creating this configuration does not publish anything. Publishing starts only
when a matching `v*` tag is pushed and the `pypi` environment permits deployment.
