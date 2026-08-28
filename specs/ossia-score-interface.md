# Ossia Score Interface Prototype

## Machine And Roles

- **Implementation and verification machine:** Ubuntu GPU PC.
- **Inference host:** the existing FastAPI, PyTorch Gemma, Gemma Scope SAE, and
  Neuronpedia pipeline.
- **Interface host:** ossia score, initially the installed 3.8.2 build.
- **Out of scope:** the Windows Ableton/Max receiver and the `/rai/v1` contract.

## Status And Decision

Slices 1 through 5 and the all-layer pretrained-SAE example are complete and
verified on the Ubuntu GPU PC with installed
ossia score 3.8.2. The fixed WebSocket device and compact custom interface can
control and observe a real Gemma/SAE/Neuronpedia run, preserve synchronized
token history and exact provenance, and apply dense-layer and probe changes to
subsequent tokens. Four raw scalar summaries are now patchable by ordinary score
processes. Slice 5 concluded that native ONNX/Avendish inference is not justified
now; the verified backend remains the inference path. The evidence and reopen
gates are recorded in `specs/ossia-native-inference-decision.md`.

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
- show the selected Gemma layer and exact trained SAE layer distinctly;
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
RAI Workbench:/run/model
RAI Workbench:/run/sae_width
RAI Workbench:/run/sae_l0
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
RAI Workbench:/observation/requested_sae_layer
RAI Workbench:/observation/sae_layer
RAI Workbench:/observation/sae_width
RAI Workbench:/observation/sae_l0
RAI Workbench:/observation/sae_category
RAI Workbench:/observation/sae_repo_id
RAI Workbench:/observation/sae_revision
RAI Workbench:/probes/1..8/...
RAI Workbench:/patchable/tensor_rms/...
RAI Workbench:/patchable/tensor_max_abs/...
RAI Workbench:/patchable/sae_active_count/...
RAI Workbench:/patchable/sae_top_activation/...
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

Status: complete

The fixed selection is intentionally limited to existing numeric fields from
the first non-SAE probe and first SAE probe in backend token-event order:

| Stable score subtree | Exact backend source |
| --- | --- |
| `/patchable/tensor_rms` | tensor `summary.rms` |
| `/patchable/tensor_max_abs` | tensor `summary.max_abs` |
| `/patchable/sae_active_count` | SAE `summary.active_count` |
| `/patchable/sae_top_activation` | SAE `summary.top_activation` |

Each subtree contains `valid`, the unchanged numeric `value`, metric, probe ID,
source slot, and exact model, token index/ID/text, site, layer, module path,
shape, dtype, and representation provenance. The top-activation subtree also
retains the literal SAE `feature_index`. That index identifies a sparse feature;
it is not interpreted as geometry or distance. The scalar transaction is
delivered before `/token/revision`, preserving synchronized history. Missing
tensor or SAE sources invalidate their corresponding rows rather than reusing
stale provenance.

The committed score document includes one built-in `Float` process named
`EXAMPLE_patchable_tensor_rms_delete_safe`. Only its inlet is addressed, at
`RAI Workbench:/patchable/tensor_rms/value`. It does not write back to the
observation, normalize the value, assign artistic meaning, or supply data to
the interface. `interface.qml` starts the normal score transport when a run is
started, so arbitrary user processes patched to the scalar tree are active.
The labelled example can be deleted or disabled without affecting observation
delivery or any run/history behavior.

Raw dense vectors and complete sparse SAE records stay in the local WebSocket
payload. Slice 4 does not change inference, `/rai/v1`, the bounded OSCQuery
tree, or the Windows receiver.

Observed verification:

- eleven adapter/device tests and nine interface/document tests pass, including
  exact raw-value/provenance delivery, fixed selection, missing-source
  invalidation, no vector/sparse expansion, and exactly one removable example;
