"""Tests for the bounded libossia/OSCQuery probe Connector."""

import base64
from pathlib import Path
from types import SimpleNamespace

from app.server.pipeline.ossia_probe_output import (
    MAX_OSCQ_PROBE_SLOTS,
    OSSIA_SLOT_FIELDS,
    OssiaProbeOutput,
    bridge_environment,
    encode_bridge_command,
)


class RecordingInput:
    def __init__(self, fail=False):
        self.lines = []
        self.fail = fail

    def write(self, value):
        if self.fail:
            raise BrokenPipeError("bridge exited")
        self.lines.append(value)

    def flush(self):
        if self.fail:
            raise BrokenPipeError("bridge exited")


class FakeProcess:
    def __init__(self, fail=False):
        self.stdin = RecordingInput(fail=fail)
        self.terminated = False
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode


def params(**overrides):
    values = {
        "ossia_enabled": True,
        "ossia_osc_port": 9010,
        "ossia_query_port": 5678,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def decoded_strings(lines):
    decoded = []
    for line in lines:
        kind, path, value = line.rstrip("\n").split("\t", 2)
        if kind == "s":
            value = base64.b64decode(value).decode("utf-8")
        decoded.append((kind, path, value))
    return decoded


def test_bridge_commands_are_line_safe_and_namespace_is_stable():
    assert encode_bridge_command("/rai/run/token/text", " moon") == (
        "s\t/rai/run/token/text\tIG1vb24=\n"
    )
    assert encode_bridge_command("/rai/probes/1/layer", 7) == (
        "i\t/rai/probes/1/layer\t7\n"
    )
    assert encode_bridge_command("/rai/probes/1/rms", 1.25) == (
        "f\t/rai/probes/1/rms\t1.25\n"
    )
    assert encode_bridge_command("/rai/probes/1/enabled", True) == (
        "b\t/rai/probes/1/enabled\t1\n"
    )
    assert MAX_OSCQ_PROBE_SLOTS == 8
    assert {
        "enabled", "id", "site", "layer", "module_path", "shape",
        "rms", "max_abs", "mean", "active_count", "top_index",
        "top_activation", "sequence",
    } == set(OSSIA_SLOT_FIELDS)


def test_only_bounded_probe_summaries_are_written_to_libossia():
    process = FakeProcess()
    output = OssiaProbeOutput(
        run_id="run-1",
        process_factory=lambda _command: process,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    assert output.sync(params()).state == "active"

    event = {
        "token": " test",
        "token_id": 4,
        "observation": {"model": "test/gemma"},
        "probes": [
            {
                "id": "residual",
                "site": "residual_post",
                "layer": 7,
                "module_path": "model.layers.7",
                "shape": [1152],
                "publish": True,
                "vector": [float(index) for index in range(1152)],
                "summary": {"rms": 2.5, "max_abs": 8.0, "mean": -0.25},
            },
            {
                "id": "private",
                "site": "mlp_output",
                "layer": 9,
                "module_path": "model.layers.9.mlp",
                "shape": [1152],
                "publish": False,
                "summary": {"rms": 99.0, "max_abs": 100.0, "mean": 50.0},
            },
        ],
    }

    assert output.emit_token(params(), event).state == "active"
    commands = decoded_strings(process.stdin.lines)
    assert ("s", "/rai/run/token/text", " test") in commands
    assert ("s", "/rai/model/name", "test/gemma") in commands
    assert ("s", "/rai/probes/1/site", "residual_post") in commands
    assert ("f", "/rai/probes/1/rms", "2.5") in commands
    assert ("b", "/rai/probes/2/enabled", "0") in commands
    serialized = "".join(process.stdin.lines)
    assert "99.0" not in serialized
    assert "1151.0" not in serialized
    assert "vector" not in serialized


def test_slots_are_cleared_when_fewer_probes_are_published():
    process = FakeProcess()
    output = OssiaProbeOutput(
        run_id="run-1",
        process_factory=lambda _command: process,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    output.sync(params())
    first = {
        "observation": {"model": "test/gemma"},
        "probes": [
            {"id": "one", "site": "residual_post", "layer": 1, "publish": True, "summary": {"rms": 1.0}},
            {"id": "two", "site": "mlp_output", "layer": 2, "publish": True, "summary": {"rms": 9.0}},
        ],
    }
    output.emit_token(params(), first)
    process.stdin.lines.clear()

    output.emit_token(params(), {**first, "probes": first["probes"][:1]})

    commands = decoded_strings(process.stdin.lines)
    assert ("b", "/rai/probes/2/enabled", "0") in commands
    assert ("s", "/rai/probes/2/id", "") in commands
    assert ("i", "/rai/probes/2/layer", "-1") in commands
    assert ("f", "/rai/probes/2/rms", "0") in commands


def test_sparse_feature_zero_remains_a_valid_top_index():
    process = FakeProcess()
    output = OssiaProbeOutput(
        run_id="run-1",
        process_factory=lambda _command: process,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    output.sync(params())
    output.emit_token(
        params(),
        {
            "probes": [
                {
                    "id": "sae",
                    "site": "sae",
                    "layer": 22,
                    "publish": True,
                    "summary": {"active_count": 1, "top_index": 0, "top_activation": 4.0},
                }
            ]
        },
    )

    assert ("i", "/rai/probes/1/top_index", "0") in decoded_strings(process.stdin.lines)


def test_current_rack_publication_choice_filters_subsequent_output():
    process = FakeProcess()
    output = OssiaProbeOutput(
        run_id="run-1",
        process_factory=lambda _command: process,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    live_params = params(
        probe_rack=[
            {"id": "one", "site": "residual_post", "enabled": True, "publish": False}
        ]
    )
    output.sync(live_params)
    process.stdin.lines.clear()

    output.emit_token(
        live_params,
        {
            "probes": [
                {"id": "one", "site": "residual_post", "layer": 1, "publish": True, "summary": {"rms": 4.0}}
            ]
        },
    )

    commands = decoded_strings(process.stdin.lines)
    assert ("b", "/rai/probes/1/enabled", "0") in commands
    assert ("f", "/rai/probes/1/rms", "4") not in commands


def test_live_disable_and_port_change_stop_or_restart_the_sidecar():
    processes = []

    def factory(command):
        process = FakeProcess()
        process.command = command
        processes.append(process)
        return process

    output = OssiaProbeOutput(
        run_id="run-1",
        process_factory=factory,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    assert output.sync(params()).state == "active"
    assert processes[0].command[-4:] == ["--osc-port", "9010", "--query-port", "5678"]

    assert output.sync(params(ossia_query_port=5679)).state == "active"
    assert processes[0].terminated is True
    assert processes[1].command[-1] == "5679"

    assert output.sync(params(ossia_enabled=False)).state == "disabled"
    assert processes[1].terminated is True


def test_missing_or_broken_libossia_bridge_is_failure_isolated():
    def missing(_command):
        raise FileNotFoundError("bridge missing")

    output = OssiaProbeOutput(
        run_id="run-1",
        process_factory=missing,
        bridge_command=["missing-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    result = output.sync(params())
    assert result.state == "error"
    assert "bridge missing" in result.message

    broken = FakeProcess(fail=True)
    output = OssiaProbeOutput(
        run_id="run-2",
        process_factory=lambda _command: broken,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: True,
    )
    assert output.sync(params()).state == "error"
    assert output.emit_token(params(), {"probes": []}).state == "error"


def test_occupied_ports_fail_before_starting_the_optional_bridge():
    started = False

    def factory(_command):
        nonlocal started
        started = True
        return FakeProcess()

    output = OssiaProbeOutput(
        run_id="collision",
        process_factory=factory,
        bridge_command=["fake-bridge"],
        port_checker=lambda _osc_port, _query_port: False,
    )

    result = output.sync(params())

    assert result.state == "error"
    assert "9010" in result.message
    assert "5678" in result.message
    assert started is False


def test_repository_sidecar_uses_libossia_and_a_stable_read_only_tree():
    repository = Path(__file__).resolve().parents[3]
    source = (repository / "connector" / "ossia_probe_server" / "main.cpp").read_text()
    build_script = (repository / "scripts" / "build_ossia_probe_server.sh").read_text()

    assert "opp::oscquery_server" in source
    assert "set_access(opp::Get)" in source
    assert "for (int slot = 1; slot <= 8; ++slot)" in source
    for field in OSSIA_SLOT_FIELDS:
        assert f'"{field}"' in source
    assert "/home/" not in source
    assert "/home/" not in build_script
    assert "LIBOSSIA_PREFIX" in build_script
    assert "build/ossia-probe-server" in build_script
    assert "libavahi-client.so" in build_script


def test_bridge_environment_exposes_adjacent_zeroconf_runtime(tmp_path):
    bridge = tmp_path / "rai-ossia-probe-server"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "libavahi-client.so").touch()

    environment = bridge_environment([str(bridge)], base_environment={"PATH": "/bin"})

    assert environment["LD_LIBRARY_PATH"].split(":")[0] == str(runtime)
    assert environment["PATH"] == "/bin"
