# Gemma Probe Rack And libossia Connector

## Machine and roles

- **Implementation and verification machine:** Ubuntu GPU PC.
- **Emitter:** the existing FastAPI/Gemma runtime and browser interface.
- **Connector:** an optional libossia OSCQuery device published by the Emitter.
- **Receiver/client for local verification:** ossia score on the same Ubuntu GPU
  PC. No Windows Max for Live Receiver change is part of this slice.

## Goal

Make model observation work like a small neuroscience probe rack. A researcher
can place bounded, named probes at real locations in the loaded Gemma decoder,
see those observations locally for each generated token, and optionally expose
their scalar measurements as a discoverable libossia/OSCQuery namespace.

libossia does not inspect the model. Model-family adapters own hook placement;
the Connector publishes the resulting canonical observations without assigning
them an artistic meaning.

## Probe contract

The first Gemma adapter supports at most eight simultaneous probe slots. Each
slot contains a stable ID, enabled state, site, decoder layer, capture mode, and
bounded-publication choice.

Supported sites are deliberately real and finite:

- `residual_post`: output of the selected Gemma decoder block;
- `attention_output`: output of that block's `self_attn` module;
- `mlp_output`: output of that block's `mlp` module;
- `sae`: the existing Gemma Scope residual SAE, fixed to the layer on which it
  was trained. Its layer cannot be moved by the rack.

Capture mode is either `summary` or `vector`. Summary always reports tensor
shape, RMS, maximum absolute activation, and arithmetic mean. `vector` adds the
real final-token vector to the existing local WebSocket event. Raw vectors are
never published through OSCQuery. SAE observations instead report active count,
maximum and total activation, strongest feature index and activation, plus the
existing local sparse feature data.

Probe selection is validated and read at every generation step. Browser edits
therefore affect the next token without restarting or reloading the model.
Unknown sites, duplicate IDs, out-of-range layers, invalid capture modes, and
more than eight slots are safely coerced.

Every canonical observation identifies the probe ID, model, token position,
site, actual layer, module path, capture mode, shape/dtype, summary, and whether
its bounded values are selected for the Connector.

## Browser workflow

Keep the current single live inspector. Add one real **Probes** action that opens
an on-demand rack instead of adding another permanent dashboard.

The rack must allow the user to:

- add or remove a probe;
- enable or disable it;
- choose residual, attention output, MLP output, or the fixed SAE;
- choose a real decoder block where the site is movable;
- choose summary or local vector capture;
- choose whether bounded summaries are published to ossia;
- see the exact module path and latest measured values.

A compact always-visible active-probe strip links the configured rack to the
current token. It must not displace the token timeline, model grid, or active SAE
directions.

## libossia and OSCQuery contract

Use the installed official libossia C++ library through a small repository-owned
sidecar. Do not reimplement OSCQuery JSON or discovery inside the browser.

The Connector is optional and failure-isolated. It is disabled by default and
has configurable OSC and OSCQuery ports (defaults `9010` and `5678`). Enabling,
disabling, or changing its ports must not restart model generation. Missing
libossia, build/start failure, port collision, broken pipe, or client failure
must produce a concise browser status and never stop generation.

The libossia device exposes a stable read-only tree so clients do not depend on
dynamic node creation:

```text
/rai/model/name
/rai/run/id
/rai/run/token/index
/rai/run/token/text
/rai/probes/1..8/enabled
/rai/probes/1..8/id
/rai/probes/1..8/site
/rai/probes/1..8/layer
/rai/probes/1..8/module_path
/rai/probes/1..8/shape
/rai/probes/1..8/rms
/rai/probes/1..8/max_abs
/rai/probes/1..8/mean
/rai/probes/1..8/active_count
/rai/probes/1..8/top_index
/rai/probes/1..8/top_activation
/rai/probes/1..8/sequence
```

Unused metrics remain at neutral values. A slot's metadata says which metrics
are meaningful. The Connector publishes only enabled observations whose
`publish` flag is true. Full vectors and complete SAE feature sets remain local
to the Emitter WebSocket.

This namespace is additive and separate from the established outbound
`/rai/v1` musical OSC contract. Existing Ableton/Max behavior must not change.

## Test-first verification

1. Start with failing tests for probe coercion, real module resolution,
   residual/attention/MLP hook capture, fixed SAE provenance, vector opt-in, and
   live selection on subsequent tokens.
2. Start Connector work with failing tests for the stable namespace, encoded
   sidecar commands, bounded-only publication, live enable/port changes, and
   failure isolation.
3. Start browser work with failing DOM/behavior tests for the Probes action,
   rack rows, add/remove/edit payloads, SAE layer locking, live values, and
   ossia status.
4. Run focused tests, the complete server suite, the browser harness,
   `node --check app/client/main.js`, shell/C++ build checks, and diff checks.
5. Perform a real cached Gemma/SAE GPU run with residual, attention, MLP, and SAE
   probes. Confirm the local WebSocket provenance and values.
6. Build and start the libossia sidecar, inspect its OSCQuery tree, verify live
   values change, confirm discovery from the local Ubuntu session, and inspect
   the browser alongside ossia score. Stop the Emitter and test sidecar after
   verification; do not stop the user's independently opened ossia score.

## Non-goals

- Arbitrary Python or PyTorch hook code entered through the browser.
- Attention-head decomposition, Q/K/V capture, gradients, training steps,
  optimizer state, or Interpreto claims in this first rack slice.
- Sending unbounded dense arrays through OSC or OSCQuery.
- Replacing the custom Emitter UI with ossia score.
- Changing the Windows Receiver or `/rai/v1` contract.

## Integration verification follow-up

On 2026-08-31, installed ossia score 3.8.2 connected to the real C++ sidecar
through `Score.connectOSCQueryDevice` and read the fixed `/rai` namespace. A
live update changed `/rai/probes/1/rms` from `0.5` to `10.5`; score simultaneously
read the exact 270M model, token 2, residual-post site, layer 17,
`model.layers.17`, shape `640`, and sequence 2. The test-owned score and sidecar
were stopped afterward.

A separate real browser/GPU run exposed the discoverable eight-slot namespace
while moving the matching 270M dense/SAE observation through L0, L8, and L17.
The visible probe rack and model-switch layer normalization were corrected with
focused browser tests. No namespace field or publication boundary changed.
