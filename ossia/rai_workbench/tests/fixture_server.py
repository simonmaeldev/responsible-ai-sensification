"""Deterministic WebSocket fixture for the score Phase 1 smoke test."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets


READY_EVENT = {
    "type": "ready",
    "params": {
        "prompt": "",
        "model": "google/gemma-3-1b-it",
        "observation_layer": 17,
        "layer": 22,
    },
}

TOKEN_EVENT = {
    "type": "token",
    "token": " bell",
    "token_id": 420,
    "elapsed_ms": 12.5,
    "observation": {
        "model": "google/gemma-3-1b-it",
        "layer": 17,
        "sae_layer": 22,
    },
    "probes": [
        {
            "id": "residual-17",
            "site": "residual",
            "layer": 17,
            "module_path": "model.language_model.layers.17",
            "capture": "output",
            "publish": "summary",
            "shape": [1, 1, 1152],
            "token_index": 0,
            "summary": {
                "rms": 0.75,
                "max_abs": 2.5,
                "mean": -0.125,
                "active_count": 6,
                "top_index": 91,
                "top_activation": 3.25,
            },
        }
    ],
    "emitter": {
        "streams": {
            "sae.active_features": {
                "value": [
                    {"index": 8, "activation": 0.5, "description": "glass"},
                    {"index": 3, "activation": 2.25, "description": "bells"},
                ]
            }
        }
    },
}


async def send_event(socket: Any, event: dict[str, Any]) -> None:
    await socket.send(json.dumps(event))


async def run_fixture(
    host: str,
    port: int,
    ready: asyncio.Future[int] | None = None,
) -> None:
    received: list[dict[str, Any]] = []
    finished = asyncio.Event()

    async def handle(socket: Any) -> None:
        await send_event(socket, READY_EVENT)
        async for raw_message in socket:
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                print(f"FIXTURE_IGNORED {raw_message!r}", flush=True)
                continue
            received.append(message)
            print(f"FIXTURE_RECEIVED {json.dumps(message, sort_keys=True)}", flush=True)

            if message.get("action") == "start":
                await send_event(
                    socket,
                    {
                        "type": "loading",
                        "label": "Sparse autoencoder",
                        "detail": "Deterministic fixture",
                        "progress": 0.5,
                    },
                )
                await asyncio.sleep(0.1)
                await send_event(socket, TOKEN_EVENT)
                await asyncio.sleep(0.1)
                await send_event(socket, {"type": "done"})
            elif message.get("action") == "stop":
                await send_event(socket, {"type": "stopped"})
                finished.set()

    async with websockets.serve(handle, host, port) as server:
        actual_port = server.sockets[0].getsockname()[1]
        if ready is not None and not ready.done():
            ready.set_result(actual_port)
        print(
            f"FIXTURE_READY ws://{host}:{actual_port}/ws/stream",
            flush=True,
        )
        await asyncio.wait_for(finished.wait(), timeout=60)

    start_messages = [item for item in received if item.get("action") == "start"]
    stop_messages = [item for item in received if item.get("action") == "stop"]
    if len(start_messages) != 1 or len(stop_messages) != 1:
        raise RuntimeError("Expected exactly one start and one stop request")

    start_params = start_messages[0].get("params", {})
    if start_params.get("prompt") != "Phase 1 score smoke":
        raise RuntimeError("score did not forward the smoke-test prompt")
    if start_params.get("max_tokens") != 1:
        raise RuntimeError("score did not forward the smoke-test token limit")
    signal_keys = start_params.get("emitter_signal_keys", [])
    if "sae.active_features" not in signal_keys:
        raise RuntimeError("score did not request the sparse SAE feature stream")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()
    asyncio.run(run_fixture(args.host, args.port))


if __name__ == "__main__":
    main()
