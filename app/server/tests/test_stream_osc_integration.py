"""Small integration checks at the WebSocket-to-OSC forwarding boundary."""

import asyncio
import json
import threading
from unittest.mock import patch

from app.server.pipeline.osc_output import OscResult
from app.server.pipeline.ossia_probe_output import OssiaResult
from app.server.routers.stream import (
    _forward_token_event,
    _put_token_event,
    _sync_live_osc_controls,
    _sync_live_ossia,
    _stop_session,
)
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


class FailingOssiaOutput:
    def __init__(self):
        self.forwarded_event = None
        self.synced = False

    def emit_token(self, params, event):
        self.forwarded_event = event
        return OssiaResult("error", "libossia bridge output failed: test", error="test")

    def sync(self, params):
        self.synced = True
        return OssiaResult("active", "OSCQuery ws://127.0.0.1:5678")


class StopSession:
    def __init__(self, running):
        self.running = running
        self.cancelled = False

    def is_running(self):
        return self.running

    async def cancel(self):
        self.cancelled = True


def test_generation_waits_until_forwarding_finishes_before_next_model_step():
    class ImmediateLoop:
        @staticmethod
        def call_soon_threadsafe(callback, *args):
            callback(*args)

    class RecordingQueue:
        def __init__(self):
            self.queued = threading.Event()
            self.value = None

        def put_nowait(self, value):
            self.value = value
            self.queued.set()

    queue = RecordingQueue()
    event = {"type": "token", "token": "first"}
    observer_event = {"type": "activation_token", "sequence": 1}
    producer = threading.Thread(
        target=_put_token_event,
        args=(queue, event, ImmediateLoop(), observer_event),
    )
    producer.start()

    assert queue.queued.wait(timeout=1)
    queued_event, activation_event, delivered = queue.value
    assert queued_event is event
    assert activation_event is observer_event
    assert producer.is_alive()
    delivered.set()
    producer.join(timeout=1)
    assert producer.is_alive() is False


def test_stop_action_only_sends_fallback_status_when_no_pipeline_will_send_it():
    running_ws = FakeWebSocket()
    running = StopSession(running=True)
    asyncio.run(_stop_session(running_ws, running))
    assert running.cancelled is True
    assert running_ws.messages == []

    idle_ws = FakeWebSocket()
    idle = StopSession(running=False)
    asyncio.run(_stop_session(idle_ws, idle))
    assert idle.cancelled is True
    assert idle_ws.messages == [{"type": "stopped"}]


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


def test_passive_activation_observer_is_forwarded_without_changing_browser_event():
    ws = FakeWebSocket()
    osc = FailingOscOutput()
    params = PipelineParams()
    event = {
        "type": "token",
        "token": "x",
        "notes": [{"freq": 432.1, "raw_freq": 440.0, "amplitude": 1.0}],
    }
    activation_event = {
        "type": "activation_token",
        "schema_version": 1,
        "run_id": "run-observer",
        "active_features": [{"index": 42, "activation": 1.25}],
    }
    published = []

    async def record_activation(payload):
        published.append(payload)

    with patch(
        "app.server.routers.stream.publish_activation",
        record_activation,
        create=True,
    ):
        result = asyncio.run(
            _forward_token_event(
                ws,
                event,
                params,
                osc,
                activation_event=activation_event,
            )
        )

    assert result.state == "error"
    assert ws.messages[0] == event
    assert published == [activation_event]


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


def test_browser_token_is_unchanged_when_libossia_publication_fails():
    ws = FakeWebSocket()
    osc = FailingOscOutput()
    ossia = FailingOssiaOutput()
    params = PipelineParams()
    event = {
        "type": "token",
        "token": "x",
        "notes": [],
        "probes": [{"id": "residual", "vector": [1.0, 2.0], "publish": True}],
    }

    result = asyncio.run(_forward_token_event(ws, event, params, osc, ossia))

    assert result.state == "error"
    assert ossia.forwarded_event is event
    assert ws.messages[0] == event
    assert ws.messages[-1] == {
        "type": "ossia_status",
        "status": "error",
        "message": "libossia bridge output failed: test",
    }


def test_live_libossia_enable_and_port_updates_are_synchronized():
    ws = FakeWebSocket()
    ossia = FailingOssiaOutput()

    result = asyncio.run(_sync_live_ossia(ws, PipelineParams(), ossia))

    assert result.state == "active"
    assert ossia.synced is True
    assert ws.messages[-1] == {
        "type": "ossia_status",
        "status": "active",
        "message": "OSCQuery ws://127.0.0.1:5678",
    }
