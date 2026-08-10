#!/usr/bin/env bash
LOG_LEVEL="info"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
EMITTER_URL="${EMITTER_URL:-http://127.0.0.1:8080}"

for arg in "$@"; do
    if [ "$arg" = "--verbose" ] || [ "${VERBOSE:-0}" = "1" ]; then
        LOG_LEVEL="debug"
        export VERBOSE=1
    fi
    if [ "$arg" = "--no-browser" ]; then
        OPEN_BROWSER=0
    fi
    if [ "$arg" = "--browser" ]; then
        OPEN_BROWSER=1
    fi
    if [ "$arg" = "--reset-cache" ]; then
        echo "Resetting enriched cluster cache..."
        rm -f neuronpedia_cache/*_enriched.json
        echo "Done."
    fi
done

open_browser_when_ready() {
    if [ "$OPEN_BROWSER" != "1" ]; then
        echo "Browser auto-open disabled (--no-browser)."
        return
    fi
    if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
        echo "No desktop display detected; open $EMITTER_URL manually."
        return
    fi
    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is unavailable; open $EMITTER_URL manually."
        return
    fi

    local browser_command=""
    if command -v xdg-open >/dev/null 2>&1; then
        browser_command="xdg-open"
    elif command -v gio >/dev/null 2>&1; then
        browser_command="gio open"
    else
        echo "No desktop browser launcher found; open $EMITTER_URL manually."
        return
    fi

    local server_pid="$$"
    (
        for _attempt in $(seq 1 80); do
            if curl --silent --fail --output /dev/null "$EMITTER_URL"; then
                echo "Opening Emitter in the default browser: $EMITTER_URL"
                if [ "$browser_command" = "xdg-open" ]; then
                    xdg-open "$EMITTER_URL" >/dev/null 2>&1 || true
                else
                    gio open "$EMITTER_URL" >/dev/null 2>&1 || true
                fi
                exit 0
            fi
            if ! kill -0 "$server_pid" >/dev/null 2>&1; then
                exit 0
            fi
            sleep 0.25
        done
        echo "Emitter did not become ready for browser launch; open $EMITTER_URL manually."
    ) &
}

open_browser_when_ready
export PYTHONPATH=.
exec uv run uvicorn app.server.main:app \
    --host 0.0.0.0 --port 8080 --log-level "$LOG_LEVEL"
