# RAI Workbench for ossia score

Phase 1 provides a score-native WebSocket device for the existing Gemma,
Gemma Scope SAE, and Neuronpedia backend. It exposes a fixed, patchable address
tree inside score and can start or stop a run. It does not yet include the
custom product interface planned for Phase 2.

## Requirements

- Ubuntu GPU PC with this repository and its model dependencies installed;
- ossia score 3.8.2 available as `ossia-score`;
- the FastAPI emitter listening at `ws://127.0.0.1:8080/ws/stream`.

## Build And Check The Device

`websocket-adapter.js` is the canonical adapter logic. The build script embeds
it into a self-contained QML device because score stores the QML text without a
sibling-file base URL.

```bash
node ossia/rai_workbench/build-websocket-device.js
node ossia/rai_workbench/tests/test_websocket_adapter.js
```

The test checks the event translations, fixed tree, bounded feature/probe
slots, outbound commands, and exact synchronization of the generated QML.

## Load The Device In score

1. Start the emitter without opening its browser:

   ```bash
   ./scripts/start.sh --no-browser
   ```

2. In score's Device Explorer, add a **WebSocket** device named
   `RAI Workbench`.
3. Paste the complete contents of `websocket-device.qml` into the device's QML
   code editor. Set its address to `ws://127.0.0.1:8080/ws/stream` if score has
   not populated it, validate the device, and add it.
4. Set `/run/prompt` and `/run/max_tokens`, then toggle `/run/start` to begin.
   Toggle `/run/stop` to cancel the active run.

Start and Stop are Boolean toggles rather than pulse parameters. Prompt and
maximum-token values are local parameters read when Start changes. This avoids
score 3.8.2's binary return-frame behavior for request callbacks while still
sending each control action exactly once.

The backend owns one shared session. Use score or the browser as the run
controller, not both simultaneously.

## Verification

The deterministic smoke test starts its own fixture server on an isolated free
loopback port and launches the installed score build headlessly:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_score_smoke.py
```

The real smoke test starts and stops its own FastAPI process, requests one
Gemma token through score, and requires loading, running, done, probe, SAE, and
Neuronpedia evidence:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_score_real_smoke.py
```

`tests/score-smoke-ui.qml` is only an automated score harness. It is not the
custom Phase 2 interface.
