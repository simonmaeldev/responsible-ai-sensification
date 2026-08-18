# Roadmap

This is a planning scaffold, not an implementation commitment. It should stay
aligned with `docs/agentic/PROJECT_STATE.md` and `specs/TODO.md`.

## Phase 0: Workflow Setup

Status: complete

- Created root `AGENTS.md`.
- Created durable workflow docs under `docs/agentic/`.
- Kept local old-reference material ignored in `references/`.
- Standardized the active workflow around Codex, not Anthropic/Claude tooling.

## Phase 1: Paper Intake And Interface Direction

Status: complete for current report

- Read `references/Rai_Report.pdf`.
- Extracted implementable ideas from the report:
  - semantic feature clustering and live activation sensification;
  - verbal tonality descriptions embedded in the same space as SAE features;
  - prompt weighting during output;
  - custom intervals and unconventional tuning systems;
  - sound-wave visualization;
  - pause/replay interaction;
  - future image/color mappings.
- Chose the current app direction as a paper-driven live performance interface
  rather than a static explanatory dashboard.

Audit note: the ignored report file was not present in the current clone during
the Phase 9 redesign. The bullets above are historical extracted notes, not a
claim that the source was available or reread in that session.

## Phase 2: Semantic Tonality Foundation

Status: complete

Goal: support local, Anthropic-free verbal tonality matching in the same MiniLM
semantic space as active SAE feature descriptions.

Implemented:

- `app/server/pipeline/semantic_tonality.py`
- `app/server/pipeline/tonality_data/default_tonalities.json`
- Tests for cache building, ranking, active-feature matching, prompt blending,
  interval pitch bias, live lens coercion, run memory, and feature evidence.

## Phase 3: Paper-Driven Browser GUI

Status: complete

Goal: make the report ideas visible in the new browser interface.

Implemented:

- Token-level semantic tonality payloads in the WebSocket stream.
- Prompt blend and pitch pull controls.
- Live semantic tonality panel with ranked matches and intervals.
- Web Audio `AnalyserNode` waveform canvas.
- Anthropic-free local fallback for cluster names.
- Config endpoint for default tonalities.

## Phase 4: Live Performance Tonality Lenses

Status: complete

Goal: let the user shape the instrument live without directly overriding the
model's internal activation dynamics.

Implemented:

- Editable performance lenses in the GUI: name, verbal description, intervals.
- Lens updates can be sent while generation is running and affect subsequent
  token mappings.
- Raw/interpreted pitch blend controls.
- Run-level tonality memory.
- "Why this sound" active-feature evidence panel.

## Phase 5: Ableton Live Bridge

Status: Phase 5A complete; Phase 5B in progress; Phase 5C transport verified

Goal: let UI-edited, post-tonality SAE musical events produced on the Ubuntu GPU
PC affect Ableton Live on the Windows laptop in real time.

### Phase 5A: Ubuntu GPU PC OSC emitter

Status: complete

- Added optional, live-configurable OSC destination, UDP port, and note-cap
  controls to the browser UI using the existing WebSocket/localStorage flow.
- Added the `/rai/v1` lifecycle, live-control, token, final post-tonality note,
  and tonality output with per-run sequence numbers.
- Kept browser/WebSocket token events uncapped and unchanged; OSC errors are
  logged/reported without interrupting generation.
- Verified with focused tests, the complete 48-test server suite, JavaScript
  syntax checking, and a real Ubuntu loopback UDP receiver.

### Phase 5B: Windows Max for Live/ossia receiver

Status: in progress on the Windows laptop

Completed locally:

- Added a focused Windows receiver spec.
- Added textual Max source for native UDP 9000 reception, exhaustive OSC v1
  parsing, run/sequence token-frame grouping, bounded 16-voice preview audio,
  diagnostics, and typed ossia/OSCQuery configuration/status parameters.
- Preserved raw final frequency, activation, feature, cluster, instrument, and
  tonality metadata for later Ableton mappings.
