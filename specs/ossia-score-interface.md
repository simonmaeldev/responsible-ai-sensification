# Ossia Score Interface Prototype

## Machine And Roles

- **Implementation and verification machine:** Ubuntu GPU PC.
- **Inference host:** the existing FastAPI, PyTorch Gemma, Gemma Scope SAE, and
  Neuronpedia pipeline.
- **Interface host:** ossia score, initially the installed 3.8.2 build.
- **Out of scope:** the Windows Ableton/Max receiver and the `/rai/v1` contract.

## Status And Decision

Slices 1 through 3 are complete and verified on the Ubuntu GPU PC with installed
ossia score 3.8.2. The fixed WebSocket device and compact custom interface can
control and observe a real Gemma/SAE/Neuronpedia run, preserve synchronized
token history and exact provenance, and apply dense-layer and probe changes to
subsequent tokens. Slice 4, patchable scalar observations, is next.

The first prototype will put the visible research interface and patching
surface inside ossia score while keeping the existing Python inference backend.
It will use score's bidirectional WebSocket device to translate the current
`/ws/stream` JSON protocol into a stable score device tree.

The stock score Language Model process is not the inference path for this
prototype. The installed 3.8.2 process predates current generic Gemma support,
and the current add-on exposes generated text rather than exact token IDs,
internal activations, SAE features, or Neuronpedia evidence.

## Goal

Create a score-native instrument that can:

- enter a prompt and start or stop a run;
- show connection, loading, run, and error state;
- show the exact current token and token ID;
- show the selected Gemma layer and fixed SAE layer distinctly;
- show bounded probe summaries;
- show the strongest active SAE features with activation and Neuronpedia text;
- make selected scalar observations available to normal score processes.

The current browser remains a verified reference interface until the score
prototype reaches feature and evidence parity. Do not remove it during these
slices.

## Initial Architecture

```text
ossia score QML interface
        |
score WebSocket device and address tree
        |
existing FastAPI /ws/stream
        |
PyTorch Gemma + hooks + Gemma Scope SAE + Neuronpedia cache
```

Use the existing WebSocket messages wherever possible:

- score to backend: `start`, `stop`, and `update_params` actions;
- backend to score: `ready`, `loading`, `token`, `done`, `stopped`, status, and
  `error` events.

The server currently owns one shared session. The first prototype therefore
has one active controller: use either score or the browser to start a run, not
both simultaneously. Multi-client broadcasting or session IDs require a later
focused spec.

## Initial Score Device Tree

The WebSocket adapter should expose a fixed tree rather than creating and
destroying nodes during generation:

```text
RAI Workbench:/connection/state
RAI Workbench:/run/state
RAI Workbench:/run/error
RAI Workbench:/run/prompt
RAI Workbench:/run/max_tokens
RAI Workbench:/run/start
RAI Workbench:/run/stop
RAI Workbench:/loading/label
RAI Workbench:/loading/detail
RAI Workbench:/loading/progress
RAI Workbench:/token/index
RAI Workbench:/token/id
RAI Workbench:/token/text
RAI Workbench:/token/elapsed_ms
RAI Workbench:/model/name
RAI Workbench:/observation/layer
RAI Workbench:/observation/sae_layer
RAI Workbench:/probes/1..8/...
RAI Workbench:/features/1..12/index
RAI Workbench:/features/1..12/activation
RAI Workbench:/features/1..12/description
```

The device exposes the twelve strongest features. Complete sparse sets and
full residual vectors remain in the local WebSocket payload and are not
expanded into thousands of score addresses. A later measured experiment may
use score `List` or `Map` values for selected raw data.

`/run/prompt` and `/run/max_tokens` are local score parameters read when
`/run/start` changes. Start and Stop are Boolean toggles rather than pulse
parameters so each action works reliably with score 3.8.2's WebSocket request
callback behavior.

This score device is separate from the existing bounded OSCQuery `RAI Emitter`
device. Do not merge their contracts merely because both are visible in score.

## Repository Layout

Keep score-owned prototype material together under `ossia/rai_workbench/`:

- `README.md`: launch, loading, and verification instructions;
- `websocket-adapter.js`: canonical JSON-to-address-tree logic;
- `websocket-device.template.qml`: score WebSocket device shell;
- `build-websocket-device.js`: embeds the adapter into the self-contained,
  generated `websocket-device.qml`;
- `interface.qml`: minimal score-native run and evidence interface;
- `rai-workbench.score`: score-generated document containing the WebSocket
  device;
- `build-score-document.py`: refreshes the embedded device through score's
  `--ui-debug` document API;
- `tests/`: adapter tests and deterministic/real installed-score smoke
  harnesses.

The QML files under `tests/` are automated harnesses, not product interfaces.

Server files should change only if a failing contract test proves that the
existing WebSocket protocol cannot support the score adapter cleanly.

## Implementation Slices

