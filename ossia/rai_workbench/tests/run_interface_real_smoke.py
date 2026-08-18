"""Run one real token through the Phase 2 custom score interface."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from run_score_real_smoke import run_real


def assert_interface_real_result(result: dict) -> None:
    if result.get("runError"):
        raise RuntimeError(f"Real interface run failed: {result['runError']}")
    for state in ("sawLoading", "sawRunning", "sawDone"):
        if result.get(state) is not True:
            raise RuntimeError(f"Real interface run did not reach {state}: {result}")
    if result.get("connectionState") != "ready":
        raise RuntimeError(f"Real interface did not connect: {result}")
    if result.get("runState") != "stopped":
        raise RuntimeError(f"Real interface did not stop cleanly: {result}")
    if result.get("promptValue") != "Phase 2 interface smoke":
        raise RuntimeError(f"Real interface changed the prompt: {result}")
    if result.get("maxTokensValue") != 1:
        raise RuntimeError(f"Real interface changed the token limit: {result}")
    if not result.get("tokenText"):
        raise RuntimeError(f"Real interface did not show an exact token: {result}")
    if not isinstance(result.get("tokenId"), int) or result["tokenId"] < 0:
        raise RuntimeError(f"Real interface did not show a token ID: {result}")
    if result.get("featureCount") != 12:
        raise RuntimeError(f"Real interface did not create twelve rows: {result}")
    if not isinstance(result.get("featureIndex"), int) or result["featureIndex"] < 0:
        raise RuntimeError(f"Real interface did not show an SAE feature: {result}")
    if not isinstance(result.get("featureActivation"), (int, float)):
        raise RuntimeError(f"Real interface did not show feature activation: {result}")
    if result["featureActivation"] <= 0:
        raise RuntimeError(f"Real interface feature was not active: {result}")
    if not result.get("featureDescription"):
        raise RuntimeError(
            f"Real interface did not show Neuronpedia evidence: {result}"
        )


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
            result_assertion=assert_interface_real_result,
            success_marker="SCORE_INTERFACE_REAL_SMOKE_OK",
        )
    )


if __name__ == "__main__":
    main()
