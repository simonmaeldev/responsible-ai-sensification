"""Two-token fixture for synchronized score research-interface verification."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets


READY_EVENT = {
    "type": "ready",
    "params": {
        "prompt": "",
        "model": "google/gemma-3-1b-pt",
        "observation_layer": 22,
        "layer": 22,
        "max_tokens": 200,
    },
}

MODEL_STRUCTURE_EVENT = {
    "type": "model_structure",
    "model": "google/gemma-3-1b-pt",
    "architecture": {
        "model_type": "gemma3_text",
        "layer_count": 26,
        "hidden_size": 1152,
        "intermediate_size": 6912,
        "attention_heads": 4,
        "key_value_heads": 1,
        "head_dim": 256,
        "sliding_window": 512,
        "max_position_embeddings": 32768,
        "layer_types": [
            "full_attention" if (index + 1) % 6 == 0 else "sliding_attention"
            for index in range(26)
        ],
    },
}


def layer_profile(offset: float) -> dict[str, Any]:
    return {
        "value": {
            "layers": [
                {
                    "layer": index,
                    "rms": offset + index + 0.25,
                    "max_abs": offset + index + 0.75,
                    "delta_rms": None if index == 0 else offset + index / 10,
                    "cosine_to_previous": None if index == 0 else 0.99 - index / 1000,
                }
                for index in range(26)
            ],
            "shape": [26],
            "dtype": "layer_profile",
        }
    }


def token_event(
    *,
    token: str,
    token_id: int,
    token_index: int,
    dense_layer: int,
    feature_index: int,
    feature_activation: float,
    description: str,
    profile_offset: float,
) -> dict[str, Any]:
    return {
        "type": "token",
        "token": token,
        "token_id": token_id,
        "elapsed_ms": 10.0 + token_index,
        "observation": {
            "model": "google/gemma-3-1b-pt",
            "site": "residual_post",
            "layer": dense_layer,
            "module_path": f"model.layers.{dense_layer}",
            "shape": [1152],
            "dtype": "float32",
            "representation": "dense_residual",
            "sae_layer": 22,
            "sae_width": "65k",
            "sae_module_path": "gemma_scope.resid_post.layer_22.width_65k",
            "sae_shape": [65536],
            "sae_dtype": "sparse_float32",
            "sae_representation": "sparse_sae",
        },
        "probes": [
            {
                "id": "residual",
                "model": "google/gemma-3-1b-pt",
                "token_index": token_index,
                "site": "residual_post",
                "layer": dense_layer,
                "module_path": f"model.layers.{dense_layer}",
                "capture": "summary",
                "publish": True,
                "shape": [1152],
                "dtype": "float32",
                "summary": {
                    "rms": profile_offset + 0.5,
                    "max_abs": profile_offset + 1.5,
                    "mean": profile_offset - 0.125,
                },
            },
            {
                "id": "sae",
                "model": "google/gemma-3-1b-pt",
                "token_index": token_index,
                "site": "sae",
                "layer": 22,
                "module_path": "gemma_scope.resid_post.layer_22.width_65k",
                "capture": "summary",
                "publish": True,
                "shape": [65536],
                "dtype": "sparse_float32",
                "summary": {
                    "active_count": 2,
                    "max_activation": feature_activation,
                    "total_activation": feature_activation + 0.5,
                    "top_index": feature_index,
                    "top_activation": feature_activation,
                },
            },
        ],
        "emitter": {
            "streams": {
                "model.layer_profile": layer_profile(profile_offset),
                "sae.active_features": {
                    "value": [
                        {
                            "index": feature_index + 10,
                            "activation": 0.5,
                            "description": "secondary evidence",
                        },
                        {
                            "index": feature_index,
                            "activation": feature_activation,
                            "description": description,
                        },
                    ]
                },
            }
        },
    }


FIRST_TOKEN = token_event(
    token=" bell",
    token_id=420,
    token_index=1,
    dense_layer=22,
    feature_index=3,
    feature_activation=2.25,
    description="bells",
    profile_offset=0.0,
)

SECOND_TOKEN = token_event(
    token=" glass",
    token_id=421,
    token_index=2,
    dense_layer=7,
    feature_index=8,
    feature_activation=3.5,
    description="glass surfaces",
    profile_offset=10.0,
)


async def send_event(socket: Any, event: dict[str, Any]) -> None:
    await socket.send(json.dumps(event))


def rack_moved_to_layer(params: dict[str, Any], layer: int) -> bool:
    rack = params.get("probe_rack")
    if not isinstance(rack, list):
        return False
    return any(
        probe.get("site") == "residual_post" and probe.get("layer") == layer
        for probe in rack
        if isinstance(probe, dict)
    )


async def run_research_fixture(
    host: str,
    port: int,
    ready: asyncio.Future[int] | None = None,
) -> None:
    received: list[dict[str, Any]] = []
    finished = asyncio.Event()
    observation_layer = 22
    probe_layer = 22
    second_sent = False

    async def handle(socket: Any) -> None:
        nonlocal observation_layer, probe_layer, second_sent
        await send_event(socket, READY_EVENT)
        async for raw_message in socket:
            message = json.loads(raw_message)
            received.append(message)
            print(
                f"RESEARCH_FIXTURE_RECEIVED {json.dumps(message, sort_keys=True)}",
                flush=True,
            )
            action = message.get("action")
            params = message.get("params", {})
            if action == "start":
                await send_event(
                    socket,
                    {
                        "type": "loading",
                        "label": "Sparse autoencoder",
                        "detail": "Phase 3 deterministic fixture",
                        "progress": 0.5,
                    },
                )
                await send_event(socket, MODEL_STRUCTURE_EVENT)
                await asyncio.sleep(0.1)
                await send_event(socket, FIRST_TOKEN)
            elif action == "update_params":
                if params.get("observation_layer") is not None:
                    observation_layer = int(params["observation_layer"])
                if rack_moved_to_layer(params, 7):
                    probe_layer = 7
                if observation_layer == 7 and probe_layer == 7 and not second_sent:
                    second_sent = True
                    await asyncio.sleep(0.1)
                    await send_event(socket, SECOND_TOKEN)
                    await asyncio.sleep(0.1)
                    await send_event(socket, {"type": "done"})
            elif action == "stop":
                await send_event(socket, {"type": "stopped"})
                finished.set()

    async with websockets.serve(handle, host, port) as server:
        actual_port = server.sockets[0].getsockname()[1]
        if ready is not None and not ready.done():
            ready.set_result(actual_port)
        print(
            f"RESEARCH_FIXTURE_READY ws://{host}:{actual_port}/ws/stream",
            flush=True,
        )
        await asyncio.wait_for(finished.wait(), timeout=60)

    starts = [message for message in received if message.get("action") == "start"]
    stops = [message for message in received if message.get("action") == "stop"]
    if len(starts) != 1 or len(stops) != 1:
        raise RuntimeError("Expected one research start and stop request")
    if starts[0].get("params", {}).get("prompt") != "Phase 3 research smoke":
        raise RuntimeError("score did not forward the Phase 3 prompt")
    if starts[0].get("params", {}).get("max_tokens") != 2:
        raise RuntimeError("score did not forward the Phase 3 token limit")
    if not second_sent:
        raise RuntimeError("score did not send both live layer and probe changes")
