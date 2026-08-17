# Agent Prompt Templates

Use these as lightweight prompts when starting a new agent session or task.

## Clarify Mode

Use when the user has an idea but implementation details are still unclear.

```text
Read AGENTS.md, docs/agentic/PROJECT_STATE.md, and docs/agentic/WORKFLOW.md.

Execution machine: [Ubuntu GPU PC | Ubuntu laptop | Windows laptop]
State the selected machine before proceeding. If it is unknown, ask before
making changes.

We are clarifying a new task before coding. Ask focused questions until the task is specific enough to write a short implementation spec. Keep questions grouped and practical. Do not edit app code.

User request:
[paste request]
```

## Spec Mode

Use when the idea is understood and should become a scoped implementation note.

```text
Read AGENTS.md, docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md, and any relevant specs.

Execution machine: [Ubuntu GPU PC | Ubuntu laptop | Windows laptop]
If another machine is involved, name it separately as the destination and state
which machine is in scope.

Create or update a focused spec for this task. Include goal, non-goals, affected files, implementation outline, verification plan, and open questions. Do not implement yet unless explicitly asked.

Task:
[paste task]
```

## Implement Mode

Use only after a task/spec is clear.

```text
Read AGENTS.md, docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md, and the task spec.

Execution machine: [Ubuntu GPU PC | Ubuntu laptop | Windows laptop]
Confirm the selected machine and do not imply that local commands changed any
other machine.

Implement only the requested task. Use test-driven development by default and
keep changes scoped. Run focused and complete relevant verification, update
project state when the result changes future work, and create a focused commit
after the slice is green. Do not push or perform branch/history operations
unless explicitly requested.

Spec/task:
[paste path or task]
```

## Review Mode

Use after implementation or before committing.

```text
Review the current diff as a code reviewer. Prioritize bugs, regressions, missing tests, and scope drift. Lead with findings and file/line references. If no issues are found, say so and note residual test gaps.
```

## Ossia Score Interface: Sequential Runbook

This is a recovery and handoff sequence for `specs/ossia-score-interface.md`.
The preferred workflow is to keep working in one Codex thread and say
`Continue with ossia score interface phase N`. In a new thread, paste the
corresponding prompt below.

Run only one phase at a time. Move to the next phase only when the current
agent reports:

- every required focused and complete check passed;
- the manual score acceptance check passed, or the exact blocker is recorded;
- project state reflects only observed results;
- a focused commit was created and its hash was reported;
- the worktree has no unexplained changes.

If any gate fails, stay on that phase. Do not use the next prompt to work around
an unresolved failure. A push is never required to advance on the same clone.

### Phase 1 Prompt: WebSocket Device Vertical Path

```text
Execution machine: Ubuntu GPU PC. Work only in this repository and do not
change the Windows receiver or any external connector contract.

Read AGENTS.md, docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md,
docs/agentic/ROADMAP.md, specs/TODO.md, and
specs/ossia-score-interface.md completely. Confirm the branch and inspect the
existing /ws/stream contract before editing.

Implement only Slice 1 from specs/ossia-score-interface.md using test-driven
development. Create the score WebSocket device adapter under
ossia/rai_workbench/. It must connect to the existing FastAPI endpoint, expose
the specified fixed address tree, translate deterministic ready/loading/token/
done/stopped/error events, and send prompt/start/stop actions. Do not build the
custom interface yet and do not change server behavior unless a failing
contract test proves it necessary.

First verify deterministic events, then exercise one short real Gemma/SAE run
through installed score 3.8.2. Keep the browser as the reference and use only
one run controller at a time. Run focused checks and the complete relevant
suite, inspect the diff, update state/roadmap with observed results, and create
one focused commit. Do not push.

Stop instead of proceeding if score 3.8.2 cannot load the WebSocket adapter or
represent a required value. Report the exact API/runtime limitation and the
smallest alternatives.
```

Advance to Phase 2 only when score can start and stop a real run and its device
tree shows connection, loading, exact token, model/layer, feature, and terminal
state without QML errors.

### Phase 2 Prompt: Minimal Custom Interface

