"""Small integration checks at the WebSocket-to-OSC forwarding boundary."""

import asyncio
import json

from app.server.pipeline.osc_output import OscResult
from app.server.routers.stream import _forward_token_event, _sync_live_osc_controls
from app.server.session import PipelineParams


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_text(self, payload):
        self.messages.append(json.loads(payload))


class FailingOscOutput:
    def __init__(self):
        self.forwarded_event = None
        self.changed_fields = None

    def emit_token(self, params, event):
        self.forwarded_event = event
        return OscResult("error", "OSC send failed: test", error="test")

    def sync_controls(self, params, changed_fields):
        self.changed_fields = changed_fields
        return OscResult("ready", "OSC targeting test:9000 via UDP; delivery unconfirmed")


def test_browser_token_is_unchanged_when_osc_send_fails():
    ws = FakeWebSocket()
    osc = FailingOscOutput()
    params = PipelineParams()
    event = {
        "type": "token",
        "token": "x",
        "notes": [{"freq": 432.1, "raw_freq": 440.0, "amplitude": 1.0}],
    }

    result = asyncio.run(_forward_token_event(ws, event, params, osc))

    assert result.state == "error"
    assert osc.forwarded_event is event
    assert ws.messages[0] == event
    assert ws.messages[1] == {
        "type": "osc_status",
        "status": "error",
        "message": "OSC send failed: test",
    }


def test_live_parameter_updates_are_forwarded_to_active_osc_run():
    ws = FakeWebSocket()
    osc = FailingOscOutput()
    params = PipelineParams()

    result = asyncio.run(
        _sync_live_osc_controls(ws, params, osc, {"bpm", "osc_port"})
    )

    assert result.state == "ready"
    assert osc.changed_fields == {"bpm", "osc_port"}
    assert ws.messages[-1]["type"] == "osc_status"
    assert "delivery unconfirmed" in ws.messages[-1]["message"]
