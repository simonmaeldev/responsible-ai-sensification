"""Failure-isolated bridge from canonical probe events to a libossia sidecar."""

from __future__ import annotations

import base64
import math
import os
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

MAX_OSCQ_PROBE_SLOTS = 8
OSSIA_SLOT_FIELDS = (
    "enabled",
    "id",
    "site",
    "layer",
    "module_path",
    "shape",
    "rms",
    "max_abs",
    "mean",
    "active_count",
    "top_index",
    "top_activation",
    "sequence",
)


@dataclass(frozen=True)
class OssiaResult:
    state: str
    message: str
    error: str = ""


def _finite_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def encode_bridge_command(path: str, value: Any) -> str:
    """Encode one typed, line-safe update for the C++ libossia process."""
    if isinstance(value, bool):
        return f"b\t{path}\t{1 if value else 0}\n"
    if isinstance(value, int):
        return f"i\t{path}\t{value}\n"
    if isinstance(value, float):
        return f"f\t{path}\t{format(_finite_float(value), '.9g')}\n"
    encoded = base64.b64encode(str(value).encode("utf-8")).decode("ascii")
    return f"s\t{path}\t{encoded}\n"


def default_bridge_command() -> list[str]:
    configured = os.environ.get("RAI_OSSIA_BRIDGE", "").strip()
    if configured:
        return [configured]
    repository = Path(__file__).resolve().parents[3]
    return [str(repository / "build" / "ossia-probe-server" / "rai-ossia-probe-server")]


def bridge_environment(
    command: list[str],
    *,
    base_environment: dict[str, str] | None = None,
) -> dict[str, str]:
    """Expose repository-local optional runtime shims used by libossia."""
    environment = dict(os.environ if base_environment is None else base_environment)
    if not command:
        return environment
    runtime = Path(command[0]).resolve().parent / "runtime"
    if not (runtime / "libavahi-client.so").exists():
        return environment
    previous = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = f"{runtime}:{previous}" if previous else str(runtime)
    return environment


def _start_process(command: list[str]):
    return subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=bridge_environment(command),
    )


def ports_are_available(osc_port: int, query_port: int) -> bool:
    """Check the UDP OSC and TCP OSCQuery listeners before sidecar startup."""
    sockets: list[socket.socket] = []
    try:
        for port, socket_type in (
            (int(osc_port), socket.SOCK_DGRAM),
            (int(query_port), socket.SOCK_STREAM),
        ):
            candidate = socket.socket(socket.AF_INET, socket_type)
            sockets.append(candidate)
            candidate.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        for candidate in sockets:
            candidate.close()


