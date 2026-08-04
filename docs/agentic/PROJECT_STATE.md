# Project State

Last updated: 2026-08-04

## Branch

Current branch: `nicolas-attempts`

This branch was created from `main` for Nicolas's work. Confirm the branch before any implementation session:

```bash
git branch --show-current
```

## Current Mode

Implementation is active on the paper-driven semantic-tonality GUI direction.

The current interface now exposes a local MiniLM-based semantic-tonality layer:
verbal tonality descriptions and active SAE feature descriptions share the same
embedding space, prompt semantics can be blended into the token signal, and note
frequencies can be softly pulled toward the active tonality's custom intervals.

Phase 5A is complete on the Ubuntu GPU PC: the browser can opt into a
live-configurable OSC v1 output whose destination, UDP port, and per-token note
cap can be changed during a run. The sender mirrors final post-tonality note
events without changing browser audio, visualization, or token payloads.

Phase 5B is in progress on the Windows laptop. The receiver source has now been
saved through Live's **Edit in Max** workflow as the Max-generated
`max/rai_osc_receiver/RAI OSC Receiver.amxd`, with its JavaScript, voice, panel,
and ossia dependencies beside it. The Live-hosted panel, UDP 9000 listener, and
OSCQuery namespace were exercised with the complete Windows loopback fixture.
The remaining Phase 5B gap is the audible/meter check because Ableton's audio
engine was off during verification.

The two-machine transport path is now verified in both fixture and real-model
runs. The Ubuntu GPU PC sent `/rai/v1` UDP to the Windows Live-hosted receiver,
and the receiver's OSCQuery state confirmed the expected fixture fields and a
real three-token Gemma/SAE stream carrying capped, final post-tonality notes.

Agent workflow clarification: use Codex for planning, implementation, review, and
remote-machine coordination. Do not assume Anthropic/Claude tooling for agentic
project work.

## Machine Topology

- **Ubuntu GPU PC**: runs Gemma/SAE inference, FastAPI, the browser interface,
  and the completed outbound OSC emitter.
- **Windows laptop**: runs Ableton Live, Max for Live, and ossia; it hosts the
  Max/ossia receiver and remains the Phase 5B audible-output verification target.
- **Ubuntu laptop**: a separate lightweight development/control environment; no
  GPU, Ableton, Max, or shared-cache assumptions should be made.

Every task must identify its execution machine. Worktrees are not shared across
computers: each computer uses its own clone/branch. Git moves source changes;
OSC/OSCQuery moves live performance data.

## Recent Setup

- Inspected local archive: `/home/apaixonada/EvaPortelance/responsible-ai-sensification-zougoulou-main.zip`.
- Extracted old material to a local ignored `references/` folder.
- Added `references/` to `.gitignore`.
- Inspected local PDF: `/home/apaixonada/Downloads/Mila Community Agentic Coding Best Practices (1).pdf`.
- Set up this agentic workflow documentation.
- Added `app/server/pipeline/semantic_tonality.py` and
  `app/server/pipeline/tonality_data/default_tonalities.json` as the first
  local, Anthropic-free semantic tonality foundation.
- Wired semantic tonality into the browser stream with token-level payloads,
  prompt blend, pitch pull, a live tonality panel, and an analyser-backed
  waveform canvas.
- Added local description-based cluster-name fallback when Anthropic cluster
  naming is unavailable.
- Added live performance tonality lenses: editable lens descriptions/intervals
  can be changed before or during a run, raw/interpreted blend is exposed as a
  performance control, and each token can report run-level tonality memory plus
  top active-feature evidence for the current sound.
- Completed the Ubuntu Phase 5A OSC emitter with the `/rai/v1` lifecycle,
  control, token, bounded-note, and tonality messages. OSC is disabled and
  unconfigured by default, uses no hardcoded Windows address, and reports UDP
  delivery as unconfirmed.
- Added focused OSC parameter, payload, live-reconfiguration, failure-isolation,
  and WebSocket-forwarding tests. The full server suite passes with 48 tests;
  `node --check app/client/main.js` passes.
- Verified the real UDP encoding locally against a loopback receiver on the
  Ubuntu GPU PC. It received 14 ordered messages for a test run, including two
  capped notes carrying final post-tonality frequencies, followed by done and
  stop.
- Synchronized the Windows clone to `nicolas-attempts` at `ef45749`, where
  Phase 5A and the OSC v1 contract are present.
- Verified Ableton Live 12 Suite 12.4.3, bundled Max/Max for Live 9.1.4, and
  ossia score 3.8.2 on Windows.
- Installed the official ossia Max Windows package 1.2.4 in the Max 9 user
  package folder and confirmed the installed Max process loads its device,
  parameter, model, remote, and shared-library binaries.
- Added the focused Windows receiver spec and source under
  `specs/ableton-osc-receiver.md` and `max/rai_osc_receiver/`.
- Verified all textual Max patches parse as JSON and have valid patch-cord
  endpoints. The deterministic receiver test handles all 14 documented
  addresses, preserves raw frequency `445.125` at the voice-message boundary,
  updates all live controls, ignores unknown addresses, and confirms done does
  not release voices while silent and stop do.
- Opened the receiver in bundled Max Runtime, confirmed it bound
  `0.0.0.0:9000`, and sent the complete loopback fixture including malformed
  and unknown input. Max Runtime remained alive and listening afterward.
