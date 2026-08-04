# Feature: Ubuntu-to-Ableton OSC Bridge

## Machine Contract

- **Source and current implementation scope:** Ubuntu GPU PC.
- **Destination, not implemented in the Ubuntu task:** Windows laptop running
  Ableton Live, Max for Live, and ossia.
- **Not involved by default:** Ubuntu laptop.
- Each computer has its own Git clone. Git synchronizes code; OSC carries live
  runtime messages over the LAN.

## Goal

Add an optional OSC output to the existing FastAPI/browser pipeline. Musical
events must be emitted after semantic-tonality pitch processing, so edits made
live in the browser affect the next token messages received by Max for Live.

## Non-Goals For The Ubuntu Task

- Do not create the Max for Live or ossia receiver.
- Do not edit files on, or claim to configure, the Windows laptop.
- Do not replace the existing browser Web Audio output.
- Do not add Ableton Link, MIDI, inbound OSC feedback, session persistence, or
  automatic Windows discovery in this slice.
- Do not hardcode a machine IP address.

## User Controls

Add a compact external-output group to the browser UI:

- Enable OSC output, disabled by default.
- Destination host/IP, blank by default.
- Destination UDP port, default `9000`.
- Maximum notes per token, default `32`, with a safe bounded range.
- Clear configured/status text. Because UDP has no handshake, do not label the
  destination "connected" merely because sending did not raise an error.

The OSC settings should use the existing parameter collection, WebSocket update,
and browser `localStorage` conventions. Host, port, enable state, and note cap
must be editable during a run and apply to subsequent tokens.

## Server Design

- Add a small reusable OSC output helper under `app/server/pipeline/`; keep
  transport encoding out of the main stream router where practical.
- Use a maintained Python OSC library rather than hand-encoding packets.
- Extend `PipelineParams` with validated/coerced OSC settings.
- Integrate sending at the point where the canonical token event already has its
  final post-tonality `notes` data.
- OSC failures must not stop generation or browser streaming. Log the problem
  and provide a concise status event to the browser.
- Do not perform blocking network discovery or wait for acknowledgements in the
  token loop.
- Sort candidate notes by descending activation and cap them before OSC output.
  The uncapped browser/WebSocket event must remain unchanged.

## OSC Contract Version 1

Use the root namespace `/rai/v1`. Each token gets a monotonically increasing
`sequence` number within the run.

- `/rai/v1/run/start`: `run_id`, BPM, mode.
- `/rai/v1/token`: `run_id`, sequence, token ID, token text, elapsed milliseconds.
- `/rai/v1/note`: `run_id`, sequence, note index, feature index, frequency Hz,
  raw activation, cluster ID (`-1` when absent), instrument string.
- `/rai/v1/tonality`: `run_id`, sequence, dominant tonality name, score, effective
  pitch-bias value. Omit when tonality data is unavailable.
- `/rai/v1/token/end`: `run_id`, sequence, emitted note count.
- `/rai/v1/run/done`: `run_id`.
- `/rai/v1/run/stop`: `run_id`.
- `/rai/v1/run/silent`: `run_id` when loop playback becomes silent.

Emit live control changes that matter to receiver timing/mapping:

- `/rai/v1/control/bpm`: BPM.
- `/rai/v1/control/mode`: mode string.
- `/rai/v1/control/loop`: `0` or `1`.
- `/rai/v1/control/tonality_enabled`: `0` or `1`.
- `/rai/v1/control/prompt_influence`: float.
- `/rai/v1/control/tonality_pitch_bias`: float.

The Windows receiver must tolerate unknown addresses so the contract can be
extended without breaking version 1.

## Likely Files

- `pyproject.toml` and lockfile for the OSC dependency.
- `app/server/pipeline/osc_output.py` for encoding/sending.
- `app/server/session.py` for parameters.
- `app/server/routers/stream.py` for lifecycle and canonical event forwarding.
- `app/client/index.html`, `app/client/style.css`, and `app/client/main.js` for
  controls and status.
- `app/server/tests/` for parameter, encoding, failure, and stream integration
  coverage.

## Verification

- Unit-test parameter coercion, note ordering/capping, address payloads, disabled
  behavior, and non-fatal send failures.
- Run the complete server test suite.
- Run `node --check app/client/main.js`.
- Run a loopback UDP/OSC receiver on the Ubuntu GPU PC and confirm one test run
  produces start, token, bounded note, token-end, and done/stop messages in order.
- Report the Windows/Ableton LAN test as not exercised until the separate Windows
  receiver exists.

## Acceptance Criteria

- OSC is opt-in and no packets are sent while disabled or unconfigured.
- Live host, port, cap, BPM, mode, loop, and tonality-control changes affect
  subsequent output without restarting generation.
- Max receives final frequencies after semantic-tonality pitch bias.
- High feature counts cannot create an unbounded OSC packet burst.
- OSC errors do not interrupt generation, looping, browser visualization, or
  browser audio.
- Existing server tests and JavaScript syntax checks pass.
