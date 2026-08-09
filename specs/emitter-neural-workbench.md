# Emitter Neural Workbench

## Status

Implemented specification for the August 2026 interface correction.

## Purpose

The Ubuntu application is a general Emitter workbench for observing and
interpreting model activity. It is not inherently a musical instrument. Sound,
semantic tonality, colour, OSC, and external receivers are optional experiments
or destinations built from model observations.

The implementation must keep four epistemic distinctions truthful in its
labels and provenance, but the third slice supersedes the requirement that each
distinction occupy a primary workspace:

1. **Observe** — model, prompt, token, layer, and raw model/SAE values.
2. **Interpret** — feature descriptions, Neuronpedia evidence, projections, and
   future attribution/concept methods such as Interpreto.
3. **Transform** — optional artistic mappings including semantic tonality,
   browser sound, colour, and user-defined experiments.
4. **Route** — optional transport to another context. OSC is the current
   connector; libossia/OSCQuery is the planned discoverable parameter layer.

## Required first slice

### Prompt and run context

- The prompt composer is the primary interaction, not a narrow utility field.
- The current model, token, observed layer, SAE attachment layer, dense width,
  and sparse width remain visible while inspecting a run.
- Playback and existing browser audio continue to work.

### Independent observation layer

- `layer` continues to mean the layer of the loaded Gemma Scope SAE.
- `observation_layer` selects the transformer block whose residual stream is
  exposed through model residual probes.
- The SAE must continue to encode the residual from its own attachment layer.
- A live `observation_layer` update affects subsequent tokens without restarting.
- Events identify the actual observed layer and SAE layer. Invalid layer values
  are clamped safely instead of terminating generation.

### Truthful model views

- **Architecture** shows the actual model block count and marks both the current
  dense observation site and SAE attachment site.
- **Dense state** displays real residual coordinates for the current token as a
  signed coordinate field and reports dimensionality and basic statistics. It
  must not imply that screen proximity is semantic proximity.
- **Sparse state** displays real active SAE feature indices and activations,
  with available Neuronpedia descriptions. It must not imply that feature-index
  proximity is semantic similarity.
- Any of these views can become the central focus. The inactive views remain
  available as compact selectors.

### Optional experiments and transport

- Semantic tonality appears only in Transform and is labelled as one experiment.
- Existing live verbal-lens editing and interval editing remain available.
- Visual colour mapping remains collapsed as a proof of concept.
- Existing browser audio, mappings, WebSocket behavior, and OSC output remain
  operational.
- Route describes OSC as a connector and libossia/OSCQuery as planned work; it
  does not claim libossia has already been integrated.

## Interpreto boundary

Interpreto is a future interpretation adapter, not a decorative UI panel. Before
adding it, coordinate with the researchers on split points, supported model
families, generation/training datasets, attribution methods, and which concept
representations are scientifically valid. Only expose Interpreto views when the
backend returns real results with provenance.

## Non-goals for this slice

- No Windows receiver changes.
- No libossia dependency or OSCQuery namespace implementation.
- No claim that the sparse SAE exists at transformer layers where it was not
  trained.
- No invented semantic geometry for dense dimensions or SAE feature indices.
- No live-training support presented as complete.

## Acceptance checks

- Focused Python tests cover distinct SAE/observation hooks and live layer changes.
- Browser tests cover workspace structure, model anatomy metadata, vector
  statistics, and safe layer selection.
- The complete server suite and browser harness pass.
- `node --check app/client/main.js` passes.
- A real local GPU smoke run produces dense and sparse data in the workbench.
- Screenshots are captured and the server is stopped afterward.

## Second slice: Gemma traversal

The first anatomy view proves that a selected residual can come from a real
transformer block, but a layer picker alone does not reveal how one token changes
through the network. The next slice adds a truthful, bounded traversal view.

### Runtime profile

- When selected, capture the final-position residual at every decoder block for
  the same forward pass.
- Emit one compact profile row per block: residual RMS, maximum absolute value,
  RMS of the update from the previous block, and cosine similarity with the
  previous block.
- Continue emitting the complete residual vector for only the requested dense
  observation layer. Do not send every full hidden vector to the browser.
- Continue encoding the SAE from its trained attachment layer only.
- Profile capture must remain optional through the Emitter signal registry and
  must not extend OSC v1.

### Gemma representation

- Runtime architecture metadata must come from the loaded model configuration
  where possible: layer count/types, hidden and MLP widths, attention/KV heads,
  head width, sliding window, and context length.
