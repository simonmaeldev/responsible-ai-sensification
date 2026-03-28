# Bug: Transport Controls — Soft-lock, Next disabled, Text panel stale

## Bug Description

Three related bugs in the client-side transport controls (`app/client/main.js`):

**BUG 1 — ↺ (Restart) while paused soft-locks the UI.**
Clicking the ↺ button while paused triggers `startPipeline()`, which sets `isRunning = true` and calls `setRunning()` to put the buttons in the running state. However the server responds to the new "start" action by first emitting a `"stopped"` event for the old run. The `"stopped"` handler calls `setIdle()` unconditionally, which sets `isRunning = false` and reverts all buttons to idle — overwriting the `setRunning()` state. The result is that Play, Pause, and Stop are all stuck in a broken half-idle/half-paused state and the user must reload to recover.

**BUG 2 — "Next" stays disabled even though buffered tokens exist.**
`setPaused()` computes `btnNext.disabled = historyIndex >= tokenHistory.length - 1` at the exact moment of pausing. If the user pauses on the latest token, this evaluates to `true` (disabled). Subsequent tokens that arrive while paused are pushed into both `tokenHistory` and `pendingBuffer`, so `tokenHistory.length` grows — but `btnNext.disabled` is never re-evaluated. The user cannot press Next even though there are newer tokens to navigate to, unless they first press Previous (which unconditionally sets `btnNext.disabled = false`).

**BUG 3 — Text output panel not updated when Next advances into buffered tokens.**
`navigateNext()` calls `renderClusterVizStatic()`, which updates the canvas and labels but never appends a token span to `#cv-text-content`. Tokens received while paused were buffered and never rendered to the text panel. When Next advances `historyIndex` beyond the last live-rendered token, `highlightToken()` finds no `<span data-idx="N">` for that index and silently does nothing. The text panel shows no new text and no highlight for those tokens.

## Problem Statement

1. `handleMessage("stopped")` blindly calls `setIdle()`, racing against `startPipeline()`'s optimistic `setRunning()` call.
2. `btnNext.disabled` is computed once at pause time and never updated when new tokens arrive during pause.
3. `navigateNext()` does not append a text span for tokens that were buffered (never live-rendered).

## Solution Statement

1. **BUG 1**: Guard the `"stopped"` handler — only call `setIdle()` + `resetClusterViz()` when `isRunning` is `false`. If `isRunning` is `true`, a new pipeline has already been started; the "stopped" event is stale and should be ignored.

2. **BUG 2**: After pushing a token to `pendingBuffer`, immediately set `btnNext.disabled = false` (since a new item now exists in `tokenHistory` beyond `historyIndex`). Also update the `navigateNext()` recomputation to use the same condition: `historyIndex >= tokenHistory.length - 1`.

3. **BUG 3**: In `navigateNext()`, after incrementing `historyIndex`, check whether a span with `data-idx=historyIndex` already exists in `#cv-text-content`. If it does not exist (buffered token, never rendered), create and append it the same way `renderClusterViz()` does, then call `highlightToken()` to mark it active.

## Steps to Reproduce

**BUG 1:**
1. Open the UI, press Play — pipeline starts.
2. Press Pause.
3. Press ↺ (restart / btnSend).
4. Observe: buttons freeze; Play is disabled, Pause is disabled, Stop is enabled but clicking it does nothing useful. Must F5 to recover.

**BUG 2:**
1. Open the UI, press Play.
2. Wait for at least one token to appear in the text panel.
3. Press Pause immediately.
4. Observe: Next (⏭) is disabled even though new tokens are still streaming into the buffer.
5. Press Previous (⏮) once.
6. Observe: Next (⏭) becomes enabled — confirming the state is wrong after pause.

**BUG 3:**
1. Open the UI, press Play.
2. Wait for several tokens to appear in the text panel.
3. Press Pause — let more tokens buffer.
4. Press Next (⏭) repeatedly until `historyIndex` advances beyond the last live-rendered token.
5. Observe: the text panel stops updating and no highlight appears for the new tokens.

## Root Cause Analysis

**BUG 1 — Race between optimistic `setRunning()` and server-echoed `"stopped"`:**
`startPipeline()` calls `setRunning()` synchronously and then sends `{action:"start"}` over WebSocket. The server stops the existing run (emitting `"stopped"`) before starting the new one. `handleMessage` processes `"stopped"` after `setRunning()` has already run, and `setIdle()` unconditionally overwrites the running state. Fix location: `handleMessage`, case `"stopped"`.

**BUG 2 — One-shot button state computation at pause time:**
`setPaused()` is called once. It sets `btnNext.disabled` based on the snapshot of `tokenHistory.length` at that instant. The `"token"` handler pushes to `tokenHistory` while paused but never touches `btnNext.disabled`. Fix location: `handleMessage`, case `"token"` (the `isPaused` branch).

