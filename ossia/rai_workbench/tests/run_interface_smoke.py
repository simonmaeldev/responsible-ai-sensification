"""Exercise the Phase 2 custom interface through installed ossia score."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import tempfile

from fixture_server import run_fixture
from run_score_smoke import run_score


EXPECTED_RESULT = {
    "sawLoading": True,
    "sawRunning": True,
    "sawDone": True,
    "connectionState": "ready",
    "runState": "stopped",
    "runError": "",
    "promptValue": "Phase 2 interface smoke",
    "maxTokensValue": 1,
    "loadingLabel": "Sparse autoencoder",
    "loadingProgress": 0.5,
    "tokenText": " bell",
    "tokenId": 420,
    "featureCount": 12,
    "featureIndex": 3,
    "featureActivation": 2.25,
    "featureDescription": "bells",
    "secondFeatureIndex": 8,
}


def replace_device_address(value: object, websocket_url: str) -> bool:
    """Replace the generated WebSocket device address in a score JSON tree."""
    if isinstance(value, dict):
        device = value.get("Device")
        if isinstance(device, dict) and device.get("Name") == "RAI Workbench":
            device["Address"] = websocket_url
            return True
        return any(
            replace_device_address(child, websocket_url)
            for child in value.values()
        )
    if isinstance(value, list):
        return any(replace_device_address(child, websocket_url) for child in value)
    return False


def stage_score_document(source: Path, destination: Path, port: int) -> None:
    document = json.loads(source.read_text(encoding="utf8"))
    websocket_url = f"ws://127.0.0.1:{port}/ws/stream"
    if not replace_device_address(document, websocket_url):
        raise RuntimeError("RAI Workbench device is missing from score document")
    destination.write_text(json.dumps(document), encoding="utf8")


def assert_result(result: dict) -> None:
    if result != EXPECTED_RESULT:
        raise RuntimeError(f"Unexpected interface smoke-test result: {result}")


async def run(
    score_binary: str,
    smoke_ui: Path,
    score_document: Path,
    debug: bool,
) -> None:
    ready = asyncio.get_running_loop().create_future()
    fixture_task = asyncio.create_task(
        run_fixture(
            "127.0.0.1",
            0,
            ready,
            expected_prompt="Phase 2 interface smoke",
        )
    )
    try:
        done, _ = await asyncio.wait(
            {fixture_task, ready},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if fixture_task in done:
            await fixture_task
        port = ready.result()

        with tempfile.TemporaryDirectory(prefix="rai-interface-smoke-") as path:
            staged_document = Path(path) / "rai-workbench.score"
            stage_score_document(score_document, staged_document, port)
            result = await run_score(
                score_binary,
                smoke_ui,
                score_document=staged_document,
                ui_flag="--ui-debug" if debug else "--ui",
                forbidden_output=(
                    "ReferenceError",
                    "TypeError",
                    "Binding loop detected",
                    "Unable to assign",
                    "Cannot assign",
                ),
            )
        assert_result(result)
        await fixture_task
        mode = "UI_DEBUG" if debug else "UI"
        print(f"SCORE_INTERFACE_SMOKE_{mode}_OK", flush=True)
    except Exception:
        fixture_task.cancel()
        try:
            await fixture_task
        except asyncio.CancelledError:
            pass
        raise


def main() -> None:
    workbench = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-binary", default="ossia-score")
    parser.add_argument(
        "--smoke-ui",
        type=Path,
        default=Path(__file__).with_name("interface-smoke-ui.qml"),
    )
    parser.add_argument(
        "--score-document",
        type=Path,
        default=workbench / "rai-workbench.score",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        run(
            args.score_binary,
            args.smoke_ui,
            args.score_document,
            args.debug,
        )
    )


if __name__ == "__main__":
    main()
