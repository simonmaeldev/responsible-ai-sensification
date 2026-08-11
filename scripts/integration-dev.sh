#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${RAI_BASE_URL:-http://127.0.0.1:8080}"

if command -v uv >/dev/null 2>&1; then
    PYTHON_RUNNER=(uv run python)
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_RUNNER=("$ROOT_DIR/.venv/bin/python")
else
    PYTHON_RUNNER=(python3)
fi

usage() {
    cat <<'EOF'
Usage: ./scripts/integration-dev.sh COMMAND [ARGS]

Commands:
  serve                         Start the app
  replay [ms] [loop]            Replay passive activation fixtures
  stop                          Stop fixture replay
  status                        Show observer/replay status
  osc-fixture [host] [port]     Send the established /rai/v1 OSC fixture
  listen PORT                   Print OSC messages while a receiver is closed
  check                         Run observer and starter-asset checks
EOF
}

cd "$ROOT_DIR"

case "${1:-}" in
    serve)
        exec ./scripts/start.sh
        ;;
    replay)
        interval_ms="${2:-250}"
        loop="${3:-false}"
        curl -fsS -X POST "$BASE_URL/api/integrations/replay" \
            -H 'Content-Type: application/json' \
            -d "{\"interval_ms\":${interval_ms},\"loop\":${loop}}"
        printf '\n'
        ;;
    stop)
        curl -fsS -X POST "$BASE_URL/api/integrations/replay/stop"
        printf '\n'
        ;;
    status)
        curl -fsS "$BASE_URL/api/integrations/status"
        printf '\n'
        ;;
    osc-fixture)
        host="${2:-127.0.0.1}"
        port="${3:-9000}"
        exec "${PYTHON_RUNNER[@]}" -m scripts.send_osc_test \
            --host "$host" --port "$port"
        ;;
    listen)
        port="${2:-}"
        if [[ -z "$port" || "$port" == *[!0-9]* ]]; then
            usage
            exit 2
        fi
        exec "${PYTHON_RUNNER[@]}" scripts/osc-monitor.py --port "$port"
        ;;
    check)
        "${PYTHON_RUNNER[@]}" -m pytest \
            app/server/tests/test_external_output.py \
            app/server/tests/test_stream_osc_integration.py
        python3 -m py_compile integrations/touchdesigner/websocket_callbacks.py
        echo "Passive observer contract and TouchDesigner callback are valid."
        ;;
    *)
        usage
        exit 2
        ;;
esac
