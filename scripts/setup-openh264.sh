#!/usr/bin/env bash
# Source this file before building the extension on Linux or macOS.
openh264_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.native/openh264-2.6.0"
(
    set -euo pipefail
    archive="$openh264_root/source.tar.gz"
    source_dir="$openh264_root/openh264-2.6.0"
    prefix="$openh264_root/install"
    if [ ! -f "$source_dir/Makefile" ]; then
        mkdir -p "$openh264_root"
        curl --fail --location --retry 3 \
            https://github.com/cisco/openh264/archive/refs/tags/v2.6.0.tar.gz \
            --output "$archive"
        printf '%s  %s\n' \
            558544ad358283a7ab2930d69a9ceddf913f4a51ee9bf1bfb9e377322af81a69 \
            "$archive" | shasum -a 256 --check
        tar -xzf "$archive" -C "$openh264_root"
    fi
    make_options=("PREFIX=$prefix")
    if [ "$(uname -s)" = Darwin ]; then
        make_options+=("STATIC_LDFLAGS=-lc++")
        export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-11.0}"
    fi
    # Keep platform dependencies from upstream; regenerate pkg-config on reuse.
    make -C "$source_dir" -j "$(getconf _NPROCESSORS_ONLN)" \
        "${make_options[@]}" install-static
)
openh264_status=$?
if [ "$openh264_status" -ne 0 ]; then
    return "$openh264_status"
fi
export PKG_CONFIG_PATH="$openh264_root/install/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
if [ -n "${GITHUB_ENV:-}" ]; then
    printf 'PKG_CONFIG_PATH=%s\n' "$PKG_CONFIG_PATH" >> "$GITHUB_ENV"
fi
unset openh264_root openh264_status
