# Project State

Last updated: 2026-08-11

## Branch

Current branch: `nicolas-attempts`

This branch was created from `main` for Nicolas's work. Confirm the branch before any implementation session:

```bash
git branch --show-current
```

## Current Mode

Implementation is active on a general GPU-hosted Emitter for inspecting and
sensifying model/runtime data. The current Gemma 3, Gemma Scope, SAE,
Neuronpedia, semantic-tonality, browser audio, and visualization system is a
substantial proof of concept, not the definition or limit of the Emitter.

The browser now has two primary destinations: **Model** and **Map**. The
inference prompt and transport remain continuously visible; OSC is a compact
optional output popover. Model is the default and makes the loaded Gemma path,
selected transformer block, token, and provenance primary. Map owns probe
evidence and mapping. Run/signal controls and verbal Tonality are mutually
exclusive, closed-by-default drawers. Dense/sparse representations and the full
mapping matrix are closed disclosures. Observation, interpretation,
transformation, and routing remain important provenance distinctions, but they
do not create permanent screen regions.

Dense observation is now independent of the SAE attachment. The live
`observation_layer` parameter can move residual probes across all advertised
transformer blocks on subsequent tokens, while Gemma Scope continues to encode
the residual from its actual trained layer. WebSocket token events identify both
locations. The interface does not claim semantic geometry for neighbouring
dense dimensions or SAE feature indices.

Model now supports real token traversal through the full Gemma decoder. An
optional `model.layer_profile` captures a compact final-position residual
summary at every block in one forward pass: magnitude, peak, adjacent-block
update magnitude, and cosine similarity. The browser renders measured activity
across all 26 blocks, previous/next/direct navigation, the loaded model's real
local-versus-global attention pattern, and the selected Gemma block's RMSNorm,
self-attention, residual, gated-MLP, and residual path. Only the selected block's
complete 1,152-value residual is sent; the SAE remains fixed at its trained
layer and no semantic geometry is inferred.

The semantic-tonality experiment remains available under Tonality. Verbal
descriptions and active SAE feature descriptions share the MiniLM space, and
each live lens now combines a conventional root key, a scale preset or custom
interval set, and a free verbal description. The selected root is preserved by
the backend and transposes the actual pitch target.

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

The emitter now has a canonical, receiver-independent control bus. Each token
can expose 18 raw/normalized Gemma Scope, SAE, Neuronpedia-coverage, cluster,
semantic-tonality, pitch, and generation signals. A live mapping matrix turns
them into 14 bounded browser audio/visual targets without modifying raw feature
evidence or final post-tonality notes.

The in-place probe catalogue is complete. A generic ordered registry
describes 27 signals across model residuals, model logits, SAE activations,
Neuronpedia coverage, clusters, semantic experiments, final pitches, and
generation timing. The original 18 mapping sources remain compatible; five
lightweight model summaries are available as scalar mapping sources; and full
residual vectors, top-k logits, and sparse SAE feature streams are explicit
opt-in raw signals. The browser workbench enables the residual-vector and sparse
SAE streams on startup so its primary views have real data; they can still be
disabled through Map's Controls drawer. Live selection affects subsequent tokens without
extending OSC v1 or requiring an artistic transformation.

Emitter preparation now has structured browser feedback. A compact progress
panel reports the language model, SAE, Neuronpedia descriptions, feature
organization, semantic tonalities, and first-token generation as distinct
stages, including honest cached, downloaded, skipped, complete, and error
states. The panel dismisses when live tokens begin and does not change the
model, browser-audio, WebSocket, OSC, or Receiver contracts.

## Emitter, Connector, Receiver

- **Emitter:** observes arbitrary model/runtime probes and makes selected raw or
  derived data locally inspectable. Artistic interpretations and mappings are
  optional. It can be any compatible runtime; the current emitter is FastAPI
  plus the browser GUI on the Ubuntu GPU PC.
- **Connector:** transports selected emitter events and controls without
  defining their artistic meaning. It may select, serialize, rate-limit, chunk,
  or adapt data as technically required by a transport, while preserving raw
  access where feasible. Current external communication uses `/rai/v1` OSC,
  while the emitter browser uses an internal WebSocket.
- **Receiver:** consumes connector data and may perform its own transformations
  on raw signals or apply already-derived controls. It can be Ableton,
  TouchDesigner, ossia, another browser, hardware, or another system; the
  current receiver is the Windows Max for Live/ossia device.

