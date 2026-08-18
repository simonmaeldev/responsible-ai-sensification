"""Run one real Gemma/SAE/Neuronpedia token through installed score."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Callable

from run_score_smoke import run_score


def assert_real_result(result: dict) -> None:
    if result.get("runError"):
        raise RuntimeError(f"Real score run failed: {result['runError']}")
    for state in ("sawLoading", "sawRunning", "sawDone"):
        if result.get(state) is not True:
            raise RuntimeError(f"Real score run did not reach {state}: {result}")
    if not str(result.get("modelName", "")).startswith("google/gemma-3"):
        raise RuntimeError(f"Real score run did not report Gemma: {result}")
    if not result.get("probeId"):
        raise RuntimeError(f"Real score run did not expose a probe: {result}")
    if not isinstance(result.get("featureIndex"), int) or result["featureIndex"] < 0:
        raise RuntimeError(f"Real score run did not expose an SAE feature: {result}")
    if not result.get("featureDescription"):
        raise RuntimeError(
            f"Real score run did not expose a Neuronpedia description: {result}"
        )


async def drain_server_output(
    server_process: asyncio.subprocess.Process,
    server_lines: list[str],
) -> None:
    while True:
        line_bytes = await server_process.stdout.readline()
        if not line_bytes:
            return
        line = line_bytes.decode(errors="replace").rstrip()
        server_lines.append(line)
        if "error" in line.lower() or "loading" in line.lower():
            print("SERVER " + line, flush=True)


async def run_real(
    score_binary: str,
    smoke_ui: Path,
    start_script: Path,
    score_document: Path | None = None,
    result_assertion: Callable[[dict], None] = assert_real_result,
    success_marker: str = "SCORE_REAL_SMOKE_OK",
) -> None:
    server_process = await asyncio.create_subprocess_exec(
        str(start_script.resolve()),
        "--no-browser",
        cwd=str(start_script.resolve().parents[1]),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    server_lines: list[str] = []
    drain_task: asyncio.Task | None = None

    try:
        async with asyncio.timeout(45):
            while True:
                line_bytes = await server_process.stdout.readline()
                if not line_bytes:
                    raise RuntimeError(
                        f"FastAPI server exited early: {server_process.returncode}"
                    )
                line = line_bytes.decode(errors="replace").rstrip()
                server_lines.append(line)
                print("SERVER " + line, flush=True)
                if "Uvicorn running" in line:
                    break

        drain_task = asyncio.create_task(
            drain_server_output(server_process, server_lines)
        )
        result = await run_score(
            score_binary,
            smoke_ui,
            timeout=600,
            score_document=score_document,
            forbidden_output=(
                "ReferenceError",
                "TypeError",
                "Binding loop detected",
                "Unable to assign",
                "Cannot assign",
            ),
        )
        result_assertion(result)
        print(success_marker, flush=True)
    except Exception:
        diagnostic = "\n".join(server_lines[-100:])
        if diagnostic:
            print("SERVER_DIAGNOSTIC\n" + diagnostic, flush=True)
        raise
    finally:
        if server_process.returncode is None:
            server_process.terminate()
            try:
                await asyncio.wait_for(server_process.wait(), timeout=10)
            except TimeoutError:
                server_process.kill()
                await asyncio.wait_for(server_process.wait(), timeout=5)
        if drain_task is not None:
            await drain_task


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
    parser.add_argument(
        "--start-script",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "scripts" / "start.sh",
    )
    args = parser.parse_args()
    asyncio.run(run_real(args.score_binary, args.smoke_ui, args.start_script))


if __name__ == "__main__":
    main()
