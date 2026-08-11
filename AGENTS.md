# Agent Instructions

## Project

This repository is `responsible-ai-sensification`: a research/prototype platform
for inspecting and sensifying data from LLMs and related computational systems.
The current Gemma 3/SAE browser instrument is one proof of concept, not a fixed
definition of which probes, signals, transformations, or artistic outputs the
project may support.

The current working direction is the new browser interface in `app/client/`, backed by the FastAPI server in `app/server/`.

## Required Startup Context

Before making non-trivial changes, read:

- `docs/agentic/PROJECT_STATE.md` for the current state and handoff notes.
- `docs/agentic/WORKFLOW.md` for how planning, implementation, and verification should proceed.
- `docs/agentic/ROADMAP.md` for the current phase breakdown.
- `specs/TODO.md` and any relevant file in `specs/` for existing feature/bug context.

If the user adds a term paper or design document, treat it as the primary design context before proposing implementation.

## Logical Architecture

Treat Emitter, Connector, and Receiver as logical roles, not permanent protocols,
applications, operating systems, or physical computers:

- **Emitter** observes arbitrary probes in a model or related runtime and makes
  selected data available. It may expose raw streams, derived signals, artistic
  interpretations, or mapped controls, but none of the current Gemma Scope,
  SAE, Neuronpedia, semantic-tonality, audio, or visual experiments defines its
  permanent scope. It must remain useful locally without a connector or
  receiver.
- **Connector** transports selected emitter data without owning its artistic
  meaning. It may perform technically necessary selection, serialization,
  rate-limiting, or protocol adaptation, but it should not require signals to
  be artistically interpreted before transport. OSC is one connector;
  WebSockets, OSCQuery, MIDI, files, or other bounded transports may be used
  later.
- **Receiver** consumes connector data and may transform raw signals or apply
  already-derived controls in an external context such as Ableton,
  TouchDesigner, ossia, a browser, or hardware.

In the current setup, the FastAPI/browser application on the Ubuntu GPU PC is
the emitter. Outbound `/rai/v1` OSC is the musical-event connector; the optional
libossia/OSCQuery `/rai` namespace is a separate bounded probe-summary
connector. The Windows Max for Live/ossia device receives `/rai/v1`; no Windows
receiver for the new probe namespace is implemented. Do not make emitter
features depend on a particular connector or receiver. Validate observations
locally before expanding an external transport contract, and keep raw vectors
out of the bounded OSCQuery tree.

## Execution Environment

At the start of every task, explicitly identify the machine where commands and
edits will run. Use one of these names exactly:

- **Ubuntu GPU PC**: primary model-inference and FastAPI machine; owns the
  browser app backend and outbound OSC implementation.
- **Ubuntu laptop**: secondary lightweight development/control machine; do not
  assume CUDA, Ableton, Max, or the same local caches as the GPU PC.
- **Windows laptop**: Ableton Live, Max for Live, and ossia machine; owns the
  Max/ossia receiver and Ableton mappings.

If the target machine is not explicit, clarify it before making changes. For a
task spanning machines, state the source, destination, and which side is in
scope. Never imply that a command run on one machine changed another machine.
Separate computers use separate Git clones and branches; Git worktrees are only
for multiple working directories on the same computer. Git synchronizes source
code, while OSC/OSCQuery carries live performance data between machines.

## Collaboration Mode

- Use Codex as the coding agent/workflow driver. Do not assume Claude Code,
  Anthropic tooling, or Anthropic-specific agent commands for project work.
- The user may want to talk through ideas before coding. If they say not to code yet, only update planning/state docs when asked.
- Keep implementation scoped to one clear task/spec at a time.
- Prefer asking targeted clarifying questions before implementing ambiguous research-interface ideas.
- Do not silently make architecture decisions that are not present in a spec, paper note, or explicit user instruction.

## Development Discipline

- Test-driven development is the default and expected workflow for every
  implementation change. Add or extend a test first, run it to confirm that it
  fails for the intended reason, implement the smallest change that makes it
  pass, and then refactor while keeping the tests green.
- After focused tests pass, run the complete relevant test suite before calling
  an implementation complete. For browser work, add automated DOM/behavior
  coverage where practical and always run the applicable syntax and browser
  checks. If a behavior cannot reasonably be automated, define its manual
  acceptance check before implementation and report the result explicitly.
- Documentation-only changes do not require a contrived failing code test;
  verify their diffs and internal consistency instead.
- After completing and verifying a coherent change, create a focused Git commit
  automatically so project history remains easy to follow. Inspect the diff and
  staged files first, never include unrelated user work, and never commit known
  failing behavior.
- A commit does not authorize a push, branch switch, rebase, worktree creation,
  or other remote/history operation. Perform those only when the user asks.

## Codebase Map

- `app/client/`: vanilla JavaScript browser interface.
- `app/server/main.py`: FastAPI app entrypoint and static serving.
- `app/server/routers/config.py`: model/config API.
- `app/server/routers/stream.py`: websocket streaming pipeline.
- `app/server/session.py`: pipeline parameters and session state.
- `app/server/pipeline/`: extraction, transform, synthesis, cluster naming, and export helpers.
- `connector/ossia_probe_server/`: optional C++ libossia OSCQuery sidecar for bounded probe summaries.
- `app/server/tests/`: server-side pytest tests.
- `specs/`: implementation specs, bug notes, and backlog.
- `docs/agentic/`: agent workflow, state, roadmap, and prompt templates.

## Commands

- Start app and open its browser UI: `./scripts/start.sh`
- Start without opening a browser: `./scripts/start.sh --no-browser`
- Start verbose: `./scripts/start.sh --verbose`
- Stop app: `./scripts/stop.sh`
- Reset enriched cluster cache on start: `./scripts/start.sh --reset-cache`
- Run server tests: `cd app/server && uv run pytest`

## Coding Rules

- Follow the existing Python/FastAPI and vanilla JavaScript style.
- Keep browser UI changes in `app/client/index.html`, `app/client/style.css`, and `app/client/main.js` unless a server change is required.
- Keep server streaming changes localized to `app/server/routers/stream.py` and pipeline helpers where possible.
- Follow the test-driven development rules above for Python, JavaScript, and
  other behavior changes.
- For research-facing logic, use meaningful names and docstrings that connect code to the paper/design context.
- Avoid hardcoded absolute paths in app code. Use relative paths, config, or environment variables.

## Safety

- Commit completed, verified, in-scope work automatically. Do not push, switch
  branches, rebase, or create worktrees unless the user asks.
- Do not edit files outside the repo unless the user explicitly asks.
- Do not add generated caches, audio outputs, runs, local references, or papers to Git without confirmation.
- `references/` is ignored intentionally; it is local background material, not active app code.
- Existing app code may contain old Anthropic/Claude references for runtime cluster
  naming. Treat those as implementation details to replace or remove only when the
  user asks for that task; they are not part of the agent workflow.
