# RAI Workbench for ossia score

Phase 2 provides a minimal score-native interface for the existing Gemma,
Gemma Scope SAE, and Neuronpedia backend. The custom QML UI controls the saved
`RAI Workbench` WebSocket device and shows exact token and feature evidence.

The model block map, token history, probe editor, raw vectors, native inference,
and external connector changes belong to later phases and are not included.

## Requirements

- Ubuntu GPU PC with this repository and its model dependencies installed;
- ossia score 3.8.2 available as `ossia-score`;
- the FastAPI emitter listening at `ws://127.0.0.1:8080/ws/stream`.

## Launch

Start the emitter without opening the browser:

```bash
./scripts/start.sh --no-browser
```

During development, keep score's normal patch and Device Explorer visible:

```bash
ossia-score --ui-debug ossia/rai_workbench/interface.qml ossia/rai_workbench/rai-workbench.score
```

For the normal custom-interface view:

```bash
ossia-score --ui ossia/rai_workbench/interface.qml ossia/rai_workbench/rai-workbench.score
```

Enter a prompt, choose a maximum token count, and press **Run prompt**. The UI
shows connection/loading/error state, the exact JSON-quoted token and token ID,
and twelve strongest active SAE rows. Each row shows the literal feature index,
raw activation to six decimal places, and the available Neuronpedia description.

The backend owns one shared session. Use score or the browser as the run
controller, not both simultaneously.

## Rebuild The Saved Device

`websocket-adapter.js` is the canonical adapter logic. score stores the device
QML as text inside the `.score` document, so rebuild both artifacts after an
adapter change:

```bash
node ossia/rai_workbench/build-websocket-device.js
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/build-score-document.py
```

The second command uses installed score in `--ui-debug` mode to replace the
device in the committed score-generated seed document and save it through
score's document API.

## Verification

Static adapter, interface, and embedded-document contracts:

```bash
node ossia/rai_workbench/tests/test_websocket_adapter.js
node ossia/rai_workbench/tests/test_interface.js
```

Deterministic installed-score checks in normal and development UI modes:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_interface_smoke.py
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_interface_smoke.py --debug
```

The real smoke test starts and stops its own FastAPI process, requests one
Gemma token through the custom interface, and requires loading, running, done,
exact token/ID, raw SAE activation, and Neuronpedia evidence:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_interface_real_smoke.py
```

Files under `tests/` are automated score harnesses, not product interfaces.
