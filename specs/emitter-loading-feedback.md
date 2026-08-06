# Feature: Emitter Loading Feedback

## Machine And Scope

- **Implementation machine:** Ubuntu GPU PC.
- **Role in scope:** Emitter only.
- Preserve browser audio, visualization, WebSocket streaming, OSC output, and
  the Windows Receiver contract.

## Goal

Make the preparation delay before the first generated token understandable.
The existing interface should show structured progress while it prepares the
language model, SAE, Neuronpedia descriptions, feature organization, semantic
tonality, and generation runtime.

## Loading Event Contract

`loading` WebSocket messages carry:

- a stable `stage_key` and human-readable `label`;
- `step`, `total`, and normalized `progress` values;
- `state`: `active`, `complete`, `cached`, or `skipped`;
- a concise `detail` that can name the selected model, scope, cache result, or
  current operation.

The six ordered stages are model, SAE, Neuronpedia, feature organization,
semantic tonality, and generation. Cache hits must be reported honestly.
Neuronpedia feedback must distinguish reading the local cache from downloading
the explanations.

## Browser Behavior

- Starting a run reveals a compact progress panel in the existing Emitter UI.
- The panel shows the current stage, detail, percentage, progress bar, and stage
  badges without opening a second interface.
- The first token dismisses preparation feedback and returns the status area to
  token progress.
- An error keeps a visible failed state; stopping a preparation hides it.
- Legacy free-text `loading` messages remain readable as a defensive fallback.

## Test-Driven Verification

- Add a focused server test for structured stage ordering and progress.
- Extend the browser DOM/behavior harness for the loading panel and message
  handling.
- Run the focused tests, complete server suite, DOM harness, and
  `node --check app/client/main.js`.
- Start the app, capture the loading UI with a deterministic WebSocket event,
  and stop the server.

## Non-Goals

- Byte-level Hugging Face or Neuronpedia download percentages.
- Changes to model loading, caches, generation semantics, OSC, or the Windows
  Receiver.
- A separate setup screen or modal that blocks access to the instrument.

## Completion Record

Completed on the Ubuntu GPU PC on 2026-08-06.

- Added the six-stage structured WebSocket contract and the in-place browser
  progress panel with stage badges, normalized progress, cache/download detail,
  first-token dismissal, stop handling, and visible errors.
- Added focused Python and browser behavior tests before implementation.
- Verified 70 passing server tests, `node --check app/client/main.js`, and the
  109-ID browser DOM/behavior harness.
- Inspected a deterministic 1800×1100 loading-state screenshot. The compact
  panel preserved the established interface layout.
- Ran a real one-token Gemma 3 1B/SAE GPU session with OSC disabled. The
  production WebSocket emitted all six stages from model loading through 100%,
  reported 64,751 Neuronpedia descriptions from local cache, delivered token 1,
  and hid the loading panel.
- Stopped the local server after both visual and real-model verification.
