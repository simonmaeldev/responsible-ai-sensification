# Emitter Live Inspector Simplification

## Machine and scope

- **Machine:** Ubuntu GPU PC.
- **Role:** browser interface for the existing Emitter.
- No model, WebSocket, OSC, libossia, or Windows Receiver contract changes.

## Problem

The current default screen gives more space to navigation, controls, and an
abstract residual-line treatment than to the data changing during generation.
The generated-token transcript is also incorrectly appended inside the colour
visualization path, so tokens can be absent when colour metadata is absent.
Real active SAE directions are available but hidden behind secondary views.

## Required interface

Use one primary live inspection surface:

1. A prominent exact current-token readout and a continuously visible token
   timeline. Every received token appears even when it has no notes, clusters,
   colours, or tonality result. Timeline tokens are selectable for inspection.
2. A compact clickable grid of the real Gemma transformer blocks. Per-block
   measured update strength, local/global attention, the selected residual
   probe, and the fixed SAE attachment remain truthful. Do not use the long
   decorative residual-line composition as the primary representation.
3. An always-visible list of the strongest active SAE feature directions for
   the inspected token. Each row shows literal feature index, exact activation,
   relative strength, and available Neuronpedia description. State clearly
   that feature index is a sparse coordinate and the text is external evidence.
4. The selected block's real operation order and measured profile remain
   compactly visible. Dense coordinates and advanced mappings remain available
   through disclosures or drawers.
5. Keep only Run, Stop, Setup, Tonality, and optional OSC prominent. Existing
   pause/history behavior may be driven by selecting tokens; legacy transport
   controls must not consume primary space.

Existing browser audio, live parameters, signal selection, mapping/scenes,
tonality editing, colour proof of concept, WebSocket behavior, and OSC output
remain operational but secondary.

## Test-first acceptance

- Browser DOM tests reject primary workspace tabs and the long model-path stage.
- Browser DOM tests require the current token, timeline, model-depth grid, and
  live feature-direction list.
- Unit behavior covers activation ordering/relative strength and confirms that
  a token is appended without notes or colour metadata.
- JavaScript syntax, browser harness, and complete server tests pass.
- A real Gemma/SAE run visibly updates the current token, token timeline,
  selected model block, and active feature directions. Inspect a desktop
  screenshot and stop the server afterward.

## Completion record (2026-08-10)

Implemented on the Ubuntu GPU PC. The default page is now a single synchronized
live inspector with no primary tabs or decorative residual-line stage. Tokens
are appended independently of note/colour data and can be selected to restore
their inspection state. The 26 model blocks form a compact clickable grid with
measured update bars. The strongest sparse SAE directions are continuously
visible with literal indices, activations, relative bars, and Neuronpedia
evidence. Existing controls and experiments remain under Setup, Tonality, raw
representation, and OSC disclosures.

Verification passed with all 79 server tests, JavaScript syntax, and the 153-ID
browser behavior harness. A real three-token Gemma/SAE browser run rendered
`↵`, `The`, and `␠moon`; the final token exposed 53 active directions and 12
strongest rows beside all 26 model blocks. Token-history selection restored
token 1, browser errors were zero, and there was no horizontal overflow at
1,440 px. The inspected screenshot is
`runs/emitter-live-inspector-live.png`. Browser and server were stopped.
