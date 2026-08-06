# Feature: General Emitter Signal Explorer

## Machine And Role Contract

- **Implementation machine:** Ubuntu GPU PC.
- **Role in scope:** Emitter only. The existing browser is the Emitter GUI.
- **Out of scope:** Windows Receiver changes and a libossia/OSCQuery Connector.

The current Gemma 3, Gemma Scope, SAE, Neuronpedia, semantic-tonality, audio,
and visual work remains available as a proof of concept. It must not define a
closed list of future probes or require raw data to receive an artistic meaning
inside the Emitter.

## Goal

Extend the existing professional browser interface with a Signal Explorer that
shows which data sources the Emitter knows about, which ones are selected for
live observation, and where selected data currently goes. Artists and
researchers must be able to activate or deactivate supported signals without
restarting the server or replacing the current instrument.

## Signal Catalogue

Add a generic registry whose entries describe a signal without coupling the
registry to one model family or artistic mapping. Each entry has:

- stable key and human-readable label;
- source family and observation location;
- raw or derived classification;
- scalar, vector, sparse-vector, event, or structured value type;
- optional unit and description;
- whether the signal is enabled by default;
- whether it can be used by the scalar mapping matrix;
- bandwidth/cost guidance for opt-in raw streams.

The existing 18 scalar mapping signals become registered entries. Their keys,
values, defaults, and mapping behavior remain compatible.

## First Observation Sites

The first general slice must expose representative values from more than the
existing semantic-tonality experiment:

- selected decoder-layer residual stream: lightweight scalar summaries plus an
  opt-in raw vector;
- model output logits: lightweight confidence summaries plus an opt-in top-k
  structured stream;
- SAE output: the existing scalar summaries plus an opt-in sparse active-feature
  stream with indices, activations, and available descriptions.

Raw vectors are disabled by default. Selecting them is an explicit local
performance/research choice; no raw tensor is automatically sent through OSC.

## Live Selection

- The session stores a validated list of selected signal keys.
- Browser changes update that list through the existing WebSocket parameter
  flow and affect subsequent tokens without a server restart.
- Signals needed by an enabled mapping may still be computed internally even
  when hidden from the live monitor, so selection changes do not silently break
  the existing instrument.
- Unknown keys are ignored safely.

## Existing-GUI Workflow

Add a **Signals** tab to the current left control panel. Do not create a second
application or redesign the established transport, tonality, mapping, and
connector tabs.

The Signals tab contains:

1. **Available:** searchable, grouped catalogue entries with raw/derived, value
   type, location, and cost information.
2. **Active:** live checkboxes and an honest selected count.
3. **Destinations:** per-signal status for local monitoring, scalar mappings,
   and external connectors. Connector status is descriptive only in this phase;
   selecting a signal must not change the OSC v1 contract.

The right-side Emitter inspector previews selected scalar and structured
signals. It continues to show mapped controls and SAE feature evidence.

## Visual Proof Of Concept

The cluster/color visualization remains functional but is not the dominant
workspace. Place it behind a compact, closed-by-default disclosure labelled as
a visual-mapping proof of concept. Opening it reveals the existing visualization
without changing its data or mappings.

## Non-Goals

- Do not build a visual editor for arbitrary PyTorch hooks in this slice.
- Do not capture every layer or emit full tensors continuously by default.
- Do not implement libossia, OSCQuery, or extend `/rai/v1`.
- Do not change the Windows Max for Live/ossia Receiver.
- Do not remove the current tonality, audio, visual, scene, feature-browser,
  WebSocket, or OSC behavior.

## Test-Driven Verification

- Begin with failing tests for catalogue metadata, unique keys, selection
  coercion, raw-stream opt-in behavior, model-probe summaries, and compatibility
  of the existing 18 mapping sources.
- Begin browser work with failing DOM/behavior assertions for the Signals tab,
  dynamic catalogue rendering, live selection payload, route summaries, and the
  closed visual disclosure.
- Run focused tests after each slice, then the complete server suite.
- Run the browser DOM harness and `node --check app/client/main.js`.
- Start the application locally, inspect the GUI at desktop width, save a
  screenshot for verification outside tracked source, and stop the server.

## Acceptance Criteria

- The established interface gains an in-place Signal Explorer.
- All existing 18 scalar signals are registered and remain mapping-compatible.
- Residual, logits, and SAE observation sites are represented by working live
  signals or opt-in raw streams.
- Live selection affects subsequent browser payloads without restarting.
- Raw high-bandwidth data is disabled by default and never added to OSC v1.
- Existing browser audio, tonality, visualization, mappings, WebSocket flow,
  scenes, and optional OSC output remain functional.
- The visual/color proof of concept is closed by default and appears on demand.

## Completion Record

Completed on the Ubuntu GPU PC on 2026-08-06.

- All 26 registered signals and the three first observation sites are
  implemented.
- Live per-token selection, opt-in raw streams, mapping dependency preservation,
  and the in-place GUI are covered by focused tests.
- The complete server suite passes with 68 tests.
- `node --check app/client/main.js` and the 104-ID browser DOM/behavior harness
  pass.
- The application starts and stops locally. Screenshot capture was attempted but
  was unavailable because this host has no functioning Firefox, Chromium, or
  Playwright browser installation; the server was stopped afterward.
- OSC v1 and the Windows Receiver were not expanded.
