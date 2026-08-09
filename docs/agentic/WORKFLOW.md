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
   - Define tests, smoke checks, or manual checks before implementation.
   - Repeat important negative constraints directly in the task.

6. Red
   - Test-driven development is the default for implementation work.
   - Add or extend the smallest automated test that expresses the requested
     behavior, then run it and confirm that it fails for the intended reason.
   - For behavior that cannot reasonably be automated, write down the manual
     acceptance check before changing the implementation.

7. Green And Refactor
   - Make only the smallest in-scope change required to pass the new test.
   - Preserve existing code style and architecture, and do not implement
     unrelated ideas discovered during exploration.
   - Refactor only while the focused tests remain green.

8. Verify
   - Run the focused tests and the complete relevant suite.
   - Report what was run and what could not be run.
   - Update state docs if the result affects future work.

9. Save Point
   - Inspect the diff and staged paths, then automatically create a focused
     commit for each coherent, completed, verified change.
   - Do not commit unrelated user changes or known failing behavior.
   - Do not push, switch branches, rebase, or create worktrees unless the user
     explicitly requests that separate operation.

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
  The Emitter may expose arbitrary raw or derived probe data; Gemma Scope, SAE,
  Neuronpedia, tonality, audio, and visual mappings are current experiments, not
  a closed list. Establish discoverable signals without requiring them to have
  a predetermined artistic interpretation.
- Keep four epistemic distinctions explicit in implementation and language:
  observation of raw runtime state, interpretation with evidence/provenance,
  optional artistic transformation, and optional external routing. They do not
  require one visible tab each. The current focused UI uses **Model** and
  **Map** as its only primary destinations. Controls and Tonality are on-demand
  drawers, and OSC is a compact popover. A value must not be presented as raw
  if it came from a projection, description, or mapping.
- Every live model view should identify the model/session, observation site,
  token or training step, and representation type. Do not imply semantic
  distance from coordinate or feature-index proximity unless a documented
  projection establishes it.
- Connectors should preserve access to selected raw data when technically
  feasible. Selection, serialization, chunking, and rate limits may be needed
  for a transport, but artistic transformations may instead be created by a
  Receiver.
- Use a separate clone on each computer. Use separate branches when both sides
  are being developed concurrently, and merge through Git after each side is
  independently understandable.
- Do not use Git as the live transport. Use OSC/OSCQuery over the LAN for runtime
  messages.
- Treat libossia as a candidate Connector namespace/discovery layer, not as the
  model-exploration UI. Treat Interpreto as a candidate interpretation adapter,
  not as proof of live training support. Both need a focused spec and real
  backend evidence before user-facing claims.

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

Begin behavior changes with a failing focused test, then use both focused and
complete relevant checks for confidence:

- Python server behavior: `cd app/server && uv run pytest`
- UI behavior: run `./scripts/start.sh`, then manually or browser-test the relevant workflow.
- Streaming/model behavior: expect HuggingFace/model cache/API constraints and document what was or was not exercised.
- Cross-machine OSC behavior: first verify the Ubuntu sender against a loopback
  receiver; verify Ableton/Max reception separately on Windows; then run one LAN
  integration check with both machines named in the report.
- Documentation-only changes: inspect the complete diff, run `git diff --check`,
  and confirm that linked workflow/state documents remain consistent. Do not
  invent a code test merely to claim test-driven development.

## No-Code Discussion Mode

When the user says not to code yet:

- Do not edit app implementation files.
- It is okay to inspect files and update planning/workflow docs if asked.
- Summarize options and decisions instead of writing feature code.