```text
Execution machine: Ubuntu GPU PC.

Read the required startup documents and specs/ossia-score-interface.md. Verify
that Phase 1 has a passing commit and re-run its focused smoke check before
editing.

Implement only Slice 2 with test-driven development. Add a custom QML interface
and a score-generated rai-workbench.score document under ossia/rai_workbench/.
The interface must provide prompt, Run, Stop, connection/loading/error state,
the exact current token and token ID, and the twelve strongest SAE features
with exact activation and available Neuronpedia descriptions. Use --ui-debug
during development and document both debug and normal launch commands.

Do not add the model block grid, probe rack editor, raw residual arrays, native
ONNX inference, or external connector changes in this phase. Verify deterministic
events and one short real model run, inspect score logs for QML/binding errors,
run complete relevant checks, update durable docs, and create one focused
commit. Do not push.
```

Advance to Phase 3 only when the custom score interface alone can control and
observe a real run and agrees with the browser reference for token and feature
evidence.

### Phase 3 Prompt: Research Observation Views

```text
Execution machine: Ubuntu GPU PC.

Read the startup documents and specs/ossia-score-interface.md. Confirm Phases 1
and 2 are green before editing.

Implement only Slice 3 using test-driven development. Extend the score-native
interface with the real Gemma block map, selectable dense observation layer,
visibly fixed SAE layer, selectable token history, and eight bounded probe
summaries. Preserve exact model, token, site, layer, module path, shape, and
representation provenance. Keep raw vectors local and do not imply semantic
distance from dense coordinates or SAE feature indices.

Preserve the minimal interface and existing browser/backend behavior. Verify
deterministic history selection, live layer/probe changes on subsequent tokens,
and a real GPU run against the browser reference. Run all relevant checks,
update durable docs, and create one focused commit. Do not push.
```

Advance to Phase 4 only when current and historical token evidence stays
synchronized and live probe/layer edits affect the expected subsequent token.

### Phase 4 Prompt: Patchable Score Observations

```text
Execution machine: Ubuntu GPU PC.

Read the startup documents and specs/ossia-score-interface.md. Confirm the
score-native observation interface is green before editing.

Implement only Slice 4 using test-driven development. Make a deliberately
selected set of scalar token, residual, probe, and SAE observations available
to normal score processes. Add one small removable example mapping that proves
score can transform an observation without changing its raw value or assigning
artistic meaning in the transport layer.

Do not expand OSC v1, OSCQuery, the Windows receiver, or raw vector transport.
Verify the example with deterministic data and one real run, document how to
replace or remove it, run all relevant checks, update durable docs, and create
one focused commit. Do not push.
```

Advance to Phase 5 only when a normal score process demonstrably reacts to a
real scalar observation and the raw/provenance display remains unchanged.

### Phase 5 Prompt: Native Inference Decision Gate

```text
Execution machine: Ubuntu GPU PC. This is an investigation and decision task,
not authorization to port inference.

Read the startup documents, specs/ossia-score-interface.md, the completed score
prototype, current ossia score source, and current score-addon-onnx source.
Reconfirm installed, continuous, add-on, ONNX Runtime, CUDA, and SDK versions.

Evaluate whether exact google/gemma-3-1b-pt inference plus the matching layer-22
Gemma Scope 2 SAE can move into a native score/Avendish process while preserving
token IDs, prompt semantics, residual values, active SAE indices/activations,
Neuronpedia lookup, cancellation, one-token backpressure, and GPU performance.
Ask before downloading large models, installing dependencies, or creating a
new source build.

Produce a concise evidence-backed decision record with measured gaps and a
recommendation: keep the backend, add an Avendish bridge, or write a native
ONNX process. Do not implement the selected route. If native work is justified,
write a new focused spec for user approval. Update durable docs and commit only
documentation produced by this decision task. Do not push.
```

The sequence stops after Phase 5. Native inference requires a new approved spec;
there is intentionally no automatic Phase 6 prompt.

## Ubuntu GPU PC: Implement Ableton OSC Emitter

