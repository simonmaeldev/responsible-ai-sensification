# Feature: Passive External Observer Development Workflow

## Goal

Let TouchDesigner and future research/visual tools develop against stable sparse
activation fixtures without loading Gemma and the SAE, while keeping the
verified `/rai/v1` OSC Connector and Max receiver intact.

## Implemented scope

- [x] Define a versioned sparse activation JSON contract.
- [x] Preserve run, model, observation-layer, SAE-layer, and SAE-width
  provenance.
- [x] Build live activation events before Receiver-specific mapping.
- [x] Add passive WebSocket observers at `/ws/activations`.
- [x] Add deterministic NDJSON fixtures and replay API controls.
- [x] Add one command for serve/replay/status/stop/check workflows.
- [x] Add TouchDesigner WebSocket callbacks and setup instructions.
- [x] Keep the existing `/rai/v1` OSC fixture available as a separate command.
- [x] Add tests for sorting, normalization, provenance, observer isolation, and
  browser/OSC forwarding compatibility.
- [ ] Smoke-test fixture and live events inside TouchDesigner.
- [ ] Save a project-specific `.toe` or `.tox` after its visual mapping is
  chosen.

## Explicit non-goals

- No second unversioned OSC activation namespace.
- No default three-port broadcast or always-on UDP listener.
- No replacement for `max/rai_osc_receiver/`.
- No generic bidirectional control bus without a selected-control spec.
- No claim that the Ubuntu laptop can validate TouchDesigner GPU behavior.

## Development loop

Use `./scripts/integration-dev.sh serve`, connect a passive client, then run
`./scripts/integration-dev.sh replay 250 true`. Replace fixture replay with a
normal browser generation only after the host mapping is stable.

Automated acceptance is `./scripts/integration-dev.sh check`. Full acceptance
requires one fixture replay and one live-model event observed in TouchDesigner
on a machine where that host is actually installed.
