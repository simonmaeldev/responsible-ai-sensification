# Roadmap

This is a planning scaffold, not an implementation commitment. Update it after the term paper is added.

## Phase 0: Workflow Setup

Status: complete

- Create root `AGENTS.md`.
- Create durable workflow docs under `docs/agentic/`.
- Keep local old-reference material ignored.
- Do not code new ideas yet.

## Phase 1: Paper Intake

Status: waiting

Goal: turn the user's term paper into usable project context.

Potential tasks:

- Identify where the paper lives in the repo.
- Decide whether it should be tracked by Git.
- Extract or summarize its key claims, sections, and interface implications.
- Add a paper-context note under `docs/agentic/` or `specs/`.

## Phase 2: Interface Story

Status: waiting

Goal: decide what the new interface should help the user demonstrate.

Potential questions:

- What should a viewer understand after using the interface?
- Should the paper drive prompts, explanations, annotations, or evaluation?
- Which current UI panels should remain central?
- Which old ideas from `references/` should be ported, if any?

## Phase 3: First Implementation Spec

Status: waiting

Goal: write one focused spec before coding.

Spec should include:

- User-facing outcome.
- Files likely to change.
- Data inputs and outputs.
- Non-goals.
- Verification plan.

## Phase 4: Implementation And Verification

Status: waiting

Goal: implement the spec in small steps.

Expected pattern:

- Explore relevant files.
- Implement one scoped change.
- Run focused tests or smoke checks.
- Update docs/state if behavior changes.
- Ask before committing.