- Show the actual repeated Gemma decoder structure: RMSNorm, local or full
  multi-query/grouped-query self-attention, residual addition, RMSNorm, gated
  MLP, and residual addition.
- The selected block can be changed with direct click, previous/next controls,
  or the layer slider. All controls use the same `observation_layer` parameter.
- Each block shows its real attention type and current profile activity. A
  selected profile row can be inspected immediately; the complete dense vector
  remains labelled with the layer at which it was actually captured.
- The UI must explain that profile metrics compare the same residual-stream
  coordinate basis across adjacent blocks; they are not neuron firing rates or
  a semantic projection.

### Completion record (2026-08-08)

Implemented on the Ubuntu GPU PC. `model.layer_profile` is an optional local
WebSocket stream and does not alter OSC v1 or the Windows Receiver. Runtime
Gemma metadata comes from the loaded configuration; the browser provides
direct, previous, next, and slider navigation through measured blocks. The full
residual vector remains restricted to the selected block and the SAE remains at
its trained attachment.

Verification: 77 server tests, `node --check app/client/main.js`, and the 137-ID
browser harness passed. A real Gemma 3 1B run returned 26 profile rows and a
1,152-value layer-7 residual. Headless Chromium rendered four live profile
metrics and the local-attention block diagram without page errors; the inspected
screenshot is `runs/emitter-gemma-traversal-live.png`. The server was stopped.

## Third slice: focused Gemma interface correction

The four-stage workbench and nested atlas tabs made the implemented ideas harder
to use. For the current research sessions, optimize the visible interface for
Gemma 3 and Gemma Scope 2 while retaining model adapters and generic signal keys
behind the UI.

### Information architecture

- Use exactly three primary workspaces: **Model**, **Signals**, and
  **Tonality**.
- Model answers “where are we observing Gemma?” Signals answers “what data is
  selected and what does it control?” Tonality provides the paper-derived live
  verbal/interval experiment.
- OSC remains available in a compact output popover. It is not a primary
  workspace, and libossia planning is not presented as an interactive feature.
- Keep the inference prompt and transport continuously visible, following the
  directness of Maël Simon's original browser layout.

### Gemma map

- The primary screen shows the entire loaded Gemma decoder from token embedding
  through every transformer block to logits on one continuous residual path.
- Every block is a real clickable observation site. The map distinguishes local
  and global attention, the selected dense probe, and the fixed Gemma Scope 2
  SAE attachment.
- The latest real all-layer profile appears as a restrained mathematical trace
  over the path. Do not animate invented neurons or imply semantic geometry.
- Keep the selected block's real structure and measurements directly below the
  whole-model path. Dense and sparse representations remain simultaneously
  visible instead of being hidden behind more tabs.

### Live tonality

- Give the lens editor enough horizontal space to edit name, verbal
  description, root, scale preset, and custom intervals without navigating a
  narrow nested disclosure.
- Add, duplicate, reorder, remove, enable, re-embed, prompt contribution, and
  raw/tonal blend behavior remains live for subsequent tokens.
- The live tonality match, evidence, interval output, and browser waveform stay
  visible beside the editor.

### Boundaries

- No new model backend, fake projection, arbitrary-hook editor, Connector
  contract, or Windows Receiver change is part of this correction.
- The absent `Rai_Report.pdf` cannot be claimed as reread. Use only the durable
  paper-derived notes already recorded in the roadmap until the PDF is restored.
- Preserve generation, WebSocket payloads, history, loading feedback, browser
  audio, mappings, feature evidence, scenes, color disclosure, and optional OSC.

### Acceptance checks

- Browser tests first fail on the old four-workspace/nested-atlas DOM and pass
  with the three-workspace Gemma interface.
- Layer-profile plotting and bounded layer navigation have focused behavior
  tests.
- The complete server suite, browser harness, and JavaScript syntax check pass.
- A real Gemma 3/Gemma Scope 2 GPU run populates the whole-model path, selected
  layer trace, dense residual, sparse features, and live tonality interface.
- Inspect screenshots at desktop width and stop the server afterward.

### Completion record (2026-08-08)

Implemented on the Ubuntu GPU PC. The visible interface now has exactly three
workspaces: Model, Signals, and Tonality. The inference prompt and transport
remain fixed above them, and OSC is an optional compact popover. The Model view
uses the loaded Gemma metadata to render the full 26-block residual path, real
local/global attention types, a clickable observation site at every block, the
movable dense probe, fixed layer-22 SAE attachment, selected-block internals,
and the measured all-layer update trace. Dense and sparse representations are
shown together. Signals owns selection, evidence, and the live mapping matrix.
Tonality owns the full-width editable verbal/root/scale/custom-interval lenses
and live resonance evidence. Workspace changes reset the content viewport so a
new view opens at its beginning.