These roles may move between processes or machines. New emitter capabilities
must be usable locally before a connector contract or receiver mapping is added.

Agent workflow clarification: use Codex for planning, implementation, review,
and remote-machine coordination. Test-driven development is expected by
default: establish a failing behavioral test before implementation, then run
focused and complete relevant suites. After a coherent change is verified,
Codex creates a focused commit automatically so development history stays easy
to follow. Commits do not authorize pushes or branch/history operations. Do not
assume Anthropic/Claude tooling for agentic project work.

## Machine Topology

- **Ubuntu GPU PC**: runs Gemma/SAE inference, FastAPI, the Emitter workbench,
  optional local transformation experiments, and outbound OSC implementation.
- **Windows laptop**: runs Ableton Live, Max for Live, and ossia; it hosts the
  current receiver and remains the audible-output verification target.
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
- Added the receiver-independent GPU emitter mapping instrument. The browser now
  separates Source, Tonality, Mappings, and Connector controls; exposes 18 raw
  and normalized signal types and 14 bounded browser targets; and includes
  activation, semantic, and sparse-detail templates.
- Added browser-audio mappings for gain, pitch, note density, duration, timbre,
  pan, filter/resonance, and delay, plus visual energy, hue, motion, and
  activation-bar scale.
- Added a searchable live SAE/Neuronpedia feature browser with raw/interpreted
  frequency, activation, cluster, instrument, pin, mute, and solo controls.
- Added local instrument scenes with save/recall and A/B morphing. Scenes capture
  mappings, tonal lenses, prompt/pitch interpretation, volume, and local feature
  audition state.
- Expanded the live lens editor with enable/disable, duplicate, reorder, remove,
  reset, and honest MiniLM embedding status. A real cached-model smoke test
  reported `embedding` then `1 embedded`, excluded a disabled lens, and selected
  the edited `glass current` lens for both following tokens.
- Verified a live mapping edit without restarting generation: three real
  Gemma/SAE tokens each exposed all 18 signals and used the newly selected
  `feature.top_share` to `audio.pan` mapping. The complete server suite now
  passes with 60 tests, the 95-ID browser DOM harness passes, and JavaScript
  syntax checks pass.
- Added the general Emitter signal registry and API. It preserves the original
  18 scalar mapping keys while adding residual-stream and output-logit scalar
  summaries plus opt-in raw residual, top-k logit, and sparse SAE streams.
- Added live, validated `emitter_signal_keys` session selection. The model probe
  callback resolves the current selection on every generation step, so browser
  changes affect subsequent tokens; enabled mappings continue to compute their
  required scalar source even when it is hidden from the monitor.
- Added the in-place Signals tab with searchable/grouped Available probes,
  active checkboxes, raw/derived and cost metadata, live previews, mapping-route
  counts, and explicit Connector `Not routed` status. No OSC v1 message or
  Windows Receiver behavior changed.
- Moved the cluster/color visualization behind a compact, closed-by-default
  **Visual mapping — Proof of concept** disclosure. The existing visualization
  remains functional when revealed while the tonality/waveform workspace gets
  the primary live area.
- Verified the completed slice with 68 passing server tests,
  `node --check app/client/main.js`, and the 104-ID browser DOM/behavior harness,
  including a live WebSocket selection payload. The application started and
  stopped successfully. A new screenshot was not captured because this host's
  Firefox command is an uninstalled Snap placeholder and no Chromium/Playwright
  browser is installed; no system package was installed as a workaround.
- Verified the new probe path with a real one-token Gemma 3 1B/SAE GPU run and
  OSC disabled. Token ` to` carried all five selected scalar model summaries, a
  raw residual vector with shape `[1152]`, eight top-logit records, and 52
  sparse active SAE features in the production WebSocket payload.
- Added structured Emitter preparation feedback with six stable stages, a
  compact progress bar and stage badges, local-cache/download distinctions,
  first-token dismissal, and a persistent error presentation.
- Verified the loading path with 70 passing server tests, the 109-ID browser
  DOM/behavior harness, JavaScript syntax checking, and a real one-token
  Gemma/SAE GPU run. The production WebSocket emitted all 12 active/completion
  transitions in order, reported 64,751 Neuronpedia descriptions from local
  cache, reached 100%, delivered token 1, and hid the preparation panel. A
  desktop loading-state screenshot was inspected and the server was stopped.
