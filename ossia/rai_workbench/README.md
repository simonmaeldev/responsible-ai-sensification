# RAI Workbench for ossia score

Phase 3 provides a compact score-native research interface for the existing
Gemma, Gemma Scope SAE, and Neuronpedia backend. The custom QML UI controls the
saved `RAI Workbench` WebSocket device and keeps exact token history, the real
Gemma block map, dense and fixed-SAE provenance, bounded probe summaries, and
SAE/Neuronpedia evidence synchronized.

Raw vectors stay in the local WebSocket payload and are not expanded into the
score address tree. Native inference and external connector changes belong to
later phases and are not included.

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
shows connection/loading/error state, selectable exact-token history, all real
Gemma blocks, a selectable dense observation layer, the visibly fixed SAE
attachment, eight bounded probe-control/summary slots, and twelve strongest
active SAE rows. Provenance includes the exact model, token, site, layer, module
path, shape, dtype, and representation. Block position, dense coordinate, and
SAE feature index are not presented as semantic distance.

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

The Slice 3 checks exercise two synchronized tokens, select historical evidence,
and require live dense-layer and probe changes on token two:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_smoke.py
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_smoke.py --debug
```

The real Slice 3 smoke test starts and stops its own FastAPI process, requests
two Gemma tokens through the custom interface, and compares score's exact
provenance and SAE/Neuronpedia evidence with the browser WebSocket contract:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_real_smoke.py
```

Files under `tests/` are automated score harnesses, not product interfaces.