TDD began with the old four-workspace/nested-atlas DOM failing the new browser
contract. Verification then passed with 77 server tests, JavaScript syntax
checking, and the 140-ID browser DOM/behavior harness. A real one-token Gemma 3
1B/Gemma Scope 2 GPU run selected block 7, returned a 1,152-coordinate dense
residual, measured all 26 blocks, exposed 54 active layer-22 SAE features out of
65,000, and updated the live tonality view without a browser error. The
inspected screenshots are `runs/gemma-focused-model-live.png`,
`runs/gemma-focused-signals-live.png`, and
`runs/gemma-focused-tonality-live.png`. The server was stopped afterward.

## Fourth slice: progressive-disclosure correction

The three-workspace correction still places too many controls, cards, metrics,
and experiments on screen simultaneously. The next correction must reduce the
default cognitive load without deleting working capabilities.

### Visible hierarchy

- Use exactly two primary destinations: **Model** and **Map**. Model remains the
  default. `Map` is the user-facing name for the existing signal-selection and
  mapping workflow.
- Keep the prompt, Run button, transport, token, and observation location
  continuously available.
- Move run/model/signal settings into one closed-by-default **Controls** drawer.
- Move verbal tonality into one closed-by-default **Tonality** drawer. It is an
  on-demand experiment, not a third primary destination.
- Keep OSC in its existing compact opt-in popover.

### Progressive disclosure

- The whole-model path and selected real Gemma block are the only large Model
  surfaces visible initially.
- Dense and sparse representations remain functional together inside one
  closed-by-default disclosure.
- The Map view initially shows selected observations and SAE/Neuronpedia
  evidence. Mapped controls and the full mapping matrix remain functional inside
  one closed-by-default disclosure.
- Tonality lenses render as a compact accordion with only one lens editor open
  initially. Every existing lens action and live update remains available.

### Behavior and boundaries

- Opening Controls closes Tonality and opening Tonality closes Controls. A
  backdrop, close buttons, and Escape return focus to the primary workspace.
- Workspace changes close transient drawers and reset the main viewport.
- Preserve model generation, loading feedback, browser audio, visualization,
  WebSocket payloads, mappings/scenes, live lens updates, and OSC behavior.
- No server, Connector-contract, or Windows Receiver change is part of this
  correction.

### Acceptance checks

- Browser tests first fail against the three-tab/persistent-sidebar interface.
- The default DOM has two primary workspace tabs and closed Controls, Tonality,
  representation, and mapping disclosures.
- Browser behavior tests cover mutual drawer exclusion and workspace reset.
- At desktop width the primary model path is wider than 1,000 pixels and the
  initial viewport does not contain the dense/sparse canvases or mapping rows.
- JavaScript syntax, the browser harness, complete server suite, and a real
  Gemma/Gemma Scope GPU smoke run pass. Screenshots are inspected and the server
  is stopped afterward.

### Completion record (2026-08-08)

Implemented on the Ubuntu GPU PC. Model and Map are now the only primary
destinations. The persistent sidebar was replaced with a workspace-aware
Controls drawer, and Tonality moved from a primary tab to a mutually exclusive
right drawer. Both are closed initially and can be dismissed by their close
button, the backdrop, Escape, or a workspace change. Loading feedback remains a
small independent status toast. The model path and selected block remain
visible initially; dense/sparse representations and the mapping matrix are
closed disclosures. Tonality retains eight live lenses but renders them as an
accordion with one editor open.

TDD began with the previous three-tab/persistent-sidebar DOM failing the new
two-destination and drawer contract. Verification passed with 77 server tests,
`node --check app/client/main.js`, and the 149-ID browser DOM/behavior harness.
At a 1,440 px viewport, the actual model map was 1,376 px wide, both drawers and
both secondary disclosures started closed, drawer exclusion worked, only one of
eight lens editors was open, and closed mapping rows had zero rendered height.
A real Gemma 3 1B/Gemma Scope 2 run selected block 7, measured all 26 blocks,
returned a 1,152-coordinate residual and 54 active SAE features out of 65,000,
and updated the live `luminous resolve` match without a browser error. The
inspected screenshots are `runs/emitter-decluttered-model-live.png`,
`runs/emitter-decluttered-map-live.png`, and
`runs/emitter-decluttered-tonality-live.png`. The server was stopped afterward.
