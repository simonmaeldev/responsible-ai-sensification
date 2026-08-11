# ossia score Development

ossia score is a candidate timeline and automation Receiver. The current app
does not expose a separate ossia bus or automatic OSCQuery namespace.

To inspect the verified OSC v1 contract today:

1. Add an OSC device in score and choose an unused UDP input port.
2. Configure the same host and port in the browser's OSC popover.
3. Run a normal Emitter generation, or send the model-free fixture with
   `./scripts/integration-dev.sh osc-fixture 127.0.0.1 <port>`.
4. Learn or map only the `/rai/v1` addresses the scenario actually needs.

The current OSC fixture carries lifecycle, bounded notes, tonality, and live
Emitter controls. It does not carry the complete sparse feature list; use a
`/ws/activations` client for that rich observation data.

Before adding OSCQuery discovery or inbound score controls, specify a small
namespace with parameter types, ranges, units, and access modes. Dense arrays
should remain on a suitable high-bandwidth path rather than being forced into
OSC messages.