- Replaced the instrument-first browser shell with a prompt-first Emitter
  workbench organized as Observe, Interpret, Transform, and Route. Semantic
  tonality and colour are no longer the default or dominant views.
- Added truthful Gemma architecture metadata and an independent live
  `observation_layer`. Dense residual probes can move through all 26 Gemma 3 1B
  blocks while the 65k SAE remains visibly attached to layer 22. Invalid probe
  layers are bounded without stopping generation.
- Added focusable Structure, Dense state, and Sparse state views. Dense cells
  are actual signed residual coordinates with min/max/RMS/peak statistics;
  sparse marks are actual active feature indices/activations with Neuronpedia
  descriptions where present. The UI states that layout/index proximity is not
  semantic proximity.
- Expanded each semantic-tonality lens with a conventional root-key selector,
  named scale presets, and custom intervals. Root pitch class now travels
  through coercion, embedding cache, matches, token payloads, and pitch bias.
- Verified the redesign with 75 passing server tests, JavaScript syntax
  checking, and the 128-ID browser DOM/behavior harness. Headless Chromium found
  no console/page errors across Observe, dense, Transform, and Route.
- Ran a real Gemma 3 1B GPU smoke test with dense observation at layer 7 and the
  SAE at layer 22. The live browser rendered 1,152 residual coordinates and 48
  active SAE features out of 65,000 for token ` of`, with no browser error. The
  server was stopped after screenshots were captured.
- Added the second neural-workbench slice: runtime-derived Gemma structure,
  optional all-block residual profiling, measured layer activity bars,
  previous/next/direct block traversal, and an explicit selected-block diagram.
  Profile math is vectorized to avoid repeated per-block GPU synchronization;
  full dense data is still captured only for the selected block.
- Verified the traversal slice with 77 server tests, `node --check`, the 137-ID
  browser DOM/behavior harness, and a real Gemma 3 1B GPU/browser run. The run
  reported 26 structure/profile rows, a 1,152-value layer-7 residual, RMS
  `67.5254`, update RMS `7.8591`, and adjacent-layer cosine `0.9970`. Headless
  Chromium rendered the live diagram with no page errors and captured
  `runs/emitter-gemma-traversal-live.png`; the server was stopped afterward.
- Replaced the crowded four-stage and nested-atlas navigation with exactly three
  direct views: Model, Signals, and Tonality. Maël Simon's prompt-first
  directness is retained without restoring the older archive implementation.
  OSC remains available through a compact header popover.
- Recast the Model view as one continuous, clickable Gemma residual path from
  token embedding through all 26 real blocks to logits. The latest measured
  layer-update profile is a mathematical trace over the path; local/global
  attention, the movable dense probe, and fixed Gemma Scope 2 SAE are distinct.
  The selected block, dense residual trace, and sparse features are visible
  together rather than hidden behind nested tabs.
- Expanded Tonality into a dedicated editing surface for verbal descriptions,
  roots, scale presets, and custom intervals beside the live match, evidence,
  output intervals, and waveform. Colour remains collapsed as a proof of
  concept. Opening any workspace now resets its content viewport to the top.
- Verified the focused correction with 77 passing server tests, JavaScript
  syntax checking, and the 140-ID browser DOM/behavior harness. A real one-token
  Gemma 3 1B/Gemma Scope 2 GPU run selected block 7, measured all 26 blocks,
  rendered a 1,152-value dense residual and 54 active layer-22 SAE features, and
  updated Tonality with no browser errors. Inspected screenshots were captured
  at `runs/gemma-focused-{model,signals,tonality}-live.png`; the server was
  stopped afterward.
- Replaced the three permanent workspaces and persistent control sidebar with
  two primary destinations, Model and Map. Controls and Tonality now open as
  mutually exclusive drawers; workspace changes, close buttons, the backdrop,
  and Escape return to the primary surface.
- Put dense/sparse inspection and the full mapping matrix behind
  closed-by-default disclosures. Tonality now shows a compact eight-lens
  accordion with one editor open while preserving live enable, edit, reorder,
  duplicate, remove, root, preset, custom-interval, and re-embedding behavior.
- Verified the decluttered interface with 77 server tests, JavaScript syntax,
  the 149-ID browser harness, and headless drawer/disclosure checks. The model
  path was 1,376 px wide at a 1,440 px desktop viewport; mapping rows stayed out
  of layout while closed. A real one-token GPU run measured all 26 blocks,
  selected layer 7, rendered 1,152 dense coordinates and 54/65,000 active SAE
  features, and updated `luminous resolve` Tonality without browser errors.
  Inspected screenshots were captured at
  `runs/emitter-decluttered-{model,map,tonality}-live.png`; the server was stopped.
