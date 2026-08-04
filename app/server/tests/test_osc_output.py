"""Focused tests for the versioned, failure-isolated OSC emitter."""

from app.server.pipeline.osc_output import CONTROL_ADDRESSES, OSC_ROOT, OscRunOutput
from app.server.session import PipelineParams


class RecordingClient:
    def __init__(self, host, port, *, fail_address=None):
        self.host = host
        self.port = port
        self.fail_address = fail_address
        self.messages = []

    def send_message(self, address, value):
        if address == self.fail_address:
            raise OSError("test UDP failure")
        self.messages.append((address, value))


class RecordingFactory:
    def __init__(self, *, fail_address=None):
        self.fail_address = fail_address
        self.clients = []

    def __call__(self, host, port):
        client = RecordingClient(host, port, fail_address=self.fail_address)
        self.clients.append(client)
        return client


def enabled_params(**updates):
    params = PipelineParams()
    params.update(osc_enabled=True, osc_host="127.0.0.1", **updates)
    return params


def token_event():
    return {
        "type": "token",
        "token_id": 42,
        "token": " sound",
        "elapsed_ms": 17,
        "notes": [
            {
                "feature_index": 10,
                "freq": 201.25,
                "raw_freq": 200.0,
                "amplitude": 0.2,
                "cluster": None,
            },
            {
                "feature_index": 11,
                "freq": 333.75,
                "raw_freq": 300.0,
                "amplitude": 0.9,
                "cluster": 4,
                "instrument": "bell",
            },
            {
                "feature_index": 12,
                "freq": 444.5,
                "raw_freq": 400.0,
                "amplitude": 0.6,
                "cluster": 2,
                "instrument": "pad",
            },
        ],
        "tonality": {
            "pitch_bias": 0.75,
            "matches": [{"name": "bright tension", "score": 0.81}],
        },
    }


def test_disabled_and_unconfigured_outputs_send_no_packets():
    factory = RecordingFactory()
    output = OscRunOutput("run-disabled", client_factory=factory)
    params = PipelineParams()

    disabled = output.begin(params)
    params.update(osc_enabled=True)
    unconfigured = output.emit_token(params, token_event())

    assert disabled.state == "disabled"
    assert unconfigured.state == "unconfigured"
    assert unconfigured.sequence == 1
    assert factory.clients == []


def test_disabling_live_output_sends_no_packets_while_disabled():
    factory = RecordingFactory()
    output = OscRunOutput("run-disable-live", client_factory=factory)
    params = enabled_params()
    output.begin(params)
    sent_before_disable = len(factory.clients[0].messages)

    params.update(osc_enabled=False)
    disabled = output.sync_controls(params, {"osc_enabled"})
    output.emit_token(params, token_event())

    assert disabled.state == "disabled"
    assert len(factory.clients[0].messages) == sent_before_disable


def test_start_token_notes_tonality_and_end_follow_v1_contract():
    factory = RecordingFactory()
    output = OscRunOutput("run-1", client_factory=factory)
    params = enabled_params(osc_max_notes_per_token=2, bpm=96, mode="sustain")

    started = output.begin(params)
    event = token_event()
    emitted = output.emit_token(params, event)

    assert started.state == "ready"
    assert emitted.state == "ready"
    assert event["notes"][0]["feature_index"] == 10  # browser event remains uncapped/unreordered

    messages = factory.clients[0].messages
    assert messages[0] == (f"{OSC_ROOT}/run/start", ["run-1", 96, "sustain"])
    assert [address for address, _ in messages[1:7]] == list(CONTROL_ADDRESSES.values())
    assert messages[7] == (f"{OSC_ROOT}/token", ["run-1", 1, 42, " sound", 17])

    note_messages = [message for message in messages if message[0] == f"{OSC_ROOT}/note"]
    assert len(note_messages) == 2
    assert note_messages[0][1] == ["run-1", 1, 0, 11, 333.75, 0.9, 4, "bell"]
    assert note_messages[1][1] == ["run-1", 1, 1, 12, 444.5, 0.6, 2, "pad"]

    assert messages[-2] == (
        f"{OSC_ROOT}/tonality",
        ["run-1", 1, "bright tension", 0.81, 0.75],
    )
    assert messages[-1] == (f"{OSC_ROOT}/token/end", ["run-1", 1, 2])


def test_live_control_and_destination_changes_apply_without_restart():
    factory = RecordingFactory()
    output = OscRunOutput("run-live", client_factory=factory)
    params = enabled_params()
    output.begin(params)

    params.update(bpm=144)
    control_result = output.sync_controls(params, {"bpm"})

    assert control_result.sent == 1
    assert factory.clients[0].messages[-1] == (f"{OSC_ROOT}/control/bpm", 144)

    params.update(osc_port=9100, osc_max_notes_per_token=1)
    destination_result = output.sync_controls(
        params,
        {"osc_port", "osc_max_notes_per_token"},
    )
    output.emit_token(params, token_event())

    assert destination_result.state == "ready"
    assert factory.clients[0].messages[-1] == (f"{OSC_ROOT}/run/stop", "run-live")
    assert (factory.clients[1].host, factory.clients[1].port) == ("127.0.0.1", 9100)
    assert factory.clients[1].messages[0][0] == f"{OSC_ROOT}/run/start"
    assert len([
        message for message in factory.clients[1].messages
        if message[0] == f"{OSC_ROOT}/note"
    ]) == 1


def test_lifecycle_and_sequence_continue_across_looped_tokens():
    factory = RecordingFactory()
    output = OscRunOutput("run-loop", client_factory=factory)
    params = enabled_params(osc_max_notes_per_token=1)

    output.begin(params)
    first = output.emit_token(params, token_event())
    second = output.emit_token(params, token_event())
    output.emit_done(params)
    output.emit_silent(params)
    output.stop(params)

    assert (first.sequence, second.sequence) == (1, 2)
    addresses = [address for address, _ in factory.clients[0].messages]
    assert addresses[-3:] == [
        f"{OSC_ROOT}/run/done",
        f"{OSC_ROOT}/run/silent",
        f"{OSC_ROOT}/run/stop",
    ]


def test_send_failures_are_reported_without_raising():
    factory = RecordingFactory(fail_address=f"{OSC_ROOT}/note")
    output = OscRunOutput("run-error", client_factory=factory)
    params = enabled_params()

    output.begin(params)
    result = output.emit_token(params, token_event())

    assert result.state == "error"
    assert result.error == "test UDP failure"
    assert "delivery" not in result.message
