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

Agent workflow clarification: use Codex for planning, implementation, review, and
remote-machine coordination. Do not assume Anthropic/Claude tooling for agentic
project work.

## Machine Topology

- **Ubuntu GPU PC** (current implementation target): runs Gemma/SAE inference,
  FastAPI, the browser interface, and the planned outbound OSC emitter.
- **Windows laptop**: runs Ableton Live, Max for Live, and ossia; it will host a
  separate Max/ossia receiver task.
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

1. On the Windows laptop, implement the separate Max for Live/ossia receiver
   that consumes the `/rai/v1` contract in `specs/ableton-osc-bridge.md`.
2. After that receiver works locally, run the Phase 5C two-machine LAN check and
   confirm live lens/blend edits affect subsequent Ableton notes.
3. Decide the final Windows LAN address, firewall rule, receiving port, and
   master-clock policy during the two-machine integration task.
4. Keep generated caches, papers, references, runs, and screenshots untracked
   unless the user explicitly asks to save them in Git.
5. Keep each implementation step small and verifiable.
