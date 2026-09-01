# RAI libossia OSCQuery Sidecar

This optional Ubuntu GPU PC process publishes the Emitter's stable, bounded,
read-only `/rai` probe-summary tree through official libossia. It does not run
inference, interpret probe values, or transport raw dense vectors or complete
sparse SAE data.

Build it with:

```bash
./scripts/build_ossia_probe_server.sh
```

The normal app launcher prepares the sidecar opportunistically. The browser's
**Connect → Publish to ossia / OSCQuery** control starts it for a run and shows
failure-isolated status. Defaults are OSC UDP `9010` and OSCQuery `5678`.

See [the complete score/libossia integration guide](../../docs/OSSIA_SCORE_LIBOSSIA_INTEGRATION.md)
for topology, score Device Explorer setup, boundaries, and installed checks.
