"""Receiver-independent sparse activation events for passive observers."""

from __future__ import annotations

from typing import Any

ACTIVATION_SCHEMA_VERSION = 1


def _cluster_metadata(note: dict[str, Any] | None) -> dict[str, Any]:
    note = note or {}
    return {
        "cluster_id": note.get("cluster"),
        "cluster_name": note.get("cluster_name") or "",
        "cluster_color": note.get("cluster_color") or "#888888",
    }


def _tonality_summary(tonality: dict[str, Any] | None) -> dict[str, Any]:
    if not tonality:
        return {"primary": "", "score": 0.0, "pitch_bias": 0.0}
    matches = tonality.get("matches") or []
    primary = matches[0] if matches else {}
    return {
        "primary": primary.get("name") or "",
        "score": float(primary.get("score") or 0.0),
        "pitch_bias": float(tonality.get("pitch_bias") or 0.0),
    }


def build_activation_event(
    *,
    run_id: str,
    token_id: int,
    token: str,
    elapsed_ms: int,
    active_features: list[dict[str, Any]],
    observation: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
    tonality: dict[str, Any] | None = None,
    sequence: int | None = None,
    source: str = "live",
) -> dict[str, Any]:
    """Build a stable rich-JSON event before receiver-specific mappings."""
    note_by_index = {
        int(note["feature_index"]): note
        for note in notes or []
        if note.get("feature_index") is not None
    }
    ordered = sorted(
        active_features,
        key=lambda feature: abs(float(feature.get("activation") or 0.0)),
        reverse=True,
    )
    peak = max(
        (abs(float(feature.get("activation") or 0.0)) for feature in ordered),
        default=0.0,
    )

    payload_features: list[dict[str, Any]] = []
    for slot, feature in enumerate(ordered):
        index = int(feature["index"])
        activation = float(feature.get("activation") or 0.0)
        payload_features.append(
            {
                "slot": slot,
                "index": index,
                "activation": activation,
                "activation_norm": abs(activation) / peak if peak else 0.0,
                "description": feature.get("description") or "",
                **_cluster_metadata(note_by_index.get(index)),
            }
        )

    event: dict[str, Any] = {
        "type": "activation_token",
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "source": source,
        "run_id": str(run_id),
        "token_id": int(token_id),
        "token": token,
        "elapsed_ms": int(elapsed_ms),
        "observation": dict(observation),
        "active_feature_count": len(payload_features),
        "active_features": payload_features,
        "tonality": _tonality_summary(tonality),
    }
    if sequence is not None:
        event["sequence"] = int(sequence)
    return event
