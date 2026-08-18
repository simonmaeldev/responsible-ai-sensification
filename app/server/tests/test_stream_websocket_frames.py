"""Compatibility checks for browser text and score binary WebSocket commands."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect

from app.server.routers.stream import _observation_payload, _receive_command


class FrameWebSocket:
    def __init__(self, frame):
        self.frame = frame

    async def receive(self):
        return self.frame


@pytest.mark.parametrize("frame_key", ["text", "bytes"])
def test_receive_command_accepts_text_and_utf8_binary_json(frame_key):
    command = {"action": "start", "params": {"prompt": "score"}}
    encoded = json.dumps(command)
    payload = encoded if frame_key == "text" else encoded.encode("utf8")
    websocket = FrameWebSocket(
        {"type": "websocket.receive", frame_key: payload}
    )

    assert asyncio.run(_receive_command(websocket)) == command


@pytest.mark.parametrize(
    "frame",
    [
        {"type": "websocket.receive", "text": "not json"},
        {"type": "websocket.receive", "bytes": b"\xff"},
        {"type": "websocket.receive", "bytes": None},
    ],
)
def test_receive_command_rejects_invalid_payloads(frame):
    with pytest.raises(ValueError, match="Invalid JSON"):
        asyncio.run(_receive_command(FrameWebSocket(frame)))


def test_receive_command_preserves_disconnect_semantics():
    websocket = FrameWebSocket(
        {"type": "websocket.disconnect", "code": 1001}
    )

    with pytest.raises(WebSocketDisconnect) as error:
        asyncio.run(_receive_command(websocket))
    assert error.value.code == 1001


def test_observation_payload_preserves_dense_and_fixed_sae_provenance():
    token = SimpleNamespace(
        probe_layer=7,
        probe_module_path="model.layers.7",
        probe_shape=[1152],
        probe_dtype="float32",
        probe_representation="dense_residual",
        sae_module_path="gemma_scope.resid_post.layer_22.width_65k",
        sae_shape=[65536],
        sae_dtype="sparse_float32",
        sae_representation="sparse_sae",
    )
    params = SimpleNamespace(
        model="google/gemma-3-1b-pt",
        layer=22,
        width="65k",
    )

    assert _observation_payload(token, params) == {
        "model": "google/gemma-3-1b-pt",
        "site": "residual_post",
        "layer": 7,
        "module_path": "model.layers.7",
        "shape": [1152],
        "dtype": "float32",
        "representation": "dense_residual",
        "sae_layer": 22,
        "sae_width": "65k",
        "sae_module_path": "gemma_scope.resid_post.layer_22.width_65k",
        "sae_shape": [65536],
        "sae_dtype": "sparse_float32",
        "sae_representation": "sparse_sae",
    }
