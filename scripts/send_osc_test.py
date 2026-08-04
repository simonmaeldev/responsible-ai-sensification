"""Send a deterministic /rai/v1 fixture to a configurable OSC receiver.

This isolates Ubuntu-to-Windows UDP diagnostics from model loading and browser
state. It uses the production OscRunOutput implementation, so address encoding,
live controls, note ordering, and note capping match the FastAPI stream.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from collections.abc import Sequence

from app.server.pipeline.osc_output import OscResult, OscRunOutput
from app.server.session import PipelineParams


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a bounded OSC v1 fixture without loading Gemma or an SAE.",
    )
    parser.add_argument("--host", required=True, help="Receiver host or IP address")
    parser.add_argument("--port", type=int, default=9000, help="Receiver UDP port (default: 9000)")
    parser.add_argument(
        "--max-notes",
        type=int,
        default=2,
        help="Maximum notes emitted per token (default: 2; allowed: 1-128)",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=40,
        help="Delay between fixture stages (default: 40; allowed: 0-2000)",
    )
    return parser


def _token_event(token_id: int, token: str, elapsed_ms: int) -> dict:
    """Return final-frequency notes with distinct raw frequencies for inspection."""
    return {
        "type": "token",
        "token_id": token_id,
        "token": token,
        "elapsed_ms": elapsed_ms,
        "notes": [
            {
                "feature_index": 12345,
                "freq": 333.75,
                "raw_freq": 330.0,
                "amplitude": 0.60,
                "cluster": 2,
                "instrument": "pad",
            },
            {
                "feature_index": 54321,
                "freq": 445.125,
                "raw_freq": 440.0,
                "amplitude": 0.90,
                "cluster": 7,
                "instrument": "bell",
            },
            {
                "feature_index": 101,
                "freq": 201.25,
                "raw_freq": 200.0,
                "amplitude": 0.20,
                "cluster": None,
                "instrument": "default",
            },
        ],
        "tonality": {
            "pitch_bias": 0.50,
            "matches": [{"name": "ubuntu lan fixture", "score": 0.875}],
        },
    }


def _require_ready(stage: str, result: OscResult) -> None:
    if result.state != "ready":
        raise RuntimeError(f"{stage}: {result.message}")
    sequence = f", sequence {result.sequence}" if result.sequence is not None else ""
    print(f"{stage}: queued {result.sent} OSC message(s){sequence}")


def _pause(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not 1 <= args.port <= 65_535:
        raise SystemExit("--port must be between 1 and 65535")
    if not 1 <= args.max_notes <= 128:
        raise SystemExit("--max-notes must be between 1 and 128")
    if not 0 <= args.delay_ms <= 2_000:
        raise SystemExit("--delay-ms must be between 0 and 2000")

    params = PipelineParams()
    params.update(
        osc_enabled=True,
        osc_host=args.host,
        osc_port=args.port,
        osc_max_notes_per_token=args.max_notes,
        bpm=120,
        mode="timed",
        loop=False,
        tonality_enabled=True,
        prompt_influence=0.25,
        tonality_pitch_bias=0.50,
    )
    run_id = f"ubuntu-lan-{uuid.uuid4().hex[:12]}"
    output = OscRunOutput(run_id)
    delay_seconds = args.delay_ms / 1_000.0

    print(f"OSC v1 fixture target: {args.host}:{args.port}")
    print(f"Run ID: {run_id}")
    print("UDP has no acknowledgement; confirm reception in the Windows receiver.")

    try:
        _require_ready("run start + initial controls", output.begin(params))
        _pause(delay_seconds)
        _require_ready("timed token", output.emit_token(params, _token_event(4242, "timed fixture", 17)))
        _pause(delay_seconds)

        params.update(
            bpm=96,
            mode="sustain",
            loop=True,
            tonality_enabled=False,
            prompt_influence=0.625,
            tonality_pitch_bias=0.375,
        )
        _require_ready(
            "live control update",
            output.sync_controls(
                params,
                {
                    "bpm",
                    "mode",
                    "loop",
                    "tonality_enabled",
                    "prompt_influence",
                    "tonality_pitch_bias",
                },
            ),
        )
        _pause(delay_seconds)
        _require_ready("sustain token", output.emit_token(params, _token_event(4243, "sustain fixture", 23)))
        _pause(delay_seconds)
        _require_ready("run done", output.emit_done(params))
        _pause(delay_seconds)
        _require_ready("run silent", output.emit_silent(params))
        _pause(delay_seconds)
        _require_ready("run stop", output.stop(params))
    except Exception as exc:
        print(f"OSC fixture failed: {exc}", file=sys.stderr)
        return 1

    expected_notes = min(3, args.max_notes)
    print(
        "Fixture sent. Windows should show the run, two token frames, "
        f"{expected_notes} note(s) in the final frame, live controls, done, silent, and stop."
    )
    print("Sentinel final frequency: 445.125 Hz (raw source value was 440.0 Hz).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