### Slice 1: WebSocket device vertical path

Status: complete

- Connect score 3.8.2 to `/ws/stream`.
- Translate `ready`, structured loading, one token, done, stopped, and error.
- Send prompt/start/stop through score parameters.
- Verify one short real Gemma/SAE run without a custom UI.

Observed verification:

- eight adapter/tree tests pass, including generated-QML synchronization;
- the backend accepts browser text JSON and score 3.8.2 binary JSON command
  frames, with 105 complete server tests passing;
- the deterministic installed-score smoke test observes loading, running,
  exact token, probe, feature, done, and stop behavior;
- a real one-token installed-score run loaded Gemma 3 1B PT, the layer-22 65k
  SAE, and Neuronpedia evidence, then exposed token `" and"`, feature 14994,
  and its cached description without a QML error.

### Slice 2: Minimal custom interface

Status: complete

- Add prompt, Run, Stop, connection/loading state, current token, and twelve
  strongest SAE/Neuronpedia rows.
- Develop with `--ui-debug`; document the final `--ui` launch.
- Keep the normal score patch visible during development.

Observed verification:

- four static interface/document tests, all eight Phase 1 adapter tests, and all
  105 FastAPI server tests pass;
- the score-generated document contains one `RAI Workbench` WebSocket device
  whose embedded QML exactly matches the generated Phase 1 device;
- deterministic installed-score runs pass in both final `--ui` mode and
  development `--ui-debug` mode with no QML reference, type, assignment, or
  binding-loop diagnostics;
- a real one-token custom-interface run exposed token `" detector"`, token ID
  24772, feature 14994, raw activation 3411.114501953125, and its Neuronpedia
  description;
- an offscreen 1120×760 acceptance capture was inspected after removing an
  unsupported generic monospace override that had hidden numeric/token text.

score 3.8.2 must refresh the saved document in `--ui-debug` mode. Saving from
replacement `--ui` mode writes the JSON but then crashes because the normal
document UI lifecycle is absent; the repository build helper deliberately uses
the verified debug mode and the committed score-generated document as its seed.

### Slice 3: Research observation views

Status: complete

- Add the real Gemma block map, independent dense observation layer, fixed SAE
  attachment, token history, and bounded probe summaries.
- Preserve model, token, layer, module path, shape, and representation
  provenance. Do not infer semantic proximity from coordinate or feature index.

Observed verification:

- nine adapter/device tests and seven interface/document tests pass;
- deterministic installed-score runs pass in normal `--ui` and development
  `--ui-debug` modes, including exact two-token history restoration, all 26
  Gemma blocks, live dense/probe movement from L22 to L7, fixed SAE L22, and
  eight bounded summary slots;
- the full 106-test server suite and unchanged 165-element browser behavior
  harness pass;
- a temporary 1440×900 offscreen acceptance render showed both history entries,
  all 26 blocks without horizontal overflow, distinct L7 dense selection and
  fixed L22 SAE markers, and readable exact historical evidence; it was removed;
- a real RTX 4060 Ti run exposed tokens `"-"` and `"free"`; token two used
  dense and residual-probe path `model.layers.7` after the live edit while the
  SAE remained at `gemma_scope.resid_post.layer_22.width_65k` with exact shape
  `[65536]`; both tokens retained active SAE and Neuronpedia evidence;
- the model-to-interface handoff now waits until the current timed token has
  been forwarded before starting the next model step, making the existing live
  update contract effective for score as well as the browser.

### Slice 4: Patchable observations

- Make selected scalar observations usable by normal score processes.
- Add one small, clearly labelled example mapping without changing the raw
  observations or external connector contracts.

### Slice 5: Native inference decision gate

- After the interface works, evaluate an isolated current/continuous score and
  `score-addon-onnx` build.
- Compare exact Gemma 3 1B PT tokenization, token IDs, hidden-state access, SAE
  parity, cancellation, backpressure, GPU performance, and build cost.
- Do not implement a native inference port until a new focused spec is approved.

## Test-First Verification

For every implementation slice:

1. Define an automated contract check or a written manual acceptance check
   before implementation.
2. For backend behavior, add a failing focused test first and then run the
   complete server suite.
3. Validate QML parsing/loading and inspect score logs for binding or runtime
   errors.
4. Exercise deterministic WebSocket events before using the real model.
5. Run a short real Gemma/SAE session and compare the observed token, probe, and
   SAE evidence with the current browser.
6. Stop the test server after verification, inspect the diff, and create one
   focused commit. Do not push unless requested.

## Non-Goals

- Porting Gemma or the SAE to ONNX in the first four slices.
- Embedding Python or PyTorch inside score.
- Deleting or redesigning the current browser interface.
- Expanding `/rai/v1`, the Windows receiver, or the bounded OSCQuery namespace.
- Sending full dense vectors through OSC or OSCQuery.
- Claiming that Neuronpedia descriptions are raw model state.
