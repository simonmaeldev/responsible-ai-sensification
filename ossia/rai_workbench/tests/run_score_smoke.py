"""Run the deterministic Phase 1 smoke test through installed ossia score."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from fixture_server import run_fixture


RESULT_MARKER = "RAI_SCORE_SMOKE_RESULT "
DEFAULT_WEBSOCKET_URL = "ws://127.0.0.1:8080/ws/stream"


def parse_result(output: str) -> dict:
    for line in output.splitlines():
        marker_index = line.find(RESULT_MARKER)
        if marker_index >= 0:
            return json.loads(line[marker_index + len(RESULT_MARKER) :])
    raise RuntimeError("score did not report a smoke-test result")


def assert_result(result: dict) -> None:
    expected = {
        "sawLoading": True,
        "sawRunning": True,
        "sawDone": True,
        "runError": "",
        "loadingLabel": "Sparse autoencoder",
        "loadingProgress": 0.5,
        "tokenText": " bell",
        "modelName": "google/gemma-3-1b-it",
        "probeId": "residual-17",
        "featureIndex": 3,
        "featureDescription": "bells",
    }
    if result != expected:
        raise RuntimeError(f"Unexpected score smoke-test result: {result}")


async def run_score(
    score_binary: str,
    smoke_ui: Path,
    timeout: float = 45,
) -> dict:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"

    score_process = await asyncio.create_subprocess_exec(
        score_binary,
        "--no-restore",
        "--no-opengl",
        "--ui",
        str(smoke_ui.resolve()),
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    try:
        output_lines: list[str] = []
        try:
            async with asyncio.timeout(timeout):
                while True:
                    line_bytes = await score_process.stdout.readline()
                    if not line_bytes:
                        raise RuntimeError(
                            f"score exited before reporting a result: "
                            f"{score_process.returncode}"
                        )
                    line = line_bytes.decode(errors="replace").rstrip()
                    output_lines.append(line)
                    if RESULT_MARKER in line:
                        break
        except TimeoutError as exc:
            diagnostic = "\n".join(output_lines[-80:])
            raise RuntimeError(
                "score smoke test timed out\n" + diagnostic
            ) from exc
        output = "\n".join(output_lines)
        for line in output_lines:
            if "RAI_SCORE_SMOKE" in line:
                print(line, flush=True)
        return parse_result(output)
    finally:
        if score_process.returncode is None:
            score_process.terminate()
            try:
                await asyncio.wait_for(score_process.wait(), timeout=5)
            except TimeoutError:
                score_process.kill()
                await asyncio.wait_for(score_process.wait(), timeout=5)


def stage_smoke_ui(smoke_ui: Path, port: int, directory: Path) -> Path:
    """Copy the smoke UI and device to a temporary, collision-free endpoint."""
    source = smoke_ui.read_text(encoding="utf8")
    if source.count(DEFAULT_WEBSOCKET_URL) != 1:
        raise RuntimeError(
            f"Expected one {DEFAULT_WEBSOCKET_URL} in {smoke_ui}"
        )

    tests_directory = directory / "tests"
    tests_directory.mkdir()
    staged_ui = tests_directory / smoke_ui.name
    staged_ui.write_text(
        source.replace(
            DEFAULT_WEBSOCKET_URL,
            f"ws://127.0.0.1:{port}/ws/stream",
        ),
        encoding="utf8",
    )

    device_qml = Path(__file__).resolve().parents[1] / "websocket-device.qml"
    (directory / "websocket-device.qml").write_text(
        device_qml.read_text(encoding="utf8"),
        encoding="utf8",
    )
    return staged_ui


async def run(
    score_binary: str,
    smoke_ui: Path,
) -> None:
    ready = asyncio.get_running_loop().create_future()
    fixture_task = asyncio.create_task(run_fixture("127.0.0.1", 0, ready))
    try:
        done, _ = await asyncio.wait(
            {fixture_task, ready},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if fixture_task in done:
            await fixture_task
        port = ready.result()

        with tempfile.TemporaryDirectory(prefix="rai-score-smoke-") as path:
            staged_ui = stage_smoke_ui(smoke_ui, port, Path(path))
            result = await run_score(score_binary, staged_ui)
        assert_result(result)
        await fixture_task
        print("SCORE_SMOKE_OK", flush=True)
    except Exception:
        fixture_task.cancel()
        try:
            await fixture_task
        except asyncio.CancelledError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--score-binary",
        default="ossia-score",
        help="Installed ossia score executable (default: ossia-score)",
    )
    parser.add_argument(
        "--smoke-ui",
        type=Path,
        default=Path(__file__).with_name("score-smoke-ui.qml"),
    )
    args = parser.parse_args()
    asyncio.run(run(args.score_binary, args.smoke_ui))


if __name__ == "__main__":
    main()
