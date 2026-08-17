"""Compatibility checks for browser text and score binary WebSocket commands."""

import asyncio
import json

import pytest
from fastapi import WebSocketDisconnect

from app.server.routers.stream import _receive_command


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