- Added a Windows loopback OSC fixture and deterministic state-engine test.
- Verified textual patches, all 14 contract addresses, live controls, unknown
  and malformed input tolerance, frequency `445.125` at the Max voice-message
  boundary, done/silent/stop behavior, and real UDP traffic into Max Runtime.
- Saved the source through Live's **Edit in Max** workflow as the Max-generated
  `RAI OSC Receiver.amxd`, with its dependencies beside the device.
- Fixed the namespace abstraction boundary and ossia access attributes, then
  added a static regression check for standard inlets/outlets and read-only
  status versus bidirectional config parameters.
- Loaded the device in Ableton and verified the complete Windows loopback fixture
  through its Live-hosted UDP 9000 receiver and OSCQuery endpoint on TCP 5679.
  The published sentinel values include two notes, `445.125` Hz, BPM `96`,
  sustain mode, control changes, and the final `run_stop` release.

Still required before Phase 5B is complete:

- Enable a deliberate Ableton audio output, then hear and meter the bounded
  preview synth. The prior hosted verification ran with Live's audio engine off.
- Phase 5B does not include Ubuntu-to-Windows LAN validation.

### Phase 5C: Two-machine performance integration

Status: in progress; fixture and real-model transport verified

- Added a configurable, model-free Ubuntu LAN fixture backed by the production
  OSC sender, so UDP/firewall reception can be checked before model inference.
- Verified the fixture over the LAN from Ubuntu to the Live-hosted receiver at
  the then-current `192.168.1.208:9000` destination. Windows OSCQuery confirmed
  both frames, bounded notes, live controls, `445.125` Hz, and stop lifecycle.
- Verified a real three-token Gemma/SAE run through semantic tonality and the
  production sender. Windows OSCQuery confirmed sequence 3, a two-note cap,
  final post-tonality frequencies, tonality `luminous resolve`, SAE metadata,
  and clean stop. This proves transport and receiver state handling, not audible
  Ableton output.
- Recheck the Windows destination before each session because DHCP can change
  it. No Windows address is hardcoded and no new firewall rule was required.
- Decide the master clock and quantization policy.
- Enable Ableton audio, hear/meter the bounded preview, and confirm that live UI
  lens/blend changes are audible in Ableton on subsequent tokens.

The focused contract and machine boundaries are in
`specs/ableton-osc-bridge.md`.

## Phase 6: Receiver-Independent Local Mapping Experiments

Status: complete; hands-on artistic evaluation next

Goal: make Gemma Scope, SAE, Neuronpedia, and semantic-tonality mappings exist
locally before exposing more controls through a connector. These experiments
do not define the Emitter as an instrument.

Implemented:

- Formalized Emitter, Connector, and Receiver as portable logical roles.
- Added a canonical per-token emitter payload with 18 raw/normalized source
  signals, bounded control outputs, and per-mapping diagnostics.
- Added a live mapping matrix with curves, threshold, inversion, quantization,
  smoothing, and safe output ranges.
- Added browser targets for gain, pitch, density, duration, timbre, pan, filter,
  resonance, delay, visual energy/hue/motion, and activation-bar scale.
- Added a searchable SAE/Neuronpedia feature browser with pin/mute/solo local
  audition, raw and interpreted frequencies, activation, cluster, and timbre.
- Added mapping templates, local scene save/recall, and A/B morphing.
- Expanded live verbal lenses with enable/disable, duplication, ordering, and
  visible MiniLM embedding status.
- Verified live mapping replacement and verbal-lens re-embedding with real
  cached Gemma/SAE token streams; complete server suite passes with 60 tests.

Next evaluation:

- Play the emitter with external output disabled and identify the most useful
  signal/target combinations.
- Only then specify a versioned Connector extension for the selected mapped
  controls and decide how particular Receivers should consume them.

The focused implementation contract is in `specs/emitter-instrument.md`.

## Phase 7: General Emitter Signal Explorer

Status: complete; hands-on probe evaluation next

