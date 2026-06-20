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

## Phase 5: Next Candidate Features

Status: open

Good next steps:

- Session history and replay/export, so live runs become reproducible research
  artifacts.
- Deeper feature detail inspection, including cluster/instrument attribution and
  the strongest feature descriptions behind each token.
- Semantic color/image mapping based on the same lens logic as tonalities.
- Neuronpedia/model loading progress, so performance setup has clearer feedback.
- OSC/MIDI or DAW output, if the priority becomes live performance with external
  audio gear.

## Verification Pattern

For implementation phases:

- Server behavior: run `uv run pytest` on the PC project environment.
- Browser behavior: run the app on the PC, capture a screenshot from the laptop,
  and stop the server afterward.
- Git hygiene: commit completed feature slices on `nicolas-attempts`; keep
  generated caches, papers, references, runs, and screenshots out of Git unless
  explicitly requested.
