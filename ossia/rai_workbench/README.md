# RAI Workbench for ossia score

Phase 4 provides a compact score-native research and patching interface for the
existing Gemma, Gemma Scope SAE, and Neuronpedia backend. The custom QML UI
controls the saved `RAI Workbench` WebSocket device and keeps exact token
history, the real Gemma block map, dense and exact-SAE provenance, bounded probe
summaries, and SAE/Neuronpedia evidence synchronized. Four patchable scalar
observations are available to ordinary score processes without changing their
backend values.

The model chooser also contains a complete official small-model example:
Gemma 3 270M with a separately trained Gemma Scope 2 `resid_post_all` 16k,
L0-small SAE at every layer 0–17. With **Move matching SAE** enabled, selecting
a block moves the dense observation and its matching pretrained SAE for the
next token. The existing 1B choice keeps its fixed trained SAE behavior.

Raw vectors stay in the local WebSocket payload and are not expanded into the
score address tree. The completed Phase 5 investigation found no current reason
to replace the verified backend with native ONNX/Avendish inference. Its exact
evidence and reopen gates are in
`specs/ossia-native-inference-decision.md`. External connector changes remain
out of scope.

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

Choose a model, enter a prompt and maximum token count, and press **Run prompt**. The UI
shows connection/loading/error state, selectable exact-token history, all real
Gemma blocks, a selectable dense observation layer, the exact fixed or matching
SAE attachment, eight bounded probe-control/summary slots, and twelve strongest
active SAE rows. Provenance includes the exact model, token, site, layer, module
path, shape, dtype, and representation. Block position, dense coordinate, and
SAE feature index are not presented as semantic distance. In the 270M example,
feature indices remain specific to the exact layer/family/width/L0/revision;
the interface does not claim that an index follows one concept across layers.

## Patchable Scalar Contract

The selection is deliberately fixed and small. For each token, the adapter uses
the first non-SAE probe and first SAE probe in backend event order:

| score value address | Existing backend field |
| --- | --- |
| `RAI Workbench:/patchable/tensor_rms/value` | tensor probe `summary.rms` |
| `RAI Workbench:/patchable/tensor_max_abs/value` | tensor probe `summary.max_abs` |
| `RAI Workbench:/patchable/sae_active_count/value` | SAE probe `summary.active_count` |
| `RAI Workbench:/patchable/sae_top_activation/value` | SAE probe `summary.top_activation` |

Each scalar subtree also carries `valid`, metric/probe/source-slot fields and
the exact model, token index/ID/text, site, layer, module path, shape, dtype, and
representation provenance. The SAE top-activation row preserves its literal
`feature_index`; that index is an identifier, not semantic geometry. Consumers
should gate on `valid` and `/token/revision`. The adapter writes the whole
scalar/provenance transaction before the revision marker, so history snapshots
remain synchronized.

The numeric `value` is copied directly from the backend token event. There is no
normalization, range mapping, inferred meaning, or feedback into the observation.
Raw vectors and complete sparse SAE data remain in the local WebSocket payload.

## Removable Example Mapping

The saved document contains one ordinary built-in `Float` process named
`EXAMPLE_patchable_tensor_rms_delete_safe`. Its input is patched to
`RAI Workbench:/patchable/tensor_rms/value`; starting a run starts score's
transport, so the process receives each raw RMS scalar. The example has no
artistic label or transformation and is not read by the adapter or interface.

In `--ui-debug`, select the clearly labelled process and press Delete to remove
it. Save the document if the removal should persist. Deleting or disabling the
example leaves all four observation subtrees, provenance, history, and run
controls intact.

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

The Slice 4 checks exercise two synchronized tokens, exact scalar delivery into
the normal `Float` process, historical selection, and live dense-layer and probe
changes on token two:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_smoke.py
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_smoke.py --debug
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_smoke.py --without-example
```

The removal run requires every observation and history assertion to keep
passing while the example inlet remains unbound. Installed-score harnesses use
score's temporary Dummy audio backend, leaving user audio settings untouched.

The real Slice 4 smoke test starts and stops its own FastAPI process, requests
two Gemma/SAE GPU tokens through the custom interface, and compares each scalar
with the unchanged probe field from the browser WebSocket contract. It also
requires exact provenance, live L22-to-L7 movement, fixed SAE evidence, and the
normal process inlet to equal the latest tensor RMS:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_research_interface_real_smoke.py
```

The real all-layer acceptance uses the official cached 270M model and three
matching SAEs on consecutive tokens (layers 0, 8, and 17), checking exact
browser-WebSocket provenance, synchronized history, unchanged patchable values,
and the ordinary Float process:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_all_layer_real_smoke.py
```

Files under `tests/` are automated score harnesses, not product interfaces.

## libossia / OSCQuery interoperability

`RAI Workbench` is the exact local WebSocket research device. It remains
separate from the optional discoverable `RAI Emitter` OSCQuery device, whose
fixed `/rai/probes/1..8` tree carries only selected bounded summaries. Either,
both, or neither can be present in a score document; inference and the browser
do not depend on the OSCQuery sidecar.

Verify that installed score can connect to the real C++ libossia server and
observe a live scalar update:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/run_oscquery_client_smoke.py
```

Create the deterministic 1440×900 Slice 4 evidence image at
`runs/ossia-score-slice4.png`:

```bash
UV_CACHE_DIR=/tmp/rai-uv-cache uv run python \
  ossia/rai_workbench/tests/capture_interface.py
```

See [the integration guide](../../docs/OSSIA_SCORE_LIBOSSIA_INTEGRATION.md) for
the complete topology, Device Explorer steps, screenshots, and contract
boundaries.