- Added a passive `/ws/activations` observer endpoint and deterministic replay
  fixture for TouchDesigner/research-tool development without model loading.
  Rich events preserve run/model/observation/SAE provenance and coexist with
  browser delivery plus the established `/rai/v1` OSC sender.
- Preserved TouchDesigner callback/setup material and general OSC inspection
  tools from the older laptop prototype. Deliberately excluded its competing
  unversioned top-K OSC sender, default three-port broadcast, toy Max receiver,
  and always-on bidirectional UDP bus.

## Local Reference Material

`references/` is intentionally ignored by Git.

The directory and `Rai_Report.pdf` were not present in this clone during the
2026-08-06 workbench redesign. Earlier state notes preserve ideas previously
extracted from the report, but a future agent must not claim to have reread the
source unless the user restores it. Treat ignored reference material as optional
background only; do not import from it directly unless asked.

## Current App Direction

Use the workbench interface already present in this repo:

- **Model**: the continuously visible prompt/run controls, one clickable Gemma
  path, movable dense probe, fixed/labelled SAE site, and selected-block
  structure. Dense/sparse details open only when requested.
- **Map**: selected raw and derived observations plus searchable SAE/Neuronpedia
  evidence. Signal selection is in Controls; mapped controls, mappings, and
  scenes open only when requested.
- **Controls drawer**: model/run settings in Model and the signal catalogue in
  Map. It is closed by default and never occupies permanent canvas space.
- **Tonality drawer**: optional live verbal descriptions,
  root/scale/custom-interval editing, resonance evidence, browser waveform, and
  collapsed colour proof of concept. One lens editor is open at a time.
- **OSC output popover**: optional OSC v1 configuration. libossia/OSCQuery is a
  planned—not complete—Connector boundary and is not presented as an app view.
- Generated text, token history, pause/replay buffering, loading stages, browser
  audio, mappings, visualization, WebSocket events, and OSC remain functional.

Avoid reverting to the older archive interface.

## Open Decisions

- Where the user will place the term paper.
- Whether paper passages should become prompts, annotations, comparison units, or all three.
- Which Ableton parameters should follow semantic tonality after the initial
  note/activation bridge: timbre, envelope, density, filter, or brightness.
- What the first TouchDesigner visual mapping should render and whether its
  deliverable should be a `.toe` project or reusable `.tox` component.
- What the first ossia score scenario should orchestrate, and whether automatic
  OSCQuery namespace discovery should follow the verified `/rai/v1` prototype.
- What the first user-facing workflow should be after paper ingestion.
- Whether paper passages should become selectable prompt presets or stay outside
  the app as reference context.
- Whether Ableton or the app should be the master clock for the first
  two-machine performance test.
- Which validated emitter controls should eventually be added to a future
  connector contract; do not assume every internal signal belongs on the wire.
- Which model-family probe adapters and observation sites should be added after
  the selected-layer residual, output-logit, and SAE examples.
- Which bounded binary transport should carry intentionally selected large raw
  arrays if OSC/libossia is unsuitable for them.
- Which libossia object tree, units, ranges, and access modes should form the
  first discoverable Connector namespace. Do not replace the custom model UI
  with libossia; use it to expose deliberately selected parameters.
- Which real Interpreto split points, concept-learning methods, attribution
  methods, datasets, and training checkpoints the researchers want. Do not show
  an Interpreto panel until the backend returns real, provenance-bearing results.
- Where the user will restore the report PDF so implementation claims can be
  audited against the primary source.

## Handoff Notes

### Ubuntu launcher and ossia setup (2026-08-10)

- `./scripts/start.sh` now polls the local HTTP endpoint and opens the Emitter
  in the desktop's default browser once it is ready. `--no-browser` or
  `OPEN_BROWSER=0` preserves an explicit headless workflow, and browser-launch
  failures cannot terminate the FastAPI process.
- The initial Ubuntu audit found neither libossia nor ossia score. The official
  libossia 1.2.4 Linux library is now installed user-locally at
  `~/.local/opt/libossia`, including headers, `libossia.so`, and CMake metadata.
  A compiled C++ smoke test loaded that exact shared library successfully.
