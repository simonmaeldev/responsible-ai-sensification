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

Implement only the requested task. Keep changes scoped. Run the smallest useful verification. Update project state if the result changes future work. Do not commit unless asked.

Spec/task:
[paste path or task]
```

## Review Mode

Use after implementation or before committing.

```text
Review the current diff as a code reviewer. Prioritize bugs, regressions, missing tests, and scope drift. Lead with findings and file/line references. If no issues are found, say so and note residual test gaps.
```

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
