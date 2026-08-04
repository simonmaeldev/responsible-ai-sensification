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

## Later Candidate Features

Good later steps:

- Session history and replay/export, so live runs become reproducible research
  artifacts.
- Deeper feature detail inspection, including cluster/instrument attribution and
  the strongest feature descriptions behind each token.
- Semantic color/image mapping based on the same lens logic as tonalities.
- Neuronpedia/model loading progress, so performance setup has clearer feedback.

## Verification Pattern

For implementation phases:

- Server behavior: run `uv run pytest` on the PC project environment.
- Browser behavior: run the app on the PC, capture a screenshot from the laptop,
  and stop the server afterward.
- Git hygiene: commit completed feature slices on `nicolas-attempts`; keep
  generated caches, papers, references, runs, and screenshots out of Git unless
  explicitly requested.
