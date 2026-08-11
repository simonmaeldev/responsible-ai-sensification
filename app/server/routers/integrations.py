"""Passive activation observers and deterministic fixture replay endpoints."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.server.pipeline.external_output import ACTIVATION_SCHEMA_VERSION

router = APIRouter()
FIXTURE_PATH = (
    Path(__file__).parents[3]
    / "integrations"
    / "fixtures"
    / "activation-events.ndjson"
)

_observers: set[WebSocket] = set()
_replay_task: asyncio.Task | None = None


class ReplayRequest(BaseModel):
    interval_ms: int = Field(default=250, ge=0, le=60_000)
    loop: bool = False


def load_activation_fixture(path: Path = FIXTURE_PATH) -> list[dict]:
    """Load and minimally validate the checked-in integration fixture."""
    events: list[dict] = []
    with path.open(encoding="utf-8") as fixture:
        for line_number, line in enumerate(fixture, start=1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("type") != "activation_token":
                raise ValueError(
                    f"Fixture line {line_number} is not an activation_token"
                )
            if event.get("schema_version") != ACTIVATION_SCHEMA_VERSION:
                raise ValueError(
                    f"Fixture line {line_number} has an unsupported schema version"
                )
            events.append(event)
    return events


async def publish_activation(event: dict[str, Any]) -> None:
    """Broadcast rich JSON without expanding the production OSC contract."""
    if not _observers:
        return
    message = json.dumps(event, ensure_ascii=True)
    observers = list(_observers)
    results = await asyncio.gather(
        *(observer.send_text(message) for observer in observers),
        return_exceptions=True,
    )
    for observer, result in zip(observers, results):
        if isinstance(result, Exception):
            _observers.discard(observer)


async def _run_replay(request: ReplayRequest) -> None:
    events = load_activation_fixture()
    iteration = 0
    while True:
        iteration += 1
        for event in events:
            await publish_activation(
                {**event, "source": "fixture", "replay_iteration": iteration}
            )
            if request.interval_ms:
                await asyncio.sleep(request.interval_ms / 1000.0)
        if not request.loop:
            return


@router.websocket("/ws/activations")
async def ws_activations(ws: WebSocket) -> None:
    """Observe activation events without controlling the model session."""
    await ws.accept()
    _observers.add(ws)
    await ws.send_json(
        {
            "type": "activation_ready",
            "schema_version": ACTIVATION_SCHEMA_VERSION,
            "mode": "passive",
        }
    )
    try:
        while True:
            message = await ws.receive_text()
            if message == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        _observers.discard(ws)


@router.post("/api/integrations/replay")
async def start_fixture_replay(request: ReplayRequest) -> dict:
    """Replay deterministic events to passive observers without model loading."""
    global _replay_task
    if _replay_task and not _replay_task.done():
        _replay_task.cancel()
    events = load_activation_fixture()
    _replay_task = asyncio.create_task(_run_replay(request))
    return {
        "status": "started",
        "event_count": len(events),
        "interval_ms": request.interval_ms,
        "loop": request.loop,
    }


@router.post("/api/integrations/replay/stop")
async def stop_fixture_replay() -> dict:
    global _replay_task
    if _replay_task and not _replay_task.done():
        _replay_task.cancel()
        try:
            await _replay_task
        except asyncio.CancelledError:
            pass
    _replay_task = None
    return {"status": "stopped"}


@router.get("/api/integrations/status")
async def integration_status() -> dict:
    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "observer_count": len(_observers),
        "replay_running": bool(_replay_task and not _replay_task.done()),
        "osc_contract": "/rai/v1",
    }
