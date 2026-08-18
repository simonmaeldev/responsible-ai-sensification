# Feature Backlog

Each item below is a self-contained feature for this branch. The current user
priority takes precedence over the older numeric ordering.

## Completed

- Focused live inspector: one primary screen now keeps the exact current token,
  selectable token history, 26-block measured Gemma grid, selected block, and
  strongest active SAE/Neuronpedia directions visible together. Generated
  tokens no longer depend on colour metadata; setup and experiments are
  secondary.
- Ubuntu desktop launcher: `./scripts/start.sh` waits for the Emitter endpoint
  and opens it in the default browser; `--no-browser` keeps headless starts
  explicit, and launch failures do not stop the server.
- Live waveform: the browser audio graph now connects through a Web Audio API
  `AnalyserNode`, and the new GUI waveform canvas renders
  `getFloatTimeDomainData()` in real time.
- Live performance tonal lenses: editable verbal tonality descriptions and
  intervals can be changed from the GUI before or during generation; raw versus
  interpreted pitch blend is exposed; token payloads include run-level tonality
  memory and active-feature evidence.
- Receiver-independent GPU emitter instrument: 18 raw/normalized model, SAE,
  Neuronpedia-coverage, cluster, semantic, pitch, and generation signals can be
  mapped live to 14 bounded browser audio/visual targets. Includes templates,
  signal/control monitoring, feature search/pin/mute/solo, saved scenes, A/B
  morphing, and visible verbal-lens re-embedding status.
- General Emitter Signal Explorer: 27 discoverable raw/derived entries across
  selected-layer residuals, output logits, SAE/Neuronpedia, semantic proofs of
  concept, pitch, and generation. Live selection, opt-in high-bandwidth streams,
  route visibility, and a compact visual-mapping disclosure are implemented.
- Emitter loading feedback: six structured preparation stages now report model,
  SAE, Neuronpedia cache/download, feature organization, semantic tonality, and
  first-token generation progress in the existing GUI.
- Focused Gemma Emitter workbench: prompt-first **Model** and **Map** views;
  truthful clickable 26-block Gemma anatomy; independent live
  dense residual observation; simultaneous 1,152-coordinate residual and 65k
  sparse SAE inspection; and real root-key/scale/custom-interval editing. Run
  controls and Tonality are mutually exclusive on-demand drawers; dense/sparse
  representations and the mapping matrix are closed disclosures. The model
  map distinguishes real local/global attention, measured per-token residual
  change, the movable dense probe, and fixed layer-22 SAE while keeping full
  dense capture at only the selected block. OSC is a compact optional output,
  not a primary workspace. Verified with a layer-7 dense probe and layer-22 SAE.
- Gemma Probe Rack + ossia Connector: an on-demand eight-slot rack captures real
  residual, attention-output, MLP-output, and fixed-layer SAE observations with
  live module/layer provenance and optional local vectors. Selected bounded
  summaries publish through a discoverable, read-only libossia OSCQuery `/rai`
  namespace; `/rai/v1`, browser audio/visuals, and the Windows receiver remain
  unchanged. Verified with 99 tests, browser checks, mDNS/OSCQuery loopback, and
  a real six-token GPU run whose attention probe moved live from L1 to L3.
- Ossia score interface Phase 1: a self-contained score 3.8.2 WebSocket device
  controls the existing FastAPI Gemma/SAE runtime and exposes a fixed tree for
  connection/loading/run state, exact tokens, layer provenance, eight probes,
  and twelve strongest SAE/Neuronpedia features. Deterministic start/stop and a
  real one-token GPU run passed through installed score; all 105 server tests
  pass.
- Ossia score interface Phase 2: a minimal custom QML interface and
  score-generated document provide prompt/run controls, connection and loading
  feedback, exact token/ID, and twelve raw SAE/Neuronpedia evidence rows.
  Deterministic `--ui`/`--ui-debug`, visual, and real one-token GPU checks pass.
- Ossia score interface Phase 3: the compact QML research view provides
  synchronized selectable token history, the real 26-block Gemma map, an
  independently selectable dense layer, fixed layer-22 SAE provenance, eight
  bounded probe controls/summaries, and exact model/token/site/module/shape/
  representation evidence. Deterministic normal/debug and real two-token GPU
  runs prove L22-to-L7 live changes while the SAE stays fixed; all 106 server
  tests and the unchanged browser harness pass.
