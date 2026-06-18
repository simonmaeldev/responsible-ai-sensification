# Project State

Last updated: 2026-06-17

## Branch

Current branch: `nicolas-attempts`

This branch was created from `main` for Nicolas's work. Confirm the branch before any implementation session:

```bash
git branch --show-current
```

## Current Mode

No coding of new project ideas yet.

The user plans to add their own term paper soon. Wait for that paper before implementing new interface ideas, because it should become the main design context.

Agent workflow clarification: use Codex for planning, implementation, review, and
remote-machine coordination. Do not assume Anthropic/Claude tooling for agentic
project work.

## Recent Setup

- Inspected local archive: `/home/apaixonada/EvaPortelance/responsible-ai-sensification-zougoulou-main.zip`.
- Extracted old material to a local ignored `references/` folder.
- Added `references/` to `.gitignore`.
- Inspected local PDF: `/home/apaixonada/Downloads/Mila Community Agentic Coding Best Practices (1).pdf`.
- Set up this agentic workflow documentation.

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
- Whether to port the old tonality/pitch-bias idea into the new interface.
- What the first user-facing workflow should be after paper ingestion.
- Whether to remove or replace existing app-level Anthropic cluster-naming code
  before live audio testing.

## Handoff Notes

Before coding next:

1. Read the term paper or paper-derived notes once the user adds them.
2. Ask clarifying questions about the desired first workflow.
3. Write or update a focused spec before implementation.
4. Keep each implementation step small and verifiable.