class OssiaProbeOutput:
    """Own one optional libossia OSCQuery server for a model-generation run."""

    def __init__(
        self,
        run_id: str,
        *,
        process_factory: Callable[[list[str]], Any] = _start_process,
        bridge_command: list[str] | None = None,
        port_checker: Callable[[int, int], bool] = ports_are_available,
    ) -> None:
        self.run_id = str(run_id)
        self.process_factory = process_factory
        self.bridge_command = list(bridge_command or default_bridge_command())
        self.port_checker = port_checker
        self.process: Any | None = None
        self.ports: tuple[int, int] | None = None
        self.sequence = 0

    def _write(self, commands: Iterable[str]) -> OssiaResult:
        if self.process is None or self.process.poll() is not None or self.process.stdin is None:
            return OssiaResult("error", "libossia bridge is not running", "bridge not running")
        try:
            for command in commands:
                self.process.stdin.write(command)
            self.process.stdin.flush()
        except Exception as exc:
            self._stop_process()
            return OssiaResult("error", f"libossia bridge output failed: {exc}", str(exc))
        query_port = self.ports[1] if self.ports else 0
        return OssiaResult("active", f"OSCQuery ws://127.0.0.1:{query_port}")

    def _initial_commands(self) -> list[str]:
        commands = [
            encode_bridge_command("/rai/run/id", self.run_id),
            encode_bridge_command("/rai/run/token/index", 0),
            encode_bridge_command("/rai/run/token/text", ""),
            encode_bridge_command("/rai/model/name", ""),
        ]
        for slot in range(1, MAX_OSCQ_PROBE_SLOTS + 1):
            commands.extend(self._neutral_slot_commands(slot))
        return commands

    @staticmethod
    def _neutral_slot_commands(slot: int) -> list[str]:
        prefix = f"/rai/probes/{slot}"
        return [
            encode_bridge_command(f"{prefix}/enabled", False),
            encode_bridge_command(f"{prefix}/id", ""),
            encode_bridge_command(f"{prefix}/site", ""),
            encode_bridge_command(f"{prefix}/layer", -1),
            encode_bridge_command(f"{prefix}/module_path", ""),
            encode_bridge_command(f"{prefix}/shape", ""),
            encode_bridge_command(f"{prefix}/rms", 0.0),
            encode_bridge_command(f"{prefix}/max_abs", 0.0),
            encode_bridge_command(f"{prefix}/mean", 0.0),
            encode_bridge_command(f"{prefix}/active_count", 0),
            encode_bridge_command(f"{prefix}/top_index", -1),
            encode_bridge_command(f"{prefix}/top_activation", 0.0),
            encode_bridge_command(f"{prefix}/sequence", 0),
        ]

    def _stop_process(self) -> None:
        process, self.process = self.process, None
        self.ports = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def sync(self, params: Any) -> OssiaResult:
        """Apply live enable/port changes without touching model generation."""
        if not bool(getattr(params, "ossia_enabled", False)):
            self._stop_process()
            return OssiaResult("disabled", "libossia / OSCQuery disabled")
        osc_port = int(getattr(params, "ossia_osc_port", 9010))
        query_port = int(getattr(params, "ossia_query_port", 5678))
        requested_ports = (osc_port, query_port)
        if (
            self.process is not None
            and self.process.poll() is None
            and self.ports == requested_ports
        ):
            return OssiaResult("active", f"OSCQuery ws://127.0.0.1:{query_port}")

        self._stop_process()
        if not self.port_checker(osc_port, query_port):
            return OssiaResult(
                "error",
                f"libossia ports unavailable (OSC {osc_port}, OSCQuery {query_port})",
                "port collision",
            )
        command = [
            *self.bridge_command,
            "--osc-port",
            str(osc_port),
            "--query-port",
            str(query_port),
        ]
        try:
            self.process = self.process_factory(command)
            self.ports = requested_ports
        except Exception as exc:
            self.process = None
            self.ports = None
            return OssiaResult("error", f"Could not start libossia bridge: {exc}", str(exc))
        return self._write(self._initial_commands())

    def emit_token(self, params: Any, event: dict[str, Any]) -> OssiaResult:
        status = self.sync(params)
        if status.state != "active":
            return status
        self.sequence += 1
        observation = event.get("observation") or {}
        commands = [
            encode_bridge_command("/rai/model/name", observation.get("model", "")),
            encode_bridge_command("/rai/run/token/index", self.sequence),
            encode_bridge_command("/rai/run/token/text", event.get("token", "")),
        ]
        current_rack = getattr(params, "probe_rack", None)
        published_ids = None
        if isinstance(current_rack, list):
            published_ids = {
                str(probe.get("id") or "")
                for probe in current_rack
                if isinstance(probe, dict)
                and probe.get("enabled", True)
                and probe.get("publish", False)
            }
        published = [
            probe
            for probe in (event.get("probes") or [])
            if isinstance(probe, dict)
            and (
                probe.get("id") in published_ids
                if published_ids is not None
                else probe.get("publish", False)
            )
        ][:MAX_OSCQ_PROBE_SLOTS]
        for slot in range(1, MAX_OSCQ_PROBE_SLOTS + 1):
            prefix = f"/rai/probes/{slot}"
            if slot > len(published):
                commands.extend(self._neutral_slot_commands(slot))
                continue
            probe = published[slot - 1]
            summary = probe.get("summary") or {}
            active_count = int(summary.get("active_count", 0) or 0)
            maximum = summary.get("max_abs", summary.get("max_activation", 0.0))
            mean = summary.get("mean")
            if mean is None and active_count:
                mean = _finite_float(summary.get("total_activation")) / active_count
            top_index = summary.get("top_index", -1)
            if top_index is None:
                top_index = -1
            shape = "x".join(str(int(value)) for value in (probe.get("shape") or []))
            commands.extend(
                [
                    encode_bridge_command(f"{prefix}/enabled", True),
                    encode_bridge_command(f"{prefix}/id", probe.get("id", "")),
                    encode_bridge_command(f"{prefix}/site", probe.get("site", "")),
                    encode_bridge_command(f"{prefix}/layer", int(probe.get("layer", -1))),
                    encode_bridge_command(f"{prefix}/module_path", probe.get("module_path", "")),
                    encode_bridge_command(f"{prefix}/shape", shape),
                    encode_bridge_command(f"{prefix}/rms", _finite_float(summary.get("rms"))),
                    encode_bridge_command(f"{prefix}/max_abs", _finite_float(maximum)),
                    encode_bridge_command(f"{prefix}/mean", _finite_float(mean)),
                    encode_bridge_command(f"{prefix}/active_count", active_count),
                    encode_bridge_command(f"{prefix}/top_index", int(top_index)),
                    encode_bridge_command(f"{prefix}/top_activation", _finite_float(summary.get("top_activation"))),
                    encode_bridge_command(f"{prefix}/sequence", self.sequence),
                ]
            )
        return self._write(commands)

    def close(self) -> OssiaResult:
        self._stop_process()
        return OssiaResult("disabled", "libossia / OSCQuery stopped")