- Ossia score interface Phase 4: four deliberately selected tensor/SAE scalar
  observations are patchable by ordinary score processes with unchanged values
  and complete provenance. One labelled built-in `Float` input patch is
  removable without affecting observation delivery, synchronized history, or
  live controls. Deterministic normal/debug/removal checks and a real two-token
  GPU run pass; raw vectors, full sparse data, inference, and external connector
  contracts remain unchanged.
- Ossia score interface Phase 5: inspected installed and current score/ONNX/
  Avendish capabilities, exact cached Gemma/SAE requirements, the host GPU
  runtime, and a real backend reference. The documented decision is no-go for a
  native port now: retain the verified FastAPI/PyTorch backend and score
  WebSocket device. No code, build, dependency, model, or connector change was
  made; future native work requires a new approved spec after explicit parity
  gates are met.

## Current priority: researcher-facing observation workflows

- Use Model to compare dense residual state across transformer blocks while
  keeping the layer-22 SAE provenance visible.
- Use Map to compare raw residual/logit/SAE data with derived signals and
  Neuronpedia descriptions. Raw residual and sparse streams are enabled locally
  by the workbench but remain outside OSC v1.
- With the researchers, specify one actual Interpreto adapter: supported model,
  split point, inference/dataset/checkpoint source, method, and provenance.
- Evaluate the implemented bounded libossia/OSCQuery namespace in ossia score.
  Add metrics only from a concrete workflow; do not force full dense arrays
  into OSC.
- Keep Tonality and other transformation experiments removable and evaluate
  them only when they answer a concrete research or artistic question.

## Established connector/receiver path: Ableton OSC bridge

- **Ubuntu GPU PC (complete):** optional, live-configurable `/rai/v1` OSC
  emission is implemented and verified against a local UDP receiver.
- **Windows laptop (in progress):** the Max-generated `.amxd`, receiver panel,
  Live-hosted UDP/OSCQuery path, and complete local loopback fixture are verified;
  the deliberate audible/meter check remains because Live's audio engine was off.
- **Integration (transport verified):** the model-free fixture and a real
  three-token Gemma/SAE/post-tonality run were received over the LAN and
  confirmed through Windows OSCQuery. A deliberate audible/meter pass and live
  UI lens/blend listening test remain.
- Do not treat Git worktrees as a cross-computer synchronization mechanism.

## Passive external observation tooling

- `/ws/activations` mirrors complete sparse SAE feature events to passive
  observers without giving them control of generation.
- Deterministic NDJSON replay and TouchDesigner callbacks support receiver work
  without loading Gemma or the SAE.
- The observer feed is separate from the established `/rai/v1` OSC contract.
  It does not add a second OSC namespace, broadcast destination, or inbound
  shared-control bus.

## 1. Host application smoke tests
- Validate passive fixture replay and a live run inside TouchDesigner.
- Save a first project-specific `.toe` or `.tox` once the visual mapping is chosen.
- Use the existing Max-generated receiver for Ableton `/rai/v1` checks; do not
  replace it with a second starter patch.
- Validate selected `/rai/v1` addresses in ossia score before saving a first
  project-specific scenario or proposing OSCQuery discovery.
- See `specs/external-integration-dev-workflow.md`.

## 2. Image generation placeholder → actual image
The bottom-right panel is currently a static placeholder.
- Generate an image that encodes the SAE feature activations visually (e.g. scatter plot of active features by cluster, heatmap of activations over tokens, or a t-SNE/UMAP projection).
- Could also call an external image generation API conditioned on the generated text.
- Decide approach when implementing.

## 2. Session history & replay
- Save each completed run (prompt + all token events) to `runs/` as NDJSON.
- Add a "History" panel in the UI to list past runs and replay them without re-running the model.
- Reuse the existing `export.py` / `runs/` convention.

## 3. Instrument attribution per cluster
- in a scroll box, display for each cluster:
  - the number of the cluster
  - which sound pack it plays (not clear how to do that at all, must be defined but the idea is to select which instrument is playing what is represented by this cluster)
  - the names of the features that were activated that are part of this cluster (to get a sense of what it represents)
