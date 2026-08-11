#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPOSITORY_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
LIBOSSIA_PREFIX="${LIBOSSIA_PREFIX:-${HOME}/.local/opt/libossia}"
SOURCE_DIR="$REPOSITORY_DIR/connector/ossia_probe_server"
BUILD_DIR="$REPOSITORY_DIR/build/ossia-probe-server"
RUNTIME_DIR="$BUILD_DIR/runtime"

if [ ! -f "$LIBOSSIA_PREFIX/lib/libossia.so" ] || [ ! -f "$LIBOSSIA_PREFIX/include/ossia-cpp/ossia-cpp98.hpp" ]; then
    echo "libossia library and headers not found under: $LIBOSSIA_PREFIX" >&2
    echo "Set LIBOSSIA_PREFIX to the installed libossia prefix." >&2
    exit 1
fi

mkdir -p "$BUILD_DIR"
if command -v ldconfig >/dev/null 2>&1; then
    AVAHI_CLIENT_LIBRARY="$(ldconfig -p 2>/dev/null | awk '$1 == "libavahi-client.so.3" { print $NF; exit }')"
    if [ -n "$AVAHI_CLIENT_LIBRARY" ] && [ -f "$AVAHI_CLIENT_LIBRARY" ]; then
        mkdir -p "$RUNTIME_DIR"
        ln -sfn "$AVAHI_CLIENT_LIBRARY" "$RUNTIME_DIR/libavahi-client.so"
    fi
fi
"${CXX:-c++}" -std=c++17 -O2 \
    -I "$LIBOSSIA_PREFIX/include" \
    "$SOURCE_DIR/main.cpp" \
    -L "$LIBOSSIA_PREFIX/lib" \
    -Wl,-rpath,"$LIBOSSIA_PREFIX/lib" \
    -lossia -pthread \
    -o "$BUILD_DIR/rai-ossia-probe-server"

"$BUILD_DIR/rai-ossia-probe-server" --version