Goal: make the Emitter discoverable and extensible beyond the current SAE,
semantic-tonality, audio, and visual proofs of concept without creating a new
application or preassigning artistic meaning to raw model data.

Implemented:

- Added a generic ordered registry with stable keys, source/location, raw versus
  derived classification, value type, unit, cost, default state, description,
  and scalar-mapping capability.
- Preserved all 18 established scalar mapping sources and added five lightweight
  selected-layer residual/output-logit summaries.
- Added opt-in full residual vectors, structured top-k logits, and sparse SAE
  active-feature streams. Server defaults remain lightweight and no raw stream
  is routed through OSC v1; the Phase 9 browser workbench enables residual and
  sparse streams locally on startup for its primary views.
- Added live session selection that is resolved on each generation step and
  updates subsequent browser payloads without restarting.
- Added an in-place Signals tab with Available, Active, and Destinations
  information, search/filtering, live values, and honest `Not routed` Connector
  state.
- Kept the current visual mapping functional while moving it behind a compact,
  closed-by-default proof-of-concept disclosure.
- Verified 68 server tests, JavaScript syntax, a 104-ID DOM/behavior harness,
  live WebSocket selection serialization, and local application start/stop.
  Screenshot capture was unavailable because no functioning headless browser is
  installed on this Ubuntu host.
- Verified a production one-token Gemma 3 1B/SAE GPU payload with five model
  summaries, a `[1152]` residual vector, eight top logits, 52 sparse SAE
  activations, and OSC disabled.

Next evaluation:

- Run real model sessions and compare the residual, logit, and SAE signals as
  research/performance material.
- Add new probe adapters only when a concrete research or artistic question
  requires them; do not build an unrestricted hook editor prematurely.
- Keep large raw data local until a bounded non-OSC transport is deliberately
  selected.

The focused implementation contract is in
`specs/emitter-signal-explorer.md`.

## Phase 8: Emitter Loading Feedback

Status: complete

Goal: make the preparation delay before the first token legible enough for
hands-on use without changing model or transport behavior.

Implemented:

- Replaced free-text-only loading messages with a stable six-stage WebSocket
  contract covering model, SAE, Neuronpedia, feature organization, semantic
  tonality, and generation.
- Added normalized progress, step counts, concise detail, and active, complete,
  cached, and skipped states. Neuronpedia distinguishes local cache reads from
  downloads.
- Added a compact progress panel and stage badges to the existing Emitter status
  area. The first token dismisses it, while preparation errors stay visible.
- Preserved browser audio/visuals, parameter updates, optional OSC, and the
  Windows Receiver contract.
- Verified 70 server tests, JavaScript syntax, the 109-ID DOM/behavior harness,
  a deterministic desktop screenshot, and a real one-token Gemma/SAE GPU run
  whose production WebSocket emitted every stage through 100%.

The focused implementation contract and completion record are in
`specs/emitter-loading-feedback.md`.

## Phase 9: General Emitter Neural Workbench

Status: six vertical slices complete; broader research adapters remain open

Goal: replace the instrument-first information architecture with a general,
truthful workbench for moving through model observation sites and separating raw
state, interpretation, artistic transformation, and routing.

Implemented:

- First separated observation, interpretation, transformation, and routing as
  explicit provenance concepts. The later focused-interface slice retained
  those distinctions without forcing one primary tab per concept.
- Added Gemma architecture metadata, a block-level anatomy navigator, and an
  independent live `observation_layer` for dense residual probes. The loaded SAE
  stays attached to its trained layer and both locations travel with token data.
- Added focusable Structure, Dense state, and Sparse state views. The dense
  field renders real signed residual coordinates and statistics; the sparse
  view renders real feature indices, activations, and available Neuronpedia
  descriptions. Both explicitly reject invented semantic geometry.
- Moved semantic tonality and colour under optional Transform, kept all existing
  browser audio/mapping behavior, and moved OSC/libossia discussion under Route.
- Added real root-key transposition and conventional scale presets to the live
  verbal-lens editor while preserving custom intervals.