**BUG 3 — `renderClusterVizStatic` intentionally skips text append:**
`renderClusterVizStatic` was designed to update only the canvas/labels for already-known tokens. But `navigateNext()` uses it even when the token at `historyIndex` was never rendered to the text panel (because it arrived while paused). `highlightToken` then fails silently because no matching span exists. Fix location: `navigateNext()`.

## Relevant Files

- **`app/client/main.js`** — all three bugs are in this file:
  - `handleMessage` (`"stopped"` case): unconditional `setIdle()` call (BUG 1).
  - `handleMessage` (`"token"` case, `isPaused` branch): missing `btnNext.disabled = false` update (BUG 2).
  - `navigateNext()`: missing text-span creation for buffered tokens (BUG 3).

## Step by Step Tasks

### Step 1: Fix BUG 1 — Guard `"stopped"` handler against restart race

In `handleMessage`, case `"stopped"`:

- Wrap the `setIdle()` + `resetClusterViz()` calls in a guard: only execute them if `!isRunning`.
- When `isRunning` is `true`, a new pipeline has already been started by `startPipeline()`; the "stopped" event is from the old run and must be discarded.

```js
case "stopped":
  engine.stopAll();
  if (!isRunning) {
    setIdle();
    resetClusterViz();
  }
  break;
```

### Step 2: Fix BUG 2 — Enable "Next" when buffered tokens arrive

In `handleMessage`, case `"token"`, inside the `if (isPaused)` branch, after `pendingBuffer.push(msg)`:

- Add `btnNext.disabled = false;` so the button reflects that there is now a token in `tokenHistory` beyond `historyIndex`.

```js
if (isPaused) {
  pendingBuffer.push(msg);
  btnNext.disabled = false;  // ← add this line
  break;
}
```

### Step 3: Fix BUG 3 — Append text span in `navigateNext()` for buffered tokens

In `navigateNext()`, after incrementing `historyIndex` and before calling `highlightToken`:

- Query `#cv-text-content` for a span with `data-idx=historyIndex`.
- If none exists (this token was buffered, never live-rendered), create and append a span with the token text, exactly as `renderClusterViz()` does.

```js
function navigateNext() {
  if (historyIndex >= tokenHistory.length - 1) return;
  historyIndex++;
  const event = tokenHistory[historyIndex];
  engine.stopAll();
  engine.playNotes(event.notes ?? [], modeSel.value, parseInt(bpmIn.value));
  renderClusterVizStatic(event);

  // Append text span if this token was never live-rendered
  const textContent = document.getElementById("cv-text-content");
  if (textContent && !textContent.querySelector(`span[data-idx="${historyIndex}"]`)) {
    const span = document.createElement("span");
    span.dataset.idx = historyIndex;
    span.textContent = event.token || "";
    textContent.appendChild(span);
    const textBox = document.getElementById("cv-text-output");
    if (textBox) textBox.scrollTop = textBox.scrollHeight;
  }

  highlightToken(historyIndex);
  btnNext.disabled = historyIndex >= tokenHistory.length - 1;
  btnPrev.disabled = false;
  setStatus(`Token ${historyIndex + 1} / ${tokenHistory.length}`);
}
```

### Step 4: Run validation commands

Execute the commands listed in the Validation Commands section.

## Validation Commands

```bash
# Server tests — must pass with zero failures
cd app/server && uv run pytest

# Manual browser smoke test
./scripts/start.sh
# Open http://localhost:8080

# BUG 1 regression check:
# 1. Press Play. Wait for a few tokens.
# 2. Press Pause.
# 3. Press ↺ — the UI must enter running state (Pause+Stop enabled, Play disabled).
# 4. Confirm no soft-lock; Pause and Stop are clickable.

# BUG 2 regression check:
# 1. Press Play. Wait for a token.
# 2. Press Pause. Wait 2 seconds for buffered tokens to accumulate.
# 3. Confirm Next (⏭) is enabled without pressing Previous first.

# BUG 3 regression check:
# 1. Press Play. Wait for 3–5 tokens.
# 2. Press Pause. Wait 3 more seconds (accumulate buffer).
# 3. Press Next repeatedly past the live tokens.
# 4. Confirm each press adds a new token to the text panel and highlights it.

./scripts/stop.sh
```

## Notes

- No server-side changes required; all three bugs are client-side only.
- BUG 1's guard (`if (!isRunning)`) relies on the fact that `startPipeline()` sets `isRunning = true` (via `setRunning()`) synchronously before the server "stopped" echo arrives asynchronously — this ordering is guaranteed by the single-threaded JS event loop.
- BUG 2's fix is a single line; the existing `navigateNext()` already recomputes `btnNext.disabled` correctly after each navigation step, so no change needed there.
- BUG 3 only affects `navigateNext()` — `navigatePrev()` always navigates to already-rendered spans and needs no change.
