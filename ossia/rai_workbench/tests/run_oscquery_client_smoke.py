"""Verify installed score reads live bounded values from the libossia sidecar."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY))

from app.server.pipeline.ossia_probe_output import (
    bridge_environment,
    encode_bridge_command,
)
from run_score_smoke import run_score


URL_PLACEHOLDER = "__RAI_OSCQUERY_URL__"


def free_port(socket_type: socket.SocketKind) -> int:
    candidate = socket.socket(socket.AF_INET, socket_type)
    try:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])
    finally:
        candidate.close()


async def wait_for_query_server(port: int, process: subprocess.Popen[str]) -> None:
    for _attempt in range(100):
        if process.poll() is not None:
            error = process.stderr.read() if process.stderr is not None else ""
            raise RuntimeError(f"libossia sidecar exited early: {error}")
        try:
            connection = await asyncio.to_thread(
                socket.create_connection, ("127.0.0.1", port), 0.1
            )
        except OSError:
            await asyncio.sleep(0.05)
            continue
        connection.close()
        return
    raise RuntimeError(f"libossia OSCQuery server did not open TCP {port}")


def write_commands(process: subprocess.Popen[str], rms: float) -> None:
    if process.stdin is None:
        raise RuntimeError("libossia sidecar stdin is unavailable")
    values = {
        "/rai/model/name": "google/gemma-3-270m",
        "/rai/run/token/index": 2,
        "/rai/run/token/text": " glass",
        "/rai/probes/1/enabled": True,
        "/rai/probes/1/id": "residual",
        "/rai/probes/1/site": "residual_post",
        "/rai/probes/1/layer": 17,
        "/rai/probes/1/module_path": "model.layers.17",
        "/rai/probes/1/shape": "640",
        "/rai/probes/1/rms": rms,
        "/rai/probes/1/sequence": 2,
    }
    process.stdin.writelines(
        encode_bridge_command(path, value) for path, value in values.items()
    )
    process.stdin.flush()


def stage_smoke_ui(source: Path, destination: Path, query_port: int) -> Path:
    text = source.read_text(encoding="utf8")
    if text.count(URL_PLACEHOLDER) != 1:
        raise RuntimeError(f"Expected one {URL_PLACEHOLDER} in {source}")
    destination.write_text(
        text.replace(URL_PLACEHOLDER, f"ws://127.0.0.1:{query_port}"),
        encoding="utf8",
    )
    return destination


def assert_result(result: dict) -> None:
    expected = {
        "connected": True,
        "rms": 10.5,
        "model": "google/gemma-3-270m",
        "tokenIndex": 2,
        "tokenText": " glass",
        "enabled": True,
        "site": "residual_post",
        "layer": 17,
        "modulePath": "model.layers.17",
        "shape": "640",
        "sequence": 2,
    }
    if result != expected:
        raise RuntimeError(f"Unexpected OSCQuery score result: {result}")


async def run(score_binary: str, bridge_binary: Path, smoke_ui: Path) -> None:
    if not bridge_binary.is_file():
        raise RuntimeError(
            f"libossia sidecar is missing: {bridge_binary}; "
            "run ./scripts/build_ossia_probe_server.sh"
        )
    osc_port = free_port(socket.SOCK_DGRAM)
    query_port = free_port(socket.SOCK_STREAM)
    command = [
        str(bridge_binary.resolve()),
        "--osc-port",
        str(osc_port),
        "--query-port",
        str(query_port),
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=bridge_environment(command),
    )
    try:
        await wait_for_query_server(query_port, process)
        write_commands(process, 0.5)
        with tempfile.TemporaryDirectory(prefix="rai-oscquery-score-") as path:
            staged_ui = stage_smoke_ui(
                smoke_ui, Path(path) / smoke_ui.name, query_port
            )

            async def update_value() -> None:
                await asyncio.sleep(1.5)
                write_commands(process, 10.5)

            update_task = asyncio.create_task(update_value())
            result = await run_score(
                score_binary,
                staged_ui,
                forbidden_output=(
                    "ReferenceError",
                    "TypeError",
                    "Binding loop detected",
                    "Unable to assign",
                    "Cannot assign",
                ),
            )
            await update_task
        assert_result(result)
        print("SCORE_OSCQUERY_CLIENT_SMOKE_OK", flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-binary", default="ossia-score")
    parser.add_argument(
        "--bridge-binary",
        type=Path,
        default=REPOSITORY
        / "build"
        / "ossia-probe-server"
        / "rai-ossia-probe-server",
    )
    parser.add_argument(
        "--smoke-ui",
        type=Path,
        default=Path(__file__).with_name("oscquery-client-smoke-ui.qml"),
    )
    args = parser.parse_args()
    asyncio.run(run(args.score_binary, args.bridge_binary, args.smoke_ui))


if __name__ == "__main__":
    main()
