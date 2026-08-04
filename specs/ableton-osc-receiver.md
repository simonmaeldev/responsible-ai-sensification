# Feature: Windows Max for Live OSC Receiver

## Machine Boundary

- **Execution and implementation machine:** Windows laptop.
- **Remote runtime source only:** Ubuntu GPU PC running Gemma/SAE inference,
  FastAPI, the browser UI, and the completed Phase 5A OSC emitter.
- The Windows receiver does not access the Ubuntu filesystem and does not
  modify or reimplement the Ubuntu OSC emitter.

## Scope

Implement Phase 5B as a focused Max for Live/ossia receiver for OSC Contract
Version 1 in `specs/ableton-osc-bridge.md`. Phase 5C remains pending until the
real Ubuntu-to-Windows LAN and Ableton audio test is exercised.

Out of scope:

- Ableton Link or master-clock policy;
- MPE;
- feedback to the Ubuntu application;
- automatic network discovery;
- receiver session persistence;
- changes to the `/rai/v1` contract;
- production instrument/effect mappings beyond a bounded preview synth.

## Verified Windows Dependencies

- Ableton Live 12 Suite 12.4.3.
- Bundled Max/Max for Live 9.1.4.
- ossia score 3.8.2.
- Official ossia Max Windows package 1.2.4 installed under the Max 9 user
  package folder.
- The installed Max process loads `ossia.device.mxe64`,
  `ossia.parameter.mxe64`, `ossia.model.mxe64`, `ossia.remote.mxe64`, and
  `ossia-max.dll64` successfully.

## Receiver Layout

```text
max/rai_osc_receiver/
  RAI OSC Receiver.maxpat        # editable Max/Max for Live source patch
  rai_osc_receiver.js            # contract parser, frame state, diagnostics
  rai_receiver_panel.js          # presentation-mode diagnostic display
  rai_ossia_namespace.maxpat     # typed config/status OSCQuery namespace
  rai_osc_voice.maxpat           # one safely bounded sine preview voice
  README.md                       # loading, use, and Ableton packaging notes
  tests/
    test_receiver_logic.js       # deterministic contract/state-engine test
  tools/
    send_osc_loopback.ps1        # Windows-only OSC v1 verification sender
```

The source patch remains textual and reviewable. Max creates the distributable
`.amxd` container when the source is saved as a Max for Live device; the binary
container is not hand-authored.

## Max/ossia Architecture

### Data Plane

- A native Max `udpreceive` listens on a configurable local UDP port, default
  `9000`. It binds locally; no Ubuntu address is hardcoded.
- `udpreceive` performs the simple OSC decoding required by the unbundled
  `python-osc` messages from Phase 5A.
- `rai_osc_receiver.js` validates and handles every documented address:
  - `/rai/v1/run/start`
  - `/rai/v1/token`
  - `/rai/v1/note`
  - `/rai/v1/tonality`
  - `/rai/v1/token/end`
  - `/rai/v1/run/done`
  - `/rai/v1/run/stop`
  - `/rai/v1/run/silent`
  - every documented `/rai/v1/control/*` address.
- Unknown addresses are counted and ignored. Missing fields, non-finite values,
  mismatched run/sequence values, and incomplete frames update `last_error` and
  are discarded without throwing out of the Max JavaScript handler.

### Token Frames and Metadata

- Frames are keyed by `(run_id, sequence)`.
- Repeated `/rai/v1/note` messages append to the keyed frame.
- `/rai/v1/token/end` is the only normal frame flush boundary.
- The receiver retains raw frequency Hz, raw activation, cluster ID, feature
  index, instrument string, and tonality values in the completed frame state.
- The frequency-Hz value is sent directly to the voice patch. It is never
  converted to or rounded through a MIDI note number.
- A new run clears stale frames. Incomplete stale frames are bounded and
  replaced rather than allowed to grow indefinitely.

### Preview Audio

- `poly~ rai_osc_voice 16` provides at most 16 simultaneous sine preview
  voices. Frames with more notes remain represented in diagnostics but only the
  16 strongest activations are previewed.
