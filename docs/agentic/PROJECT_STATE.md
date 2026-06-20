# Project State

Last updated: 2026-06-20

## Branch

Current branch: `nicolas-attempts`

This branch was created from `main` for Nicolas's work. Confirm the branch before any implementation session:

```bash
git branch --show-current
```

## Current Mode

Implementation has started on the semantic-tonality audio direction.

The first scoped implementation is a local MiniLM-based foundation for embedding
verbal tonality descriptions in the same semantic space as active SAE feature
descriptions. This does not yet alter live audio playback.

Agent workflow clarification: use Codex for planning, implementation, review, and
remote-machine coordination. Do not assume Anthropic/Claude tooling for agentic
project work.

## Recent Setup

- Inspected local archive: `/home/apaixonada/EvaPortelance/responsible-ai-sensification-zougoulou-main.zip`.
- Extracted old material to a local ignored `references/` folder.
- Added `references/` to `.gitignore`.
- Inspected local PDF: `/home/apaixonada/Downloads/Mila Community Agentic Coding Best Practices (1).pdf`.
- Set up this agentic workflow documentation.
- Added `app/server/pipeline/semantic_tonality.py` and
  `app/server/pipeline/tonality_data/default_tonalities.json` as the first
  local, Anthropic-free semantic tonality foundation.

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
- How to wire semantic tonality matches into live audio: pitch, timbre, envelope,
  density, filter/brightness, or a combination.
- What the first user-facing workflow should be after paper ingestion.
- Whether to remove or replace existing app-level Anthropic cluster-naming code
  before live audio testing.

## Handoff Notes

Before coding next:

1. Decide the first audio consumer for semantic tonality matches.
2. Wire `match_active_features_to_tonalities` into the stream only after choosing
   what it should control.
3. Keep the Anthropic cluster-naming fallback separate from semantic-tonality work.
4. Keep each implementation step small and verifiable.
