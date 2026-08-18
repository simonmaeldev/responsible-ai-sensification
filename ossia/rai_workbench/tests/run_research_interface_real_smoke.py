"""Run two real Gemma tokens through the Slice 3 score interface."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from run_score_real_smoke import run_real


def _require(condition: bool, message: str, result: dict) -> None:
    if not condition:
        raise RuntimeError(f"{message}: {result}")


def assert_research_real_result(result: dict) -> None:
    """Check the score view against the real browser WebSocket provenance contract."""
    _require(not result.get("runError"), "Real research interface failed", result)
    for state in ("sawLoading", "sawRunning", "sawDone"):
        _require(result.get(state) is True, f"Run did not reach {state}", result)
    _require(result.get("connectionState") == "ready", "Interface did not connect", result)
    _require(result.get("runState") == "stopped", "Interface did not stop", result)

    _require(result.get("historyCount") == 2, "History is not two synchronized tokens", result)
    _require(result.get("inspectedHistoryIndex") == 0, "First history item was not selected", result)
    _require(result.get("followingLatest") is False, "History selection did not pause follow mode", result)
    _require(result.get("inspectedTokenText") == result.get("firstTokenText"), "History token text changed", result)
    _require(result.get("inspectedObservationLayer") == 22, "History provenance changed", result)

    model = result.get("firstModelName", "")
    _require(str(model).startswith("google/gemma-3"), "Run did not report Gemma", result)
    _require(result.get("firstModelType") == "gemma3_text", "Wrong model type", result)
    _require(result.get("modelLayerCount") == 26, "Wrong Gemma block count", result)
    _require(result.get("blockOneAttention") == "sliding_attention", "Wrong local-attention map", result)
    _require(result.get("blockSixAttention") == "full_attention", "Wrong global-attention map", result)

    _require(result.get("firstObservationSite") == "residual_post", "Wrong dense site", result)
    _require(result.get("firstObservationLayer") == 22, "Wrong first dense layer", result)
    _require(result.get("secondObservationLayer") == 7, "Live dense layer change did not apply", result)
    _require(result.get("currentObservationLayer") == 7, "Live dense layer is stale", result)
    _require(result.get("requestedObservationLayer") == 7, "Dense control is stale", result)
    _require(result.get("firstDenseModulePath") == "model.layers.22", "Wrong first dense module", result)
    _require(result.get("secondDenseModulePath") == "model.layers.7", "Wrong second dense module", result)
    _require(result.get("firstDenseShape") == "[1152]", "Wrong dense shape", result)
    _require(result.get("firstDenseDtype") == "float32", "Wrong dense dtype", result)
    _require(result.get("firstDenseRepresentation") == "dense_residual", "Wrong dense representation", result)

    fixed_sae_path = "gemma_scope.resid_post.layer_22.width_65k"
    _require(result.get("firstSaeLayer") == 22, "Wrong first SAE layer", result)
    _require(result.get("secondSaeLayer") == 22, "SAE layer moved with dense observation", result)
    _require(result.get("firstSaeModulePath") == fixed_sae_path, "Wrong SAE module", result)
    _require(result.get("secondSaeModulePath") == fixed_sae_path, "SAE module moved", result)
    _require(result.get("firstSaeShape") == "[65536]", "Wrong SAE shape", result)
    _require(result.get("firstSaeDtype") == "sparse_float32", "Wrong SAE dtype", result)
    _require(result.get("firstSaeRepresentation") == "sparse_sae", "Wrong SAE representation", result)

    _require(isinstance(result.get("firstTokenId"), int) and result["firstTokenId"] >= 0, "Missing token ID", result)
    _require(isinstance(result.get("firstTokenIndex"), int) and result["firstTokenIndex"] >= 0, "Missing token index", result)
    _require(bool(result.get("firstTokenText")), "Missing first token text", result)
    _require(bool(result.get("secondTokenText")), "Missing second token text", result)
    _require(result.get("currentTokenText") == result.get("secondTokenText"), "Current token is not latest", result)

    _require(isinstance(result.get("firstFeatureIndex"), int) and result["firstFeatureIndex"] >= 0, "Missing SAE feature", result)
    _require(isinstance(result.get("firstFeatureActivation"), (int, float)) and result["firstFeatureActivation"] > 0, "Inactive SAE feature", result)
    _require(bool(result.get("firstFeatureDescription")), "Missing Neuronpedia evidence", result)
    _require(bool(result.get("secondFeatureDescription")), "Missing second-token Neuronpedia evidence", result)

    _require(result.get("firstProbeSlots") == 8, "Probe summary tree is not bounded to eight slots", result)
    _require(result.get("firstProbeId") == "residual", "Wrong first probe", result)
    _require(result.get("firstProbeModel") == model, "Probe model provenance changed", result)
    _require(result.get("firstProbeSite") == "residual_post", "Wrong probe site", result)
    _require(result.get("firstProbeLayer") == 22, "Wrong first probe layer", result)
    _require(result.get("secondProbeLayer") == 7, "Live probe change did not apply", result)
    _require(result.get("firstProbeModulePath") == "model.layers.22", "Wrong first probe module", result)
    _require(result.get("secondProbeModulePath") == "model.layers.7", "Wrong second probe module", result)
    _require(result.get("firstProbeShape") == "[1152]", "Wrong probe shape", result)
    _require(result.get("firstProbeDtype") == "float32", "Wrong probe dtype", result)
    _require(result.get("firstProbeRepresentation") == "dense_tensor_summary", "Wrong bounded probe representation", result)
    _require(result.get("firstSaeProbeSite") == "sae", "Wrong SAE probe site", result)
    _require(result.get("firstSaeProbeLayer") == 22, "Wrong SAE probe layer", result)
    _require(result.get("firstSaeProbeModulePath") == fixed_sae_path, "Wrong SAE probe module", result)
    _require(result.get("firstSaeProbeShape") == "[65536]", "Wrong exact SAE probe shape", result)
    _require(result.get("firstSaeProbeDtype") == "sparse_float32", "Wrong SAE probe dtype", result)
    _require(result.get("firstSaeProbeRepresentation") == "sparse_sae_summary", "Wrong SAE probe representation", result)


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
            result_assertion=assert_research_real_result,
            success_marker="SCORE_RESEARCH_INTERFACE_REAL_OK",
        )
    )


if __name__ == "__main__":
    main()
