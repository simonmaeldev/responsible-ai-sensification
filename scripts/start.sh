#!/usr/bin/env bash
LOG_LEVEL="info"
for arg in "$@"; do
    if [ "$arg" = "--verbose" ] || [ "${VERBOSE:-0}" = "1" ]; then
        LOG_LEVEL="debug"
        export VERBOSE=1
    fi
    if [ "$arg" = "--reset-cache" ]; then
        echo "Resetting enriched cluster cache..."
        rm -f neuronpedia_cache/*_enriched.json
        echo "Done."
    fi
done
PYTHONPATH=. uv run uvicorn app.server.main:app \
    --host 0.0.0.0 --port 8080 --log-level "$LOG_LEVEL"
