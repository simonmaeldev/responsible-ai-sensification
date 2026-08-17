# Ossia Score Interface Prototype

## Machine And Roles

- **Implementation and verification machine:** Ubuntu GPU PC.
- **Inference host:** the existing FastAPI, PyTorch Gemma, Gemma Scope SAE, and
  Neuronpedia pipeline.
- **Interface host:** ossia score, initially the installed 3.8.2 build.
- **Out of scope:** the Windows Ableton/Max receiver and the `/rai/v1` contract.

## Status And Decision

This is the active implementation direction, but no interface code has been
written yet.

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
RAI Workbench:/run/prompt
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

The first interface shows twelve strongest features. Complete sparse sets and
full residual vectors remain in the local WebSocket payload and are not
expanded into thousands of score addresses. A later measured experiment may
use score `List` or `Map` values for selected raw data.

This score device is separate from the existing bounded OSCQuery `RAI Emitter`
device. Do not merge their contracts merely because both are visible in score.

## Proposed Repository Layout

Keep score-owned prototype material together under `ossia/rai_workbench/`:

- `README.md`: launch and manual verification instructions;
- `websocket-device.qml`: JSON-to-address-tree adapter;
- `interface.qml`: custom score UI;
- `rai-workbench.score`: document generated and saved through score;
- small deterministic fixtures or checks needed to test the adapter.

Server files should change only if a failing contract test proves that the
existing WebSocket protocol cannot support the score adapter cleanly.

## Implementation Slices

### Slice 1: WebSocket device vertical path

- Connect score 3.8.2 to `/ws/stream`.
- Translate `ready`, structured loading, one token, done, stopped, and error.
- Send prompt/start/stop through score parameters.
- Verify one short real Gemma/SAE run without a custom UI.

### Slice 2: Minimal custom interface

- Add prompt, Run, Stop, connection/loading state, current token, and twelve
  strongest SAE/Neuronpedia rows.
- Develop with `--ui-debug`; document the final `--ui` launch.
- Keep the normal score patch visible during development.

### Slice 3: Research observation views

- Add the real Gemma block map, independent dense observation layer, fixed SAE
  attachment, token history, and bounded probe summaries.
- Preserve model, token, layer, module path, shape, and representation
  provenance. Do not infer semantic proximity from coordinate or feature index.

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
