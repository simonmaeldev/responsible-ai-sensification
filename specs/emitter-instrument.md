# Feature: GPU Emitter Mapping Instrument

## Role Contract

The project uses three logical roles. A role is a responsibility, not a fixed
protocol, application, operating system, or physical computer.

- **Emitter:** observes arbitrary model/runtime probes and may expose raw data,
  derived measurements, or optional artistic interpretations and mapped
  controls. The current Gemma/SAE musical and visual work is one instrument, not
  a permanent boundary. In the current setup the Emitter is the FastAPI/browser
  application on the Ubuntu GPU PC.
- **Connector:** transports selected emitter events and controls without owning
  their artistic meaning. OSC v1 is the current connector, but future connectors
  may use OSCQuery, MIDI, WebSockets, files, or another bounded transport.
- **Receiver:** consumes connector data and applies it in an external system.
  The current receiver is Max for Live/ossia on Windows; future receivers may be
  TouchDesigner, another browser, a hardware instrument, or another application.

Emitter features must work and remain observable locally without any connector
or receiver. Connector and receiver failures must not stop the emitter.

## Goal

Turn the Ubuntu GPU PC browser application into a live mapping instrument. The
artist can inspect Gemma Scope/Neuronpedia/semantic-tonality signals, transform
them into named controls, and hear/see the result in the browser before deciding
which controls should leave the emitter.

## Canonical Emitter Signal Bus

Each token retains its raw notes and receives an additional `emitter` payload:

- `signals`: named raw and normalized measurements derived from active SAE
  features, feature descriptions, clusters, pitches, token timing, and semantic
  tonality;
- `controls`: mapped browser audio/visual target values;
- `mappings`: compact per-row input/output diagnostics explaining the current
  transformation.

Live mappings apply to subsequent tokens. They do not mutate the canonical raw
or post-tonality note evidence.

## Mapping Matrix

Each row contains:

- enabled state;
- named source signal;
- named browser target;
- input threshold and optional inversion;
- linear, ease-in, ease-out, or S-curve response;
- quantization steps;
- smoothing;
- bounded output range.

Mappings are bounded and coerced server-side. When multiple rows target the same
control, the later enabled row wins deterministically.

## Local Targets

Initial browser-audio targets include gain, pitch shift, note density, duration,
timbre, pan, filter cutoff/resonance, and delay mix/time. Visual targets include
energy, hue, motion, and activation-bar scale.

## Live Feature Browser

The browser shows active SAE features with feature index, Neuronpedia
description, activation, cluster, raw frequency, and interpreted frequency. The
artist can search, pin, mute, and solo features for local browser audition.
Audition state is local to the emitter and is not silently imposed on connectors.

## Tonality Lenses

Existing live lens names, verbal descriptions, and intervals remain editable.
Lens edits report embedding/re-embedding status. Add, duplicate, enable/disable,
reorder, remove, and reset actions are available while performing.

## Scenes And Morphing

Instrument scenes persist locally in the browser. A scene captures mappings,
tonality lenses, prompt/pitch interpretation controls, master volume, and local
feature-audition state. Scenes can be recalled directly or used as A/B endpoints
for a live numeric morph; verbal/category choices switch at the midpoint.

## Non-Goals

- Do not change the Windows receiver in this phase.
- Do not extend OSC v1 until emitter controls are validated locally.
- Do not hardcode a receiver address or require a network connection.
- Do not hide or discard raw SAE/Neuronpedia evidence.

## Verification

- Unit-test signal extraction, mapping coercion, curves, quantization,
  smoothing, output bounds, and deterministic target collisions.
- Verify live parameter updates affect subsequent emitter payloads.
- Run the complete server test suite.
- Run JavaScript syntax checks.
- Start the application on the Ubuntu GPU PC and exercise the mapping UI with a
  real or deterministic token stream.

## Acceptance Criteria

- The emitter GUI is useful with OSC disabled and no receiver running.
- Model/SAE/semantic sources are visible as raw and normalized values.
- Mapping changes apply without restarting generation.
- Browser audio and visualization consume mapped controls safely.
- Feature search/pin/mute/solo and scene save/recall/morph work locally.
- Live lens edits visibly report embedding status.
- Existing browser transport/history, raw notes, tonality evidence, WebSocket
  flow, and optional OSC output continue working.
