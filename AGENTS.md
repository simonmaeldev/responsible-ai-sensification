# Agent Instructions

## Project

This repository is `responsible-ai-sensification`: a research/prototype app that turns Gemma 3 SAE feature activations into live browser audio and visualizations.

The current working direction is the new browser interface in `app/client/`, backed by the FastAPI server in `app/server/`.

## Required Startup Context

Before making non-trivial changes, read:

- `docs/agentic/PROJECT_STATE.md` for the current state and handoff notes.
- `docs/agentic/WORKFLOW.md` for how planning, implementation, and verification should proceed.
- `docs/agentic/ROADMAP.md` for the current phase breakdown.
- `specs/TODO.md` and any relevant file in `specs/` for existing feature/bug context.

If the user adds a term paper or design document, treat it as the primary design context before proposing implementation.

## Collaboration Mode

- Use Codex as the coding agent/workflow driver. Do not assume Claude Code,
  Anthropic tooling, or Anthropic-specific agent commands for project work.
- The user may want to talk through ideas before coding. If they say not to code yet, only update planning/state docs when asked.
- Keep implementation scoped to one clear task/spec at a time.
- Prefer asking targeted clarifying questions before implementing ambiguous research-interface ideas.
- Do not silently make architecture decisions that are not present in a spec, paper note, or explicit user instruction.

## Codebase Map

- `app/client/`: vanilla JavaScript browser interface.
- `app/server/main.py`: FastAPI app entrypoint and static serving.
- `app/server/routers/config.py`: model/config API.
- `app/server/routers/stream.py`: websocket streaming pipeline.
- `app/server/session.py`: pipeline parameters and session state.
- `app/server/pipeline/`: extraction, transform, synthesis, cluster naming, and export helpers.
- `app/server/tests/`: server-side pytest tests.
- `specs/`: implementation specs, bug notes, and backlog.
- `docs/agentic/`: agent workflow, state, roadmap, and prompt templates.

## Commands

- Start app: `./scripts/start.sh`
- Start verbose: `./scripts/start.sh --verbose`
- Stop app: `./scripts/stop.sh`
- Reset enriched cluster cache on start: `./scripts/start.sh --reset-cache`
- Run server tests: `cd app/server && uv run pytest`

## Coding Rules

- Follow the existing Python/FastAPI and vanilla JavaScript style.
- Keep browser UI changes in `app/client/index.html`, `app/client/style.css`, and `app/client/main.js` unless a server change is required.
- Keep server streaming changes localized to `app/server/routers/stream.py` and pipeline helpers where possible.
- Add tests when changing reusable Python behavior or bug-prone server logic.
- For research-facing logic, use meaningful names and docstrings that connect code to the paper/design context.
- Avoid hardcoded absolute paths in app code. Use relative paths, config, or environment variables.

## Safety

- Do not commit, push, or switch branches unless the user asks.
- Do not edit files outside the repo unless the user explicitly asks.
- Do not add generated caches, audio outputs, runs, local references, or papers to Git without confirmation.
- `references/` is ignored intentionally; it is local background material, not active app code.
- Existing app code may contain old Anthropic/Claude references for runtime cluster
  naming. Treat those as implementation details to replace or remove only when the
  user asks for that task; they are not part of the agent workflow.