- Added an opt-in, vectorized all-block residual profile for the current token.
  It reports residual RMS/peak, adjacent-block update RMS, and cosine similarity
  while retaining the full residual vector only for the selected block.
- Added a runtime-derived Gemma block diagram with the real local/global
  attention pattern, RMSNorm, self-attention, gated MLP, residual path, measured
  activity bars, and direct/previous/next navigation through every block.
- Replaced the crowded stage and nested-atlas navigation with exactly three
  direct workspaces: **Model**, **Signals**, and **Tonality**. The prompt and
  transport remain continuously visible, while OSC is a compact optional output
  popover rather than a primary workspace.
- Added a full-width Gemma residual-path map with every real block clickable and
  the measured layer-update profile drawn as a restrained trace. Dense and
  sparse representations now remain visible together below the selected block.
- Expanded the live tonality workspace so verbal descriptions, roots, scale
  presets, and custom intervals can be edited beside the current match and
  evidence without nested navigation.
- Reduced the primary navigation to **Model** and **Map**. Run/signal controls
  now use a closed-by-default left drawer; Tonality uses a mutually exclusive
  right drawer; OSC remains a compact header popover.
- Put dense/sparse representations and the full mapping matrix behind clear
  closed disclosures. Tonality lenses use an accordion with one editor open,
  keeping every live action without placing eight editors on screen at once.
- Preserved WebSocket events, history, loading feedback, browser audio,
  visualization, mappings, OSC v1, and Windows Receiver behavior.
- Updated the Ubuntu desktop launcher to open the Emitter automatically only
  after the HTTP endpoint is ready, with an explicit `--no-browser` escape hatch
  and non-fatal handling when no graphical launcher is available.
- Replaced the remaining Model/Map dashboard with one live inspector. Exact
  tokens, selectable token history, a compact measured block grid, and strongest
  active SAE directions are now the default view. Setup, mappings, Tonality,
  raw representations, colour, and OSC remain available only when requested.
- Decoupled generated-token history from the colour/cluster experiment and made
  whitespace tokens legible. Timeline selection restores the synchronized token
  evidence, while SAE rows expose literal indices, exact activation, relative
  strength, and Neuronpedia descriptions.
- Verified 77 server tests, JavaScript syntax, the 140-ID browser harness, and
  headless navigation with no browser errors. A real Gemma 3 1B run observed
  layer 7 while the SAE remained at layer 22, reported all 26 layer summaries,
  rendered the selected 1,152-coordinate residual and 54 active SAE features,
  updated live tonality, and produced inspected Model, Signals, and Tonality
  screenshots. The server was stopped afterward.
- Verified the progressive-disclosure correction with the same 77-test server
  suite, JavaScript syntax, the 149-ID browser harness, and headless interaction
  checks. At 1440 px the model map measured 1,376 px wide; drawers were mutually
  exclusive; only one of eight lenses was open; and the mapping rows had zero
  rendered height while closed. A real GPU run again measured all 26 blocks,
  selected layer 7, rendered 1,152 dense coordinates and 54 active SAE features,
  and updated Tonality without a page error. The server was stopped.
- Verified the single-surface live inspector with 79 server tests, JavaScript
  syntax, the 153-ID browser harness, and a real three-token GPU/browser run.
  The final token exposed 53 active SAE directions beside all 26 measured model
  blocks; token-history selection worked, the 1,440 px page did not overflow,
  and the browser reported no errors. The server was stopped.

Not yet implemented:

- Interpreto attribution/concept adapters or training/checkpoint views. Define
  real methods and provenance with the researchers before adding UI.
- Attention-head decomposition, Q/K/V, internal MLP sublayer, gradient,
  optimizer, training-step, dataset, or arbitrary model-family adapters.
- Semantic projections of dense or sparse directions. Coordinate/index views
  are intentionally literal until a justified projection exists.

The cumulative workbench contract is in `specs/emitter-neural-workbench.md`;
the latest single-surface correction is in `specs/emitter-live-inspector.md`.

