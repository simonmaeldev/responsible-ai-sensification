# Emitter Neural Workbench

## Status

Implementation specification for the August 2026 interface correction.

## Purpose

The Ubuntu application is a general Emitter workbench for observing and
interpreting model activity. It is not inherently a musical instrument. Sound,
semantic tonality, colour, OSC, and external receivers are optional experiments
or destinations built from model observations.

The interface must keep four epistemic stages visibly distinct:

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

