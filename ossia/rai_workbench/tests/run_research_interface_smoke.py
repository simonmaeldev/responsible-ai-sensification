"""Exercise Slice 4 scalar patching, history, and live controls through score."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
import tempfile

from research_fixture_server import run_research_fixture
from run_interface_smoke import stage_score_document
from run_score_smoke import run_score


EXPECTED_RESULT = {
    "sawLoading": True,
    "sawRunning": True,
    "sawDone": True,
    "connectionState": "ready",
    "runState": "stopped",
    "runError": "",
    "historyCount": 2,
    "inspectedHistoryIndex": 0,
    "followingLatest": False,
    "currentTokenText": " glass",
    "currentTokenId": 421,
    "currentObservationLayer": 7,
    "requestedObservationLayer": 7,
    "firstTokenText": " bell",
    "firstTokenId": 420,
    "firstTokenIndex": 1,
    "firstModelName": "google/gemma-3-1b-pt",
    "firstModelType": "gemma3_text",
    "firstObservationSite": "residual_post",
    "firstObservationLayer": 22,
    "firstSaeLayer": 22,
    "firstDenseModulePath": "model.layers.22",
    "firstDenseShape": "[1152]",
    "firstDenseDtype": "float32",
    "firstDenseRepresentation": "dense_residual",
    "firstSaeModulePath": "gemma_scope.resid_post.layer_22.width_65k",
    "firstSaeShape": "[65536]",
    "firstSaeDtype": "sparse_float32",
    "firstSaeRepresentation": "sparse_sae",
    "firstFeatureIndex": 3,
    "firstFeatureActivation": 2.25,
    "firstFeatureDescription": "bells",
    "firstProbeSlots": 8,
    "firstProbeId": "residual",
    "firstProbeModel": "google/gemma-3-1b-pt",
    "firstProbeSite": "residual_post",
    "firstProbeLayer": 22,
    "firstProbeTokenIndex": 1,
    "firstProbeModulePath": "model.layers.22",
    "firstProbeShape": "[1152]",
    "firstProbeDtype": "float32",
    "firstProbeRepresentation": "dense_tensor_summary",
    "firstProbeRms": 0.5,
    "firstProbeMaxAbs": 1.5,
    "firstSaeProbeSite": "sae",
    "firstSaeProbeLayer": 22,
    "firstSaeProbeModulePath": "gemma_scope.resid_post.layer_22.width_65k",
    "firstSaeProbeShape": "[65536]",
    "firstSaeProbeDtype": "sparse_float32",
    "firstSaeProbeRepresentation": "sparse_sae_summary",
    "firstSaeProbeActiveCount": 2,
    "firstSaeProbeTopIndex": 3,
    "firstSaeProbeTopActivation": 2.25,
    "firstBlockDelta": 0.1,
    "firstPatchableCount": 4,
    "firstTensorRms": 0.5,
    "firstTensorPeak": 1.5,
    "firstSaeActiveCount": 2,
    "firstSaeTopActivation": 2.25,
    "firstScalarModel": "google/gemma-3-1b-pt",
    "firstScalarTokenIndex": 1,
    "firstScalarTokenId": 420,
    "firstScalarTokenText": " bell",
    "firstScalarSite": "residual_post",
    "firstScalarLayer": 22,
    "firstScalarModulePath": "model.layers.22",
    "firstScalarShape": "[1152]",
    "firstScalarDtype": "float32",
    "firstScalarRepresentation": "dense_tensor_summary",
    "firstSaeFeatureIndex": 3,
    "secondTokenText": " glass",
    "secondObservationLayer": 7,
    "secondDenseModulePath": "model.layers.7",
    "secondSaeLayer": 22,
    "secondSaeModulePath": "gemma_scope.resid_post.layer_22.width_65k",
    "secondFeatureIndex": 8,
    "secondFeatureDescription": "glass surfaces",
    "secondProbeLayer": 7,
    "secondProbeModulePath": "model.layers.7",
    "secondProbeRms": 10.5,
    "secondBlockDelta": 10.1,
    "secondTensorRms": 10.5,
    "secondTensorLayer": 7,
    "secondTensorModulePath": "model.layers.7",
    "secondSaeTopActivation": 3.5,
    "secondSaeFeatureIndex": 8,
    "secondSaeProbeTopActivation": 3.5,
    "inspectedTokenText": " bell",
    "inspectedObservationLayer": 22,
    "inspectedTensorRms": 0.5,
    "exampleMappedValue": 10.5,
    "modelLayerCount": 26,
    "blockOneAttention": "sliding_attention",
    "blockSixAttention": "full_attention",
}

EXAMPLE_PROCESS_NAME = "EXAMPLE_patchable_tensor_rms_delete_safe"


def remove_example_mapping(score_document: Path) -> None:
    """Remove only the labelled example process from a staged score document."""
    document = json.loads(score_document.read_text(encoding="utf8"))
    interval = document["Document"]["BaseScenario"]["Constraint"]
    removed_ids = {
        process["id"]
        for process in interval["Processes"]
        if process.get("Metadata", {}).get("ScriptingName")
        == EXAMPLE_PROCESS_NAME
    }
    if len(removed_ids) != 1:
        raise RuntimeError(
            f"Expected exactly one removable example process; got {removed_ids}"
        )
    interval["Processes"] = [
        process
        for process in interval["Processes"]
        if process.get("id") not in removed_ids
    ]
    interval["SmallViewRack"] = [
        slot
        for slot in interval["SmallViewRack"]
        if not removed_ids.intersection(slot.get("Processes", []))
    ]
    interval["FullViewRack"] = [
        slot
        for slot in interval["FullViewRack"]
        if slot.get("Process") not in removed_ids
    ]
    score_document.write_text(json.dumps(document), encoding="utf8")


def assert_result(result: dict, example_enabled: bool) -> None:
    for key, expected in EXPECTED_RESULT.items():
        if key == "exampleMappedValue" and not example_enabled:
            continue
        actual = result.get(key)
        if isinstance(expected, float):
            if not isinstance(actual, (int, float)) or not math.isclose(
                actual,
                expected,
                rel_tol=1e-6,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Unexpected research interface field {key}: {actual}; "
                    f"expected {expected}"
                )
        elif actual != expected:
            raise RuntimeError(
                f"Unexpected research interface field {key}: {actual}; "
                f"expected {expected}"
            )
    if not example_enabled and math.isclose(
        result.get("exampleMappedValue", -1),
        EXPECTED_RESULT["exampleMappedValue"],
        rel_tol=1e-6,
        abs_tol=1e-6,
    ):
        raise RuntimeError("Removed example process still received the scalar")
    if set(result) != set(EXPECTED_RESULT):
        raise RuntimeError(f"Unexpected research interface result keys: {result}")


async def run(
    score_binary: str,
    smoke_ui: Path,
    score_document: Path,
    debug: bool,
    without_example: bool,
) -> None:
    ready = asyncio.get_running_loop().create_future()
    fixture_task = asyncio.create_task(
        run_research_fixture("127.0.0.1", 0, ready)
    )
    try:
        done, _ = await asyncio.wait(
            {fixture_task, ready},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if fixture_task in done:
            await fixture_task
        port = ready.result()

        with tempfile.TemporaryDirectory(prefix="rai-research-interface-") as path:
            staged_document = Path(path) / "rai-workbench.score"
            stage_score_document(score_document, staged_document, port)
            if without_example:
                remove_example_mapping(staged_document)
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
        assert_result(result, example_enabled=not without_example)
        await fixture_task
        mode = "UI_DEBUG" if debug else "UI"
        suffix = "_NO_EXAMPLE" if without_example else ""
        print(f"SCORE_RESEARCH_INTERFACE_{mode}{suffix}_OK", flush=True)
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
        default=Path(__file__).with_name("research-interface-smoke-ui.qml"),
    )
    parser.add_argument(
        "--score-document",
        type=Path,
        default=workbench / "rai-workbench.score",
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--without-example", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        run(
            args.score_binary,
            args.smoke_ui,
            args.score_document,
            args.debug,
            args.without_example,
        )
    )


if __name__ == "__main__":
    main()
