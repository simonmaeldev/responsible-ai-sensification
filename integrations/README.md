# External Integration Development

This directory contains a passive sparse-activation observer contract,
deterministic fixtures, and starter notes for TouchDesigner and ossia score.
The observer path is optional: the browser Emitter remains useful without an
external host.

## Fast development loop

Start the app, connect a WebSocket client to `/ws/activations`, and replay the
fixture without loading Gemma or the SAE:

```bash
./scripts/integration-dev.sh serve
./scripts/integration-dev.sh replay 250 true
./scripts/integration-dev.sh status
./scripts/integration-dev.sh stop
```

Run the automated contract checks with:

```bash
./scripts/integration-dev.sh check
```

The checked-in events vary feature count, activation magnitude, cluster, token,
and tonality. Each event also records its run, model, selected observation
layer, and fixed SAE provenance.

## Transport boundaries

- Rich sparse JSON: `ws://127.0.0.1:8080/ws/activations`
- Fixture replay: `POST /api/integrations/replay`
- Replay stop: `POST /api/integrations/replay/stop`
- Observer status: `GET /api/integrations/status`
- Production external OSC: the existing, optional `/rai/v1` sender configured
  in the browser

The passive WebSocket endpoint mirrors live events and accepts only `ping`; it
does not start, stop, or reconfigure generation. It carries the complete sparse
feature list, descriptions, cluster metadata, semantic-tonality summary, and
observation provenance.

It deliberately does not create a second OSC namespace or broadcast to default
ports. Use the established `/rai/v1` fixture when testing OSC:

```bash
./scripts/integration-dev.sh osc-fixture 127.0.0.1 9000
./scripts/integration-dev.sh listen 9000
```

Only one process can bind a UDP listener port at a time. Stop the monitor before
opening the corresponding host receiver.

The complete Max for Live receiver remains under `max/rai_osc_receiver/` and
must not be replaced by a competing starter patch.
