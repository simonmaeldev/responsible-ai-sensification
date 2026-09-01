"""Capture deterministic Slice 4 evidence through installed ossia score."""

from __future__ import annotations

import argparse
import asyncio
import math
from pathlib import Path
import shutil
import struct
import tempfile

from research_fixture_server import run_research_fixture
from run_interface_smoke import stage_score_document
from run_score_smoke import run_score


CAPTURE_PLACEHOLDER = "__RAI_CAPTURE_PATH__"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def qml_string_content(value: str) -> str:
    """Escape a path for replacement inside an existing QML string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def stage_capture_ui(source: Path, workbench: Path, destination: Path, output: Path) -> Path:
    """Stage the capture QML with its relative interface dependency."""
    source_text = source.read_text(encoding="utf8")
    if source_text.count(CAPTURE_PLACEHOLDER) != 1:
        raise RuntimeError(f"Expected one {CAPTURE_PLACEHOLDER} in {source}")
    tests_directory = destination / "tests"
    tests_directory.mkdir(parents=True)
    staged_ui = tests_directory / source.name
    staged_ui.write_text(
        source_text.replace(CAPTURE_PLACEHOLDER, qml_string_content(str(output))),
        encoding="utf8",
    )
    shutil.copyfile(workbench / "interface.qml", destination / "interface.qml")
    return staged_ui


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read the dimensions from a PNG IHDR without adding an image dependency."""
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise RuntimeError(f"Capture is not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def assert_result(result: dict, output: Path) -> None:
    expected = {
        "saved": True,
        "capturePath": str(output),
        "historyCount": 2,
        "tokenText": " glass",
        "observationLayer": 7,
        "backendScalar": 10.5,
        "exampleMappedValue": 10.5,
    }
    for key, expected_value in expected.items():
        actual = result.get(key)
        if isinstance(expected_value, float):
            if not isinstance(actual, (int, float)) or not math.isclose(
                actual, expected_value, rel_tol=1e-6, abs_tol=1e-6
            ):
                raise RuntimeError(
                    f"Unexpected capture field {key}: {actual}; expected {expected_value}"
                )
        elif actual != expected_value:
            raise RuntimeError(
                f"Unexpected capture field {key}: {actual}; expected {expected_value}"
            )
    dimensions = png_dimensions(output)
    if dimensions != (1440, 900):
        raise RuntimeError(f"Unexpected capture dimensions: {dimensions}")


async def run(score_binary: str, capture_ui: Path, score_document: Path, output: Path) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ready = asyncio.get_running_loop().create_future()
    fixture_task = asyncio.create_task(run_research_fixture("127.0.0.1", 0, ready))
    try:
        done, _ = await asyncio.wait(
            {fixture_task, ready}, return_when=asyncio.FIRST_COMPLETED
        )
        if fixture_task in done:
            await fixture_task
        port = ready.result()

        with tempfile.TemporaryDirectory(prefix="rai-score-capture-") as path:
            staged_workbench = Path(path) / "rai_workbench"
            staged_workbench.mkdir()
            staged_ui = stage_capture_ui(
                capture_ui, score_document.parent, staged_workbench, output
            )
            staged_document = staged_workbench / "rai-workbench.score"
            stage_score_document(score_document, staged_document, port)
            result = await run_score(
                score_binary,
                staged_ui,
                score_document=staged_document,
                forbidden_output=(
                    "ReferenceError",
                    "TypeError",
                    "Binding loop detected",
                    "Unable to assign",
                    "Cannot assign",
                ),
            )
        assert_result(result, output)
        await fixture_task
        print(f"SCORE_INTERFACE_CAPTURE_OK {output}", flush=True)
    except Exception:
        fixture_task.cancel()
        try:
            await fixture_task
        except asyncio.CancelledError:
            pass
        raise


def main() -> None:
    workbench = Path(__file__).resolve().parents[1]
    repository = workbench.parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-binary", default="ossia-score")
    parser.add_argument(
        "--capture-ui",
        type=Path,
        default=Path(__file__).with_name("capture-interface-ui.qml"),
    )
    parser.add_argument(
        "--score-document", type=Path, default=workbench / "rai-workbench.score"
    )
    parser.add_argument(
        "--output", type=Path, default=repository / "runs" / "ossia-score-slice4.png"
    )
    args = parser.parse_args()
    asyncio.run(
        run(args.score_binary, args.capture_ui, args.score_document, args.output)
    )


if __name__ == "__main__":
    main()