## Phase 10: Gemma Probe Rack And libossia OSCQuery

Status: complete for the first bounded adapter and namespace

Goal: let a researcher place truthful observation probes at real Gemma hook
points, inspect them beside the current token, and optionally expose bounded
measurements through a discoverable ossia namespace without turning the Emitter
into a predetermined musical instrument.

Implemented:

- Added a validated eight-slot rack for post-block residual, self-attention
  output, MLP output, and the existing fixed-layer Gemma Scope SAE.
- Added scoped PyTorch hooks with actual module paths, layers, shape/dtype,
  token/model provenance, RMS/peak/mean summaries, and optional local vectors.
  SAE observations report active count, activation totals, and the top feature.
- Resolve the rack every generation step and bound the generation queue to one
  pending token so a live browser edit reaches subsequent model forwards.
- Added one on-demand Probes drawer and a restrained always-visible live strip;
  no new permanent workspace or ornamental model visualization was introduced.
- Added an optional repository-owned C++ sidecar using official libossia
  `opp::oscquery_server`, live OSC/OSCQuery port controls, a stable read-only
  `/rai` tree, `_oscjson._tcp` discovery, and failure isolation.
- Kept raw vectors and complete sparse feature sets in the local WebSocket.
  OSCQuery publishes only selected bounded summaries and remains separate from
  the unchanged `/rai/v1` Ableton contract and Windows receiver.
- Verified 99 server tests, the 165-ID browser behavior harness, JavaScript and
  shell syntax, C++ rebuild, real HTTP OSCQuery values, mDNS discovery, port
  collision handling, and a real six-token RTX 4060 Ti run. The live attention
  probe moved from L1 to L3 starting at token 3 without restart.

Deliberate next adapter boundary:

- Add attention-head or Q/K/V probes only one real hook point at a time, with
  explicit tensor meaning and cost tests.
- Define one researcher-backed Interpreto/training adapter before exposing
  gradients, checkpoints, datasets, or training steps.
- Evaluate the existing namespace in ossia score before versioning additional
  metrics. Do not put unbounded dense arrays into OSC/OSCQuery.

The focused contract and exact namespace are in
`specs/gemma-probe-rack-ossia.md`.

## Phase 11: Ossia Score-Native Interface

Status: Slices 1 through 4 complete; Slice 5 remains a decision gate

Goal: make ossia score the visible research interface and patching environment
while initially preserving the verified FastAPI/PyTorch Gemma, Gemma Scope SAE,
and Neuronpedia backend.

Implemented Slices 1 through 4:

- Added a self-contained score 3.8.2 WebSocket device with local prompt and
  maximum-token controls plus toggle-based Start and Stop actions.
- Mapped ready/loading/token/done/stopped/error events into a fixed address
  tree with exact token data, model/layer provenance, eight probe summaries,
  and twelve ordered SAE/Neuronpedia feature rows.
- Added browser-text and score-binary JSON command compatibility to the backend.
- Verified eight adapter tests, all 105 server tests, deterministic installed
  score start/stop behavior, and one real Gemma/SAE/Neuronpedia token through
  score without QML errors.
- Added a minimal custom QML interface and score-generated document with prompt,
  maximum-token, Run, Stop, connection/loading/error state, exact quoted token
  and ID, and twelve raw SAE/Neuronpedia evidence rows.
- Verified static interface/document contracts, normal `--ui` and development
  `--ui-debug` fixture runs, an inspected 1120×760 offscreen capture, and one
  real token through the custom interface without QML/binding diagnostics.
- Added synchronized selectable token history, all 26 real Gemma blocks and
  attention types, measured layer profiles, an independently selectable dense
  observation layer, a visibly fixed layer-22 SAE, and eight bounded
  provenance-bearing probe controls and summaries.
- Preserved exact model/token/site/layer/module/shape/dtype/representation
  fields while keeping raw vectors out of the fixed score tree and explicitly
  rejecting semantic distance claims for coordinates and feature indices.
