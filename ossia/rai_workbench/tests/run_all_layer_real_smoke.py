"""Run the official Gemma 3 270M all-layer SAE example through installed score."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from run_score_real_smoke import run_real


MODEL_ID = "google/gemma-3-270m"
SAE_REPO_ID = "google/gemma-scope-2-270m-pt"
EXPECTED_LAYERS = (0, 8, 17)


def _require(condition: bool, message: str, result: dict) -> None:
    if not condition:
        raise RuntimeError(f"{message}: {result}")


def assert_all_layer_real_result(result: dict) -> None:
    """Compare score state with the browser WebSocket observation contract."""
    _require(not result.get("runError"), "All-layer run failed", result)
    for state in ("sawLoading", "sawRunning", "sawDone"):
        _require(result.get(state) is True, f"Run did not reach {state}", result)
    _require(result.get("connectionState") == "ready", "Interface did not connect", result)
    _require(result.get("runState") == "stopped", "Interface did not stop", result)
    _require(result.get("runModel") == MODEL_ID, "Score did not request 270M", result)
    _require(result.get("modelName") == MODEL_ID, "Backend did not report 270M", result)
    _require(result.get("modelType") == "gemma3_text", "Wrong model type", result)
    _require(result.get("modelLayerCount") == 18, "Wrong block count", result)
    _require(result.get("historyCount") == 3, "Token history is not synchronized", result)
    _require(result.get("requestedObservationLayer") == 17, "Dense request is stale", result)
    _require(result.get("requestedSaeLayer") == 17, "SAE request is stale", result)
    _require(result.get("inspectedHistoryIndex") == 0, "History selection failed", result)
    _require(
        result.get("inspectedTokenText") == result.get("firstTokenText"),
        "Historical token changed",
        result,
    )
    _require(result.get("blockOneAttention") == "sliding_attention", "Wrong block 1 type", result)
    _require(result.get("blockSixAttention") == "full_attention", "Wrong block 6 type", result)
    _require(result.get("blockEighteenAttention") == "full_attention", "Wrong block 18 type", result)

    revisions: set[str] = set()
    for prefix, layer in zip(("first", "second", "third"), EXPECTED_LAYERS):
        expected_dense = f"model.layers.{layer}"
        expected_sae = f"gemma_scope.resid_post_all.layer_{layer}.width_16k"
        _require(result.get(prefix + "ObservationLayer") == layer, "Dense layer did not move", result)
        _require(result.get(prefix + "DenseModulePath") == expected_dense, "Wrong dense module", result)
        _require(result.get(prefix + "SaeLayer") == layer, "Matching SAE did not move", result)
        _require(result.get(prefix + "SaeModulePath") == expected_sae, "Wrong SAE module", result)
        _require(result.get(prefix + "SaeShape") == "[16384]", "Wrong SAE shape", result)
        _require(result.get(prefix + "SaeDtype") == "sparse_float32", "Wrong SAE dtype", result)
        _require(result.get(prefix + "SaeRepresentation") == "sparse_sae", "Wrong SAE representation", result)
        _require(result.get(prefix + "SaeWidth") == "16k", "Wrong SAE width", result)
        _require(result.get(prefix + "SaeL0") == "small", "Wrong SAE L0", result)
        _require(result.get(prefix + "SaeCategory") == "resid_post_all", "Wrong SAE family", result)
        _require(result.get(prefix + "SaeRepoId") == SAE_REPO_ID, "Wrong SAE repository", result)
        revision = result.get(prefix + "SaeRevision")
        _require(isinstance(revision, str) and bool(revision), "Missing SAE revision", result)
        revisions.add(revision)
        _require(result.get(prefix + "FeatureDescription") == "", "Borrowed semantic label", result)
        _require(result.get(prefix + "DenseProbeLayer") == layer, "Dense probe is stale", result)
        _require(result.get(prefix + "TensorScalarLayer") == layer, "Scalar layer is stale", result)
        _require(
            result.get(prefix + "TensorScalar") == result.get(prefix + "DenseProbeRms"),
            "Tensor scalar changed from backend event",
            result,
        )
        _require(result.get(prefix + "SparseProbeLayer") == layer, "SAE probe is stale", result)
        _require(
            result.get(prefix + "SparseScalar")
            == result.get(prefix + "SparseProbeTopActivation"),
            "SAE scalar changed from backend event",
            result,
        )
        _require(
            result.get(prefix + "SparseFeatureIndex")
            == result.get(prefix + "SparseProbeTopIndex"),
            "SAE feature identifier changed",
            result,
        )
        _require(isinstance(result.get(prefix + "TokenId"), int), "Missing token ID", result)
        _require(bool(result.get(prefix + "TokenText")), "Missing token text", result)

    _require(len(revisions) == 1, "Layer SAEs did not share an exact snapshot", result)
    _require(
        result.get("exampleMappedValue") == result.get("thirdTensorScalar"),
        "Normal Float process did not receive the latest unchanged scalar",
        result,
    )


def main() -> None:
    workbench = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-binary", default="ossia-score")
    parser.add_argument(
        "--smoke-ui",
        type=Path,
        default=Path(__file__).with_name("all-layer-real-smoke-ui.qml"),
    )
    parser.add_argument(
        "--score-document",
        type=Path,
        default=workbench / "rai-workbench.score",
    )
    parser.add_argument(
        "--start-script",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "scripts" / "start.sh",
    )
    args = parser.parse_args()
    asyncio.run(
        run_real(
            args.score_binary,
            args.smoke_ui,
            args.start_script,
            score_document=args.score_document,
            result_assertion=assert_all_layer_real_result,
            success_marker="SCORE_ALL_LAYER_REAL_OK",
        )
    )


if __name__ == "__main__":
    main()