Use this prompt in a new task running against the repository clone on the Ubuntu
GPU PC. It intentionally excludes the Windows Max for Live receiver.

```text
Execution machine: Ubuntu GPU PC.
Destination machine: Windows laptop running Ableton Live, Max for Live, and ossia.
In scope in this task: Ubuntu GPU PC emitter only. Do not implement or claim to configure the Windows receiver.

Read AGENTS.md, docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md,
docs/agentic/ROADMAP.md, specs/TODO.md, and specs/ableton-osc-bridge.md completely.
At the start of your response, explicitly confirm that commands and edits are on
the Ubuntu GPU PC and that the Windows laptop is only the network destination.

Implement Phase 5A from specs/ableton-osc-bridge.md end to end:

- Add optional, disabled-by-default OSC output controlled live from the browser.
- Make destination host, UDP port, and maximum notes per token configurable and
  persistent using the existing UI/session conventions; never hardcode an IP.
- Emit the documented /rai/v1 lifecycle, token, bounded note, tonality, and live
  control messages from the final post-tonality event data.
- Preserve the existing WebSocket event, browser visualization, and Web Audio path.
- Keep OSC errors non-fatal and represent UDP status honestly (configured/sending,
  not "connected" without a handshake).
- Add focused Python tests, run the full server suite, syntax-check main.js, and
  verify the sender with a loopback OSC receiver on this Ubuntu GPU PC.
- Update PROJECT_STATE.md and ROADMAP.md only to reflect what was actually completed.
- Do not commit, push, switch branches, create worktrees, or edit outside this repo.

Inspect the current implementation before editing and follow existing FastAPI,
dataclass, vanilla-JavaScript, and test styles. If implementation reality conflicts
with the spec, stop and explain the exact conflict instead of silently changing the
OSC contract. Finish with changed files, verification results, and the exact
remaining Windows-laptop receiver task.
```

## Windows Laptop: Finish Receiver And Two-Machine Check

Use this after pulling the synchronized emitter, receiver, and LAN fixture from
`nicolas-attempts`. It intentionally defers the larger semantic mapping matrix.

```text
Execution machine: Windows laptop.
Remote runtime source: Ubuntu GPU PC.
In scope: finish Phase 5B local Max for Live verification, then exercise the
Phase 5C UDP path. Do not expand the OSC contract or semantic mapping system.

Pull the latest nicolas-attempts and read AGENTS.md,
docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md,
docs/agentic/ROADMAP.md, specs/ableton-osc-bridge.md,
specs/ableton-osc-receiver.md, and max/rai_osc_receiver/README.md completely.
Confirm commands and edits run on the Windows laptop.

1. Open max/rai_osc_receiver/RAI OSC Receiver.maxpat through Live's Edit in Max
   workflow and save a Max-generated RAI OSC Receiver.amxd. Do not create or
   rename an .amxd by hand.
2. Keep or freeze the JavaScript, voice, panel, and ossia dependencies correctly.
3. In the Live-hosted Max environment, rerun the Windows loopback fixture,
   query http://127.0.0.1:5679/, and verify the preview is audible and bounded.
4. Recheck the Windows LAN IPv4 and active firewall profile. Do not create or
   modify a firewall rule without reporting the exact proposed rule and getting
   approval.
5. Keep the receiver open on UDP 9000 and ask the user to run this on Ubuntu:
   uv run python -m scripts.send_osc_test --host <current-windows-ipv4> --port 9000
6. Verify both token frames, two notes in the final frame, final frequency
   445.125 Hz, BPM 96, sustain mode, control changes, done, silent, and stop.
7. Only after the fixture passes, test the real Ubuntu browser emitter using the
   same Windows IP and UDP port. Confirm live raw/interpreted blend and tonality
   lens edits change subsequent received frequencies.
8. Keep local loopback, LAN reception, and audible Ableton results as separate
   claims. UDP sending alone is not proof of reception.

Update PROJECT_STATE.md and ROADMAP.md only with observed results. Do not commit,
push, switch branches, create worktrees, or edit outside the repository unless
explicitly asked. Finish with exact verification evidence and remaining gaps.
```