- deterministic installed-score runs pass in normal `--ui` and development
  `--ui-debug` modes. Two synchronized tokens preserve values `0.5` and `10.5`,
  move the dense and residual-probe layer from L22 to L7 for token two, restore
  token one's scalar history, and deliver the latest unchanged `10.5` to the
  ordinary `Float` process inlet;
- a separate installed-score run removes the example from a staged document:
  its inlet remains unbound while the complete two-token observations,
  provenance, history, and live changes remain unchanged;
- the full 111-test server suite, unchanged 165-reference browser behavior
  harness, JavaScript syntax, generated-device synchronization, QML/document
  contracts, and earlier installed-score smoke checks pass;
- a real RTX 4060 Ti Gemma/SAE run exposed token-one tensor RMS
  `794.3080444335938`, peak `25728`, SAE active count `61`, and top activation
  `3320.06103515625` with literal feature 14994. Token two moved the tensor
  probe to `model.layers.7` and reported RMS `87.42140197753906`; the normal
  `Float` inlet received that exact value. Every scalar equalled its source
  field in the browser WebSocket event, token-one history restored the original
  value/provenance, and the fixed layer-22 SAE remained unchanged.

### Slice 5: Native inference decision gate

Status: complete — no-go for a native port now

The investigation inspected installed score 3.8.2 plus current score,
score-addon-onnx, and Avendish source. The current add-on can name Gemma-family
decoders, but its process boundary and worker lifecycle do not preserve this
project's exact plain-prompt token IDs, layer-22 residual, Gemma Scope SAE,
Neuronpedia/provenance evidence, cancellation, or one-token live-control
boundary. The installed CUDA provider is also incompatible with the host's
available CUDA libraries, and no exact PT ONNX export or matching score SDK is
present.

The decision is to keep the verified FastAPI/PyTorch backend and existing score
WebSocket device. An Avendish bridge would duplicate that working adapter
without moving inference or supplying a measured benefit. No implementation
was performed, and native work requires a new approved spec after the gates in
`specs/ossia-native-inference-decision.md` are met.

### All-layer pretrained-SAE example extension

Status: complete

This extension is not Slice 6 and does not reopen the native-inference decision.
It adds a complete small-model example to the existing backend/browser/score
path:

- model `google/gemma-3-270m`, with its real 18-block architecture;
- repository `google/gemma-scope-2-270m-pt`;
- `resid_post_all`, width `16k`, target L0 `small`, layers 0–17;
- one exact pretrained SAE runtime per model/repository/family/layer/width/L0
  cache key;
- independent dense and SAE requests, with an optional “Move matching SAE”
  control that applies both selections to the next token;
- token-bound SAE layer, family, width, L0, repository, revision, module path,
  shape, dtype, and representation evidence in browser and score history.

The all-layer series is not the separate four-layer residual series currently
carrying Neuronpedia descriptions. Description and cluster fields therefore
remain empty rather than borrowing semantic evidence. Feature indices are
specific to their exact layer-specific SAE and cannot be followed across depth
as if they represented one concept.

Observed verification on the Ubuntu GPU PC:

- 119 server tests, browser JavaScript/DOM checks, eleven adapter/device tests,
  and ten interface/document tests passed;
- installed score passed normal, debug, synchronized scalar/history, and
  staged example-removal runs;
- official model snapshot `9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1`
  and all 18 official SAE files from snapshot
  `b218cd5d69dc2fa71cff448b68d625e6c9702d49` were cached outside Git;
- a real installed-score RTX 4060 Ti run generated three consecutive tokens at
  L0, L8, and L17. Each event reported its matching 16,384-wide SAE, exact
  snapshot provenance, empty description, synchronized token history, and
  unchanged tensor/SAE scalar values. The ordinary Float example received the
  exact latest tensor RMS;
- the existing real Gemma 3 1B regression retained a movable L22→L7 dense
  observation and fixed layer-22 SAE with exact scalar equality.

The narrower source and acceptance contract is
`specs/gemma-scope-all-layer-example.md`.

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
