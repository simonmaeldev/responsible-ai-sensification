"""Exercise synchronized Slice 3 history and live controls through score."""

from __future__ import annotations

import argparse
import asyncio
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
    "firstSaeProbeSite": "sae",
    "firstSaeProbeLayer": 22,
    "firstSaeProbeModulePath": "gemma_scope.resid_post.layer_22.width_65k",
    "firstSaeProbeShape": "[65536]",
    "firstSaeProbeDtype": "sparse_float32",
    "firstSaeProbeRepresentation": "sparse_sae_summary",
    "firstBlockDelta": 0.1,
    "secondTokenText": " glass",
    "secondObservationLayer": 7,
    "secondDenseModulePath": "model.layers.7",
    "secondSaeLayer": 22,
    "secondSaeModulePath": "gemma_scope.resid_post.layer_22.width_65k",
    "secondFeatureIndex": 8,
    "secondFeatureDescription": "glass surfaces",
    "secondProbeLayer": 7,
    "secondProbeModulePath": "model.layers.7",
    "secondBlockDelta": 10.1,
    "inspectedTokenText": " bell",
    "inspectedObservationLayer": 22,
    "modelLayerCount": 26,
    "blockOneAttention": "sliding_attention",
    "blockSixAttention": "full_attention",
}


def assert_result(result: dict) -> None:
    for key, expected in EXPECTED_RESULT.items():
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
    if set(result) != set(EXPECTED_RESULT):
        raise RuntimeError(f"Unexpected research interface result keys: {result}")


async def run(
    score_binary: str,
    smoke_ui: Path,
    score_document: Path,
    debug: bool,
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
        print(f"SCORE_RESEARCH_INTERFACE_{mode}_OK", flush=True)
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
