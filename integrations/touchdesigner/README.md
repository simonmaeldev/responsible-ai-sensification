# TouchDesigner Development

TouchDesigner can consume the complete sparse feature event as a passive
WebSocket observer. Gemma, the SAE, and artistic mappings remain outside the
TouchDesigner process unless a receiver mapping deliberately introduces them.

## Rich WebSocket data

1. Add a WebSocket DAT and set its address to
   `ws://127.0.0.1:8080/ws/activations`.
2. Add Table DATs named `rai_features` and `rai_state`.
3. Use `websocket_callbacks.py` as the WebSocket DAT callbacks DAT.
4. Start replay with `./scripts/integration-dev.sh replay 250 true`.

`rai_features` is replaced on every token with one row per sparse active
feature. `rai_state` exposes the run, model/site provenance, token, feature
count, and primary tonality. Convert selected DAT columns into CHOP channels
only when a visual mapping needs them.

For a remote TouchDesigner machine, replace `127.0.0.1` with the Ubuntu Emitter
host address. The callbacks and fixtures can be tested on the Ubuntu laptop,
but operator cooking, GPU rendering, and `.toe`/`.tox` save/reload require a
manual TouchDesigner smoke test.

## OSC is a separate path

The app's optional `/rai/v1` OSC output carries bounded post-tonality note and
control events, not the complete raw sparse list. Configure that destination in
the browser only if a TouchDesigner experiment explicitly needs those existing
messages. A future top-K or OSCQuery extension needs its own versioned spec and
must not silently replace `/rai/v1`.
