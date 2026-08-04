# Project State

Last updated: 2026-08-03

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

Phase 5B is in progress on the Windows laptop. A textual Max for Live receiver
source, exhaustive `/rai/v1` state engine, bounded 16-voice preview synth,
ossia/OSCQuery configuration/status namespace, and Windows loopback sender now
exist under `max/rai_osc_receiver/`. Static checks, deterministic contract tests,
and real UDP traffic into Max Runtime pass. The final Ableton-hosted `.amxd`,
OSCQuery query, and audible Live check still require opening/saving the source
through Live's **Edit in Max** workflow.

Agent workflow clarification: use Codex for planning, implementation, review, and
remote-machine coordination. Do not assume Anthropic/Claude tooling for agentic
project work.

## Machine Topology

- **Ubuntu GPU PC**: runs Gemma/SAE inference, FastAPI, the browser interface,
  and the completed outbound OSC emitter.
- **Windows laptop**: runs Ableton Live, Max for Live, and ossia; it will host a
  separate Max/ossia receiver task. It is the current Phase 5B implementation
  and verification target.
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
- Max Runtime does not discover separately installed user packages, so it could
  not expose the ossia namespace. The Live-hosted Max editor must perform the
  final OSCQuery and audio checks; no Ableton audio or two-machine LAN pass is
  claimed yet.

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
- Final Windows LAN address/ports and whether Ableton or the app should be the
  master clock for the first two-machine performance test.

## Handoff Notes

Before coding next:

1. On the Windows laptop, open `max/rai_osc_receiver/RAI OSC Receiver.maxpat`
   through Live's **Edit in Max** workflow, save the Max-generated
   `RAI OSC Receiver.amxd`, and keep its JavaScript/voice dependencies beside it
   or freeze the device.
2. In the Live-hosted editor, confirm the ossia namespace at
   `http://127.0.0.1:5679/`, rerun the loopback fixture, verify all published
   states, and perform the first audible bounded-preview check.
3. Only after that local host check passes, run the Phase 5C two-machine LAN
   check using Windows IPv4 `192.168.1.208` and UDP 9000, and confirm live
   lens/blend edits affect subsequent Ableton notes.
4. Recheck the Windows LAN address before Phase 5C because DHCP can change it.
   Create no firewall rule unless the existing Ableton rule proves insufficient
   and the user approves an exact proposed rule.
5. Decide the master-clock policy during Phase 5C; do not add Link or
   quantization in Phase 5B.
6. Keep generated caches, papers, references, runs, and screenshots untracked
   unless the user explicitly asks to save them in Git.