- Determined the Windows Wi-Fi IPv4 as `192.168.1.208`. The active firewall
  profile is Public with inbound blocked by default, but enabled Ableton Live 12
  program rules already allow inbound UDP on Public and Private profiles. No
  firewall rule was created or modified.
- Found and fixed the Live-hosted OSCQuery publication defect: the namespace
  abstraction now uses standard Max `inlet`/`outlet` objects and current ossia
  `@mode get`/`@mode bi` attributes. A static regression check now guards that
  boundary and read/write policy.
- Saved the receiver through Live's **Edit in Max** workflow as the Max-generated
  `RAI OSC Receiver.amxd` beside its dependencies and loaded it in Ableton. The
  hosted process bound UDP 9000, OSCQuery UDP 9011, and HTTP/TCP 5679.
- Replayed the complete Windows loopback fixture into the Live-hosted device.
  OSCQuery reported run `windows-loopback-v1`, token `loopback token`, two notes,
  final frequency `445.125`, BPM `96`, sustain mode, prompt influence `0.625`,
  pitch bias `0.375`, unknown count `1`, three voice releases, and final reason
  `run_stop`. Status parameters were read-only and config parameters remained
  bidirectional.
- Ableton's audio engine was off during that pass, so no audible or meter result
  is claimed.
- Reviewed the synchronized Windows receiver against the production Ubuntu
  emitter. The exact OSC address, argument order/type, lifecycle, live-control,
  final-frequency, and note-cap expectations match; the receiver state test and
  textual patch checks also pass on the Ubuntu clone.
- Added `scripts/send_osc_test.py`, a configurable model-free LAN fixture that
  uses the production `OscRunOutput`. A real loopback receiver test confirms two
  token frames, bounded notes, live control changes, done, silent, and stop in
  order. No Windows address is hardcoded, and the current full server suite
  passes with 51 tests.
- Verified the cross-machine LAN fixture from the Ubuntu GPU PC to the Windows
  Live-hosted receiver at the then-current `192.168.1.208:9000` destination.
  OSCQuery confirmed run `ubuntu-lan-d05982a212e6`, both token frames, the final
  two-note frame, raw final frequency `445.125`, BPM `96`, sustain mode, control
  changes, and final `run_stop`; this result was observed at the receiver rather
  than inferred from UDP transmission.
- Ran a real three-token Gemma/SAE generation through semantic tonality and the
  production OSC output. Windows OSCQuery confirmed run
  `c3be7ff96b2241b9923b639201ffad49`, sequence `3`, token ` is`, the configured
  two-note cap, tonality `luminous resolve`, pitch bias `0.55`, and clean
  `run_stop`. The received frame preserved final post-tonality frequencies and
  SAE activation, feature, cluster, and instrument data.

## Local Reference Material

`references/` is intentionally ignored by Git.

It currently contains old snapshot reference material, especially the removed tonality/pitch-policy modules and an implementation ideas note. Treat it as optional background only; do not import from it directly unless the user asks to port something.

## Current App Direction

Use the new interface already present in this repo:

- Browser transport controls.
- Token history and paused-token buffering.
- Cluster visualization.
- Generated text output linked to token playback.
- Enriched cluster naming/colors.

Avoid reverting to the older archive interface.

## Open Decisions

- Where the user will place the term paper.
- Whether paper passages should become prompts, annotations, comparison units, or all three.
- Which Ableton parameters should follow semantic tonality after the initial
  note/activation bridge: timbre, envelope, density, filter, or brightness.
- What the first user-facing workflow should be after paper ingestion.
- Whether paper passages should become selectable prompt presets or stay outside
  the app as reference context.
- Whether Ableton or the app should be the master clock for the first
  two-machine performance test.

## Handoff Notes

### Immediate integration status and next action

Do not rebuild or redesign the Windows receiver. The Max-generated
`max/rai_osc_receiver/RAI OSC Receiver.amxd` exists in the Windows Ableton set,
listens on UDP 9000, and has passed Windows-local loopback plus Ubuntu-to-Windows
fixture and real Gemma/SAE reception checks. Recheck the Windows IPv4 before a
new session because DHCP can change it; no address is hardcoded in the app.

The next required action is on the Windows laptop: enable Ableton's audio engine
and deliberately hear or meter the bounded preview synth. Then use the browser
controls during a longer real run to confirm that live tonality-lens and
raw/interpreted pitch-blend edits are audible on subsequent tokens.

The scope remains observation and mapping of existing Gemma/SAE fields. Do not
expand `/rai/v1` or add discovery/pairing until the current audio path is heard
and the desired Ableton parameter-mapping matrix is specified.

### Later local and integration work

1. On the Windows laptop, open the existing Max-generated
   `max/rai_osc_receiver/RAI OSC Receiver.amxd` in Ableton and enable a deliberate
   audio output. Rerun the loopback fixture and hear/meter the bounded preview;
   do not infer audio success from OSCQuery state alone.
2. Recheck the Windows LAN address before each performance session because DHCP
   can change it.
3. Run a longer real app session and confirm live lens/blend edits affect
   subsequent audible Ableton notes.
4. If transport needs to be isolated again, rerun
   `uv run python -m scripts.send_osc_test --host <current-windows-ipv4> --port 9000`
   and verify the result through the receiver panel or OSCQuery.
   Create no firewall rule unless the existing Ableton rule proves insufficient
   and the user approves an exact proposed rule.
5. Decide the master-clock policy during Phase 5C; do not add Link or
   quantization in Phase 5B.
6. Keep generated caches, papers, references, runs, and screenshots untracked
   unless the user explicitly asks to save them in Git.