- Raw activation is preserved in receiver state. A separate per-frame
  normalization derives a bounded preview gain; it does not alter metadata.
- Every voice uses a short attack/release envelope and a hard amplitude bound.
- A bounded master gain and mute control sit after the polyphonic sum.
- Timed mode derives a bounded note duration from live BPM. Sustain mode holds
  the current frame until the next token frame, `/run/silent`, or `/run/stop`.
- `/run/silent` and `/run/stop` broadcast release to all voices.
- `/run/done` updates status but does not silence voices because loop playback
  may follow.

### Structured Namespace

- `ossia.device rai_receiver` owns a structured local configuration/status
  tree.
- `ossia.parameter` nodes expose receiver configuration and diagnostics,
  including port, master gain, mute, receiver state, latest run ID, sequence,
  token text, received note count, dominant tonality, BPM, mode, loop,
  tonality-enabled, prompt influence, pitch bias, last raw note metadata, and
  last error.
- The patch exposes this tree through OSCQuery on OSC port `9011` and WebSocket
  port `5679`, leaving data port `9000` dedicated to `/rai/v1` input and avoiding
  ossia's documented default ports.
- Status uses the honest words `listening` before data and `receiving` after a
  valid message. UDP is never described as connected and no handshake is
  implied.

## Diagnostics

The presentation view shows:

- listening UDP port;
- `listening` or `receiving` state;
- latest run ID and sequence;
- token text and received note count;
- dominant tonality;
- BPM, mode, and loop state;
- tonality-enabled, prompt-influence, and pitch-bias controls;
- last received frequency, activation, feature, cluster, and instrument;
- last error;
- master gain and mute.

## Local Verification

1. Parse all textual `.maxpat` files as JSON and syntax-check the PowerShell
   loopback sender.
2. Open the source receiver in bundled Max 9.1.4 and confirm the patch,
   `poly~` dependency, JavaScript, and ossia externals load without missing
   objects or broken connections.
3. Confirm UDP port 9000 is bound locally.
4. Run `tools/send_osc_loopback.ps1` against `127.0.0.1:9000`. The fixture sends
   start, all controls, token, multiple notes, tonality, token-end, done, an
   unknown address, malformed/incomplete input, silent, and stop.
5. Query the local OSCQuery namespace to confirm receiver state. In particular,
   verify the sentinel frequency `445.125` reaches the last-frequency state
   unchanged, controls update live, unknown input is ignored, and silent/stop
   increment the all-voices-release diagnostic.
6. Treat standalone Max preview and Ableton-hosted audio as separate claims.
   Do not claim an Ableton audio pass until the device is loaded and heard in
   Live.

## LAN and Firewall Boundary

- Current Windows Wi-Fi IPv4 is discovered at runtime; it is not stored in the
  patch.
- UDP port 9000 must be checked against the active Windows firewall profile.
- No firewall rule may be created or modified without first reporting the exact
  proposed rule and receiving approval.
- The Ubuntu browser should receive an explicit Windows IPv4 address and UDP
  port only during the Phase 5C two-machine test.
- Before model inference, run the production-backed Ubuntu fixture with
  `uv run python -m scripts.send_osc_test --host <current-windows-ipv4> --port 9000`.
  This fixture exercises start, all controls, timed and sustain token frames,
  bounded final-frequency notes, tonality, done, silent, and stop without
  loading Gemma or the SAE.

## Acceptance Criteria

- All OSC v1 addresses and live controls are handled without restart.
- Notes are grouped by run/sequence and flushed by token-end.
- Unknown or malformed input cannot break the device.
- Raw final frequency reaches the voice mapping unchanged.
- Stop and silent release every voice; done does not.
- Audio is bounded, muteable, and limited to 16 preview voices.
- Required metadata is retained for later Ableton mappings.
- ossia provides a queryable configuration/status namespace.
- Local loopback verification is reported independently from the unexercised
  two-machine LAN test.
