# Agentic Workflow

This workflow is adapted for this repository from the local PDF:

`/home/apaixonada/Downloads/Mila Community Agentic Coding Best Practices (1).pdf`

The goal is to make agent work persistent, scoped, and easy to restart without losing the project thread.

## Core Loop

1. Locate
   - Name the execution machine: Ubuntu GPU PC, Ubuntu laptop, or Windows laptop.
   - If the task crosses machines, name the source, destination, and in-scope side.
   - Confirm that required hardware/software exists on the selected machine.

2. Explore
   - Read the relevant files instead of relying on memory.
   - Record durable findings in `docs/agentic/PROJECT_STATE.md` when they matter for future work.

3. Clarify
   - For ambiguous or research-heavy changes, ask focused questions before coding.
   - Capture decisions in a spec, roadmap item, or state note.

4. Plan
   - Turn a large idea into a short spec or phased checklist.
   - Keep each implementation unit small enough to review and verify.

5. Constrain
   - Identify exact files likely to change.
   - Define tests, smoke checks, or manual checks before implementation when possible.
   - Repeat important negative constraints directly in the task.

6. Implement
   - Make only the changes required by the current task.
   - Preserve existing code style and architecture.
   - Do not implement unrelated ideas discovered during exploration.

7. Verify
   - Run focused tests or checks immediately.
   - Report what was run and what could not be run.
   - Update state docs if the result affects future work.

8. Save Point
   - Ask the user before committing.
   - Keep Git status understandable between tasks.

## Multi-Machine Work

- Start by naming the logical role in scope: Emitter, Connector, or Receiver.
  Roles are portable responsibilities and may be implemented by different
  applications, protocols, and machines in future setups.
- Ubuntu GPU PC: Gemma/SAE inference, FastAPI, browser UI, OSC emission, and
  server-side automated tests. It is the current Emitter host.
- Windows laptop: Ableton Live, Max for Live, ossia receiver, Live API mapping,
  and audible end-to-end validation. It is the current Receiver host.
- Ubuntu laptop: browser/control use and lightweight work unless the user assigns
  a different role; never assume a GPU.
- A Connector is the transport boundary between an Emitter and Receiver, not a
  synonym for either machine. Current external transport is OSC v1; the browser
  WebSocket is an internal emitter transport.
- Emitter work must run and be observable locally with external connectors off.
  Establish named emitter controls before deciding which controls a connector
  should carry or how a receiver should apply them.
- Use a separate clone on each computer. Use separate branches when both sides
  are being developed concurrently, and merge through Git after each side is
  independently understandable.
- Do not use Git as the live transport. Use OSC/OSCQuery over the LAN for runtime
  messages.

## Agent Tooling

Use Codex for this workflow. Do not rely on Anthropic/Claude-specific commands,
memory files, or agent conventions. If older docs or code mention Claude or
Anthropic, treat that as legacy project context rather than the active workflow.

## Planning Files

- `AGENTS.md`: persistent instructions for future coding agents.
- `docs/agentic/PROJECT_STATE.md`: current state, open decisions, and recent handoff notes.
- `docs/agentic/ROADMAP.md`: phased plan for upcoming work.
- `docs/agentic/PROMPTS.md`: reusable prompts for clarify, implement, and review modes.
- `specs/`: task-level implementation specs and bug reports.

## When To Ask Before Coding

Ask before implementation when:

- The user is still brainstorming.
- The term paper/design source has not been added yet.
- The UI goal could be interpreted in multiple ways.
- The change affects architecture, data persistence, model loading, or generated artifacts.
- A dependency, API key, or external service is required.

## When To Proceed Directly

Proceed directly when:

- The user gives a specific implementation task.
- The affected area is obvious and scoped.
- Existing specs/tests define the expected behavior.
- Verification can be run locally.

## Context Hygiene

- Prefer focused file reads over dumping large files into context.
- Link plans to file paths instead of duplicating code.
- Periodically summarize completed discoveries into `PROJECT_STATE.md`.
- Keep inactive external material in ignored folders such as `references/`.

## Verification Expectations

Use the smallest check that gives confidence:

- Python server behavior: `cd app/server && uv run pytest`
- UI behavior: run `./scripts/start.sh`, then manually or browser-test the relevant workflow.
- Streaming/model behavior: expect HuggingFace/model cache/API constraints and document what was or was not exercised.
- Cross-machine OSC behavior: first verify the Ubuntu sender against a loopback
  receiver; verify Ableton/Max reception separately on Windows; then run one LAN
  integration check with both machines named in the report.

## No-Code Discussion Mode

When the user says not to code yet:

- Do not edit app implementation files.
- It is okay to inspect files and update planning/workflow docs if asked.
- Summarize options and decisions instead of writing feature code.
