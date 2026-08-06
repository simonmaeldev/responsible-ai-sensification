"""Focused tests for the receiver-independent emitter mapping instrument."""

from copy import deepcopy

import pytest

from app.server.pipeline.emitter_mapping import (
    EmitterMappingRuntime,
    MAX_MAPPINGS,
    coerce_emitter_mappings,
    default_emitter_mappings,
    emitter_mapping_catalogue,
)


def _token_data():
    features = [
        {"index": 100, "activation": 3.0, "description": "bright edge"},
        {"index": 200, "activation": 1.0, "description": ""},
    ]
    notes = [
        {"feature_index": 100, "amplitude": 3.0, "freq": 440.0, "cluster": 2},
        {"feature_index": 200, "amplitude": 1.0, "freq": 880.0, "cluster": 4},
    ]
    tonality = {
        "matches": [{"name": "bright", "score": 0.6}],
        "prompt_influence": 0.25,
        "pitch_bias": 0.75,
    }
    return features, notes, tonality


def test_catalogue_has_model_semantic_audio_and_visual_entries():
    catalogue = emitter_mapping_catalogue()

    signal_keys = {item["key"] for item in catalogue["signals"]}
    target_keys = {item["key"] for item in catalogue["targets"]}

    assert {"activation.max", "feature.top_index", "tonality.score"} <= signal_keys
    assert {"audio.filter_hz", "audio.delay_mix", "visual.hue"} <= target_keys
    assert catalogue["default_mappings"] == default_emitter_mappings()


def test_coerce_mappings_rejects_unknowns_and_bounds_every_control():
    raw = [
        {
            "id": "wild",
            "source": "tonality.score",
            "target": "audio.delay_mix",
            "threshold": -2,
            "smoothing": 9,
            "quantize_steps": 99,
            "output_min": -20,
            "output_max": 20,
            "curve": "unknown",
        },
        {"source": "not-a-signal", "target": "audio.gain"},
    ]

    assert coerce_emitter_mappings(raw) == [
        {
            "id": "wild",
            "enabled": True,
            "source": "tonality.score",
            "target": "audio.delay_mix",
            "curve": "linear",
            "threshold": 0.0,
            "invert": False,
            "quantize_steps": 32,
            "smoothing": 0.98,
            "output_min": 0.0,
            "output_max": 0.75,
        }
    ]
    assert len(coerce_emitter_mappings(raw * 100)) <= MAX_MAPPINGS


def test_signal_bus_exposes_raw_and_normalized_sae_semantic_values():
    features, notes, tonality = _token_data()
    runtime = EmitterMappingRuntime()

    signals = runtime.build_signals(
        active_features=features,
        notes=notes,
        tonality=tonality,
        elapsed_ms=500,
        token_index=2,
        max_tokens=10,
        width="65k",
    )

    assert signals["activation.total"]["raw"] == 4.0
    assert signals["activation.max"]["normalized"] == 1.0
    assert signals["feature.described_ratio"]["raw"] == 0.5
    assert signals["feature.top_share"]["raw"] == 0.75
    assert signals["cluster.dominance"]["raw"] == 0.75
    assert signals["tonality.score"]["normalized"] == pytest.approx(0.8)
    assert signals["prompt.influence"]["raw"] == 0.25
    assert signals["pitch.interpretation"]["raw"] == 0.75
    assert signals["pitch.mean"]["raw"] == pytest.approx(75.0)
    assert signals["pitch.spread"]["raw"] == pytest.approx(12.0)
    assert signals["generation.elapsed"]["normalized"] == 0.5
    assert signals["token.progress"]["normalized"] == 0.2


def test_mapping_curves_quantization_smoothing_and_collision_are_deterministic():
    runtime = EmitterMappingRuntime()
    signals = {
        "tonality.score": {
            "raw": 0.5,
            "normalized": 0.5,
            "label": "score",
            "group": "Semantic",
            "unit": "cosine",
        }
    }
    mappings = [
        {
            "id": "first",
            "source": "tonality.score",
            "target": "audio.gain",
            "curve": "ease_in",
            "quantize_steps": 0,
            "smoothing": 0,
            "output_min": 0,
            "output_max": 1,
        },
        {
            "id": "last",
            "source": "tonality.score",
            "target": "audio.gain",
            "curve": "linear",
            "quantize_steps": 3,
            "smoothing": 0.5,
            "output_min": 0.2,
            "output_max": 0.8,
        },
    ]

    controls, diagnostics = runtime.apply_mappings(signals, mappings)
    assert diagnostics[0]["output"] == 0.25
    assert controls["audio.gain"] == pytest.approx(0.5)

    signals["tonality.score"]["normalized"] = 1.0
    controls, _ = runtime.apply_mappings(signals, mappings)
    assert controls["audio.gain"] == pytest.approx(0.65)


def test_payload_does_not_mutate_raw_features_or_final_notes():
    features, notes, tonality = _token_data()
    original_features = deepcopy(features)
    original_notes = deepcopy(notes)

    payload = EmitterMappingRuntime().build_payload(
        active_features=features,
        notes=notes,
        tonality=tonality,
        mappings=default_emitter_mappings(),
        elapsed_ms=20,
        token_index=1,
        max_tokens=3,
        width="65k",
    )

    assert features == original_features
    assert notes == original_notes
    assert payload["signals"]
    assert payload["controls"]
    assert payload["mappings"]


def test_live_mapping_edit_changes_the_next_payload_without_resetting_runtime():
    features, notes, tonality = _token_data()
    runtime = EmitterMappingRuntime()
    common = {
        "active_features": features,
        "notes": notes,
        "tonality": tonality,
        "elapsed_ms": 20,
        "max_tokens": 4,
        "width": "65k",
    }

    first = runtime.build_payload(
        **common,
        token_index=1,
        mappings=[
            {
                "id": "live",
                "source": "tonality.score",
                "target": "audio.gain",
                "output_min": 0,
                "output_max": 1,
            }
        ],
    )
    second = runtime.build_payload(
        **common,
        token_index=2,
        mappings=[
            {
                "id": "live",
                "source": "feature.top_share",
                "target": "audio.pan",
                "output_min": -1,
                "output_max": 1,
            }
        ],
    )

    assert set(first["controls"]) == {"audio.gain"}
    assert set(second["controls"]) == {"audio.pan"}
    assert second["controls"]["audio.pan"] == pytest.approx(0.5)