- The verified official ossia score 3.8.2 x86-64 AppImage was extracted to
  `~/.local/opt/ossia-score-3.8.2`. `~/.local/bin/ossia-score` launches it, and
  `~/.local/share/applications/ossia-score.desktop` exposes it to the Ubuntu app
  menu. Extraction avoids requiring `libfuse2`, which remains uninstalled
  because this agent session could not answer the interactive sudo prompt.
- The current custom `/rai/v1` OSC sender still does not depend on libossia or
  score. They are local Connector research tools, not Emitter prerequisites;
  the repository's Max receiver and documented Windows installations remain
  separate.
- Verification: the two launcher tests passed, all 79 server tests passed,
  `bash -n scripts/start.sh` and `node --check app/client/main.js` passed, and a
  real desktop start opened the page and established its WebSocket. The server
  was then stopped. `ossia-score --version` reports 3.8.2, and its desktop GUI
  completed a startup smoke test before being stopped. It reported optional NDI
  and JACK services as unavailable; neither blocks the planned OSC experiments.

### Immediate Ubuntu GPU PC emitter handoff

The current verified deliverable is four general Emitter-workbench slices, not a
finished definition of every model probe or research workflow. Start it
with `./scripts/start.sh`; the launcher waits for readiness and opens
`http://127.0.0.1:8080` in the default browser. Use `--no-browser` for a remote
or headless session. Enter a prompt in the large composer, and use **Model**
first with OSC disabled.

Select a Dense observation layer from the slider, previous/next buttons, or
transformer-block map. The path shows the latest token's measured update trace
and local/global attention type. The selected real Gemma decoder block and its
residual metrics appear directly below it. The
teal marker is the movable residual probe; the purple marker is the SAE's actual
attachment and must not be interpreted as moving with it. During generation,
the dense and sparse representations remain visible together. Dense and sparse
raw streams are enabled by the browser workbench on startup; use **Map** to
inspect their values and evidence, or open **Controls** from Map to change the
selection.

Open the **Tonality** drawer when evaluating the optional harmonic experiment:
choose a
root, conventional scale or custom relative intervals, and free verbal
description. Live description/root/interval changes affect subsequent semantic
output without restarting. Browser audio, mapping scenes, A/B morphing, and the
collapsed colour proof of concept are preserved.

Open the **OSC** header popover only when an external destination is wanted. OSC
v1 is available; libossia/OSCQuery is explicitly planned and not implemented.
No model, SAE, or tonality experiment depends on a Connector.

After pressing **Run prompt** (or Play), use the preparation panel at the bottom of the controls to
see whether the model, SAE, Neuronpedia descriptions, feature organization, and
semantic lenses are loading or coming from cache. The panel closes when the
first live token arrives; a preparation failure remains visible with its error.

The color/cluster experiment remains collapsed under Tonality. It is not a
primary model view.

Do not expand OSC or change the Windows receiver merely because a new local
probe or interpretation exists. First determine which signals a research or
artistic workflow actually needs; a later Connector phase can version and
transport the selected subset.

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

The Emitter catalogue can now grow beyond existing Gemma/SAE fields, but the
external contract has not grown with it. Do not expand `/rai/v1` or add
discovery/pairing merely because a signal appears in the Explorer. First hear
the current audio path and deliberately choose which bounded signals belong in
a future Connector contract.

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
7. With the researchers, define one evidence-backed Interpreto adapter slice:
   model/split point, live inference versus dataset/checkpoint source, concept or
   attribution method, and provenance. Implement the adapter before its UI.
8. Specify a small libossia/OSCQuery Connector namespace for deliberately
   selected bounded parameters. Keep dense arrays local or choose a separate
   bounded transport; do not force them into OSC messages.

### Ubuntu laptop conflict-resolution handoff (2026-08-11)

- The laptop's obsolete `3146ba5` prototype was integrated selectively rather
  than discarded wholesale. Passive sparse observation, deterministic replay,
  TouchDesigner callbacks, OSC monitoring, and launcher portability survived.
- `/rai/v1` remains the sole production OSC contract, and
  `max/rai_osc_receiver/` remains the sole Max receiver. The prototype's second
  OSC namespace, default multi-host broadcast, inbound shared-control listener,
  and toy Max patch were removed to avoid competing architectures.
- Use `./scripts/integration-dev.sh replay 250 true` for passive WebSocket host
  work. Use `./scripts/integration-dev.sh osc-fixture <host> <port>` separately
  for the established OSC receiver path.
