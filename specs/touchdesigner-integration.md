# Feature: TouchDesigner Sparse Activation Observer

## Goal

Let TouchDesigner inspect complete token-level sparse SAE activations without
moving Gemma inference, SAE extraction, or artistic meaning into TouchDesigner.

## Implemented path

`/ws/activations` is a passive WebSocket endpoint. A browser-controlled live run
publishes one `activation_token` event per token, and deterministic fixture
replay publishes the same schema without model loading.

Each event identifies:

- run ID, sequence, token ID/text, and elapsed time;
- model, selected dense observation layer, fixed SAE layer, and SAE width;
- the complete sorted sparse active-feature list;
- raw and peak-normalized activation values;
- available Neuronpedia descriptions and cluster metadata;
- an optional semantic-tonality summary.

The endpoint does not start, stop, or reconfigure generation. Observer failures
are removed without interrupting the browser run.

## TouchDesigner setup

Use a WebSocket DAT connected to `ws://<emitter-host>:8080/ws/activations` and
the checked-in `integrations/touchdesigner/websocket_callbacks.py`. The callback
populates `rai_features` and `rai_state` Table DATs. Selected columns can then be
converted to CHOP channels for a specific visual mapping.

## OSC boundary

The current `/rai/v1` OSC output is a separate, optional Connector carrying
bounded post-tonality notes and controls. It may be configured to a
TouchDesigner port when those existing events are useful, but it is not the raw
sparse feed. A top-K activation projection or OSCQuery namespace requires a
future versioned spec.

## Acceptance

- Automated tests cover event ordering/normalization/provenance, fixture
  validity, observer failure isolation, and coexistence with browser/OSC output.
- `./scripts/integration-dev.sh check` compiles the TouchDesigner callback.
- Manual acceptance still requires fixture and live observation inside an
  actual TouchDesigner project plus `.toe`/`.tox` save/reload.