- Verified nine adapter tests, seven interface tests, all 106 server tests, the
  unchanged 165-element browser harness, deterministic normal/debug score runs,
  a temporary inspected 1440×900 acceptance render, and a real two-token RTX
  4060 Ti run. The real second token moved dense and residual-probe observation
  from L22 to L7 while the 65,536-wide SAE remained attached to L22; historical
  token selection restored the first observation. The temporary capture was
  removed.
- Added four fixed patchable scalar subtrees for unchanged tensor RMS/peak and
  SAE active-count/top-activation values. Each preserves exact model, token,
  site, layer, module, shape, dtype, and representation provenance, plus the
  literal top SAE identifier, before the synchronized token revision.
- Added one clearly labelled, delete-safe built-in `Float` example whose input
  receives tensor RMS. A separate installed-score removal run proves that the
  observation tree, history, and live controls do not depend on the example.
- Verified eleven adapter/device tests, nine interface/document tests, all 111
  server tests, the unchanged 165-reference browser harness, normal/debug
  installed-score runs, and a real two-token RTX 4060 Ti run against the browser
  WebSocket event fields. The real process inlet received the exact token-two
  RMS `87.42140197753906` after the live L22-to-L7 move; raw vectors, complete
  sparse SAE data, inference, and all external connector contracts remain
  unchanged.

Remaining decision gate:

5. Decide in a new focused investigation whether native ONNX/Avendish
   inference is justified. Do not port inference without a new approved spec.

The focused contract is in `specs/ossia-score-interface.md`. The sequential
prompts and advance gates are in `docs/agentic/PROMPTS.md`.

## Later Candidate Features

Good later steps:

- TouchDesigner integration through a raw sparse-activation bridge from the
  FastAPI stream, so SAE feature indices, activations, descriptions, clusters,
  and semantic-tonality context can drive live visuals directly.
- Session history and replay/export, so live runs become reproducible research
  artifacts.
- Deeper feature detail inspection, including cluster/instrument attribution and
  the strongest feature descriptions behind each token.
- Semantic color/image mapping based on the same lens logic as tonalities.
- A researcher-defined Interpreto adapter for one real model/split-point/method
  combination, with provenance and no unsupported live-training claims.
- A versioned extension to the existing libossia/OSCQuery namespace, but only
  after concrete score/receiver use identifies additional bounded metrics.

## External Host Observation Tooling

Status: passive server feed and deterministic fixture foundation complete;
TouchDesigner host smoke test pending

- `/ws/activations` exposes complete sparse feature events to passive external
  observers without making them generation controllers.
- Events retain run, model, selected observation layer, fixed SAE layer/width,
  raw activation, normalized activation, description, cluster, and optional
  semantic-tonality provenance.
- Deterministic NDJSON replay and TouchDesigner callback examples allow host
  work without loading Gemma or the SAE.
- This observer feed does not expand or replace the verified `/rai/v1` OSC
  Connector. The obsolete unversioned top-K sender and generic bidirectional
  bus were deliberately not carried forward.

Remaining:

- Smoke-test fixture and live observation in TouchDesigner, then choose and save
  a first project-specific `.toe` or `.tox` only after its mapping is defined.
- Use the existing Max-generated receiver for Ableton work.
- Specify selected libossia/OSCQuery parameters before adding discovery or
  inbound cross-host controls.

## Verification Pattern

For implementation phases:

- Use test-driven development by default: add or extend a focused behavioral
  test, confirm the intended failure, implement the smallest passing change,
  and refactor while green.
- Server behavior: run the focused test and complete `uv run pytest` suite on
  the PC project environment.
- Browser behavior: run the app on the PC, capture a screenshot from the laptop,
  and stop the server afterward. Add automated DOM/behavior coverage where
  practical and run JavaScript syntax checks.
- Git hygiene: automatically commit each completed, verified feature slice on
  `nicolas-attempts`; never include unrelated user work. Do not push or perform
  branch/history operations unless requested. Keep generated caches, papers,
  references, runs, and screenshots out of Git unless explicitly requested.
