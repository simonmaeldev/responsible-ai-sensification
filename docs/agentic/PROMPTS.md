# Agent Prompt Templates

Use these as lightweight prompts when starting a new agent session or task.

## Clarify Mode

Use when the user has an idea but implementation details are still unclear.

```text
Read AGENTS.md, docs/agentic/PROJECT_STATE.md, and docs/agentic/WORKFLOW.md.

We are clarifying a new task before coding. Ask focused questions until the task is specific enough to write a short implementation spec. Keep questions grouped and practical. Do not edit app code.

User request:
[paste request]
```

## Spec Mode

Use when the idea is understood and should become a scoped implementation note.

```text
Read AGENTS.md, docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md, and any relevant specs.

Create or update a focused spec for this task. Include goal, non-goals, affected files, implementation outline, verification plan, and open questions. Do not implement yet unless explicitly asked.

Task:
[paste task]
```

## Implement Mode

Use only after a task/spec is clear.

```text
Read AGENTS.md, docs/agentic/PROJECT_STATE.md, docs/agentic/WORKFLOW.md, and the task spec.

Implement only the requested task. Keep changes scoped. Run the smallest useful verification. Update project state if the result changes future work. Do not commit unless asked.

Spec/task:
[paste path or task]
```

## Review Mode

Use after implementation or before committing.

```text
Review the current diff as a code reviewer. Prioritize bugs, regressions, missing tests, and scope drift. Lead with findings and file/line references. If no issues are found, say so and note residual test gaps.
```

