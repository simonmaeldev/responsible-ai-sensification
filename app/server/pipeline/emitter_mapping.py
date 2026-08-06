"""Emitter-side signal extraction and bounded live-control mappings.

The emitter owns artistic interpretation.  Connectors may mirror these named
controls later, but the browser can inspect and use them without a receiver.
Raw SAE features and final post-tonality notes are never mutated here.
"""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.server.pipeline.emitter_signals import (
    EMITTER_SIGNAL_REGISTRY,
    coerce_emitter_signal_keys,
    default_emitter_signal_keys,
    mappable_signal_specs,
)


@dataclass(frozen=True)
class TargetSpec:
    key: str
    label: str
    group: str
    minimum: float
    maximum: float
    unit: str = ""


SIGNAL_SPECS = mappable_signal_specs()

TARGET_SPECS = (
    TargetSpec("audio.gain", "Voice gain", "Audio", 0.0, 1.0, "ratio"),
    TargetSpec("audio.pitch_semitones", "Pitch shift", "Audio", -24.0, 24.0, "semitones"),
    TargetSpec("audio.note_density", "Note density", "Audio", 1.0, 128.0, "notes"),
    TargetSpec("audio.duration", "Duration multiplier", "Audio", 0.05, 4.0, "ratio"),
    TargetSpec("audio.timbre", "Timbre selector", "Audio", 0.0, 7.0, "index"),
    TargetSpec("audio.pan", "Stereo pan", "Audio", -1.0, 1.0, "pan"),
    TargetSpec("audio.filter_hz", "Filter cutoff", "Audio", 80.0, 16_000.0, "Hz"),
    TargetSpec("audio.resonance", "Filter resonance", "Audio", 0.1, 24.0, "Q"),
    TargetSpec("audio.delay_mix", "Delay mix", "Audio", 0.0, 0.75, "ratio"),
    TargetSpec("audio.delay_time", "Delay time", "Audio", 0.01, 1.0, "seconds"),
    TargetSpec("visual.energy", "Visual energy", "Visual", 0.0, 1.0, "ratio"),
    TargetSpec("visual.hue", "Hue rotation", "Visual", 0.0, 360.0, "degrees"),
    TargetSpec("visual.motion", "Visual motion", "Visual", 0.0, 1.0, "ratio"),
    TargetSpec("visual.bar_scale", "Activation-bar scale", "Visual", 0.25, 2.5, "ratio"),
)

SIGNALS_BY_KEY = {spec.key: spec for spec in SIGNAL_SPECS}
TARGETS_BY_KEY = {spec.key: spec for spec in TARGET_SPECS}
CURVES = {"linear", "ease_in", "ease_out", "s_curve"}
MAX_MAPPINGS = 32

_DEFAULT_MAPPINGS = [
    {
        "id": "activation-gain",
        "enabled": True,
        "source": "activation.max",
        "target": "audio.gain",
        "curve": "ease_out",
        "threshold": 0.0,
        "invert": False,
        "quantize_steps": 0,
        "smoothing": 0.35,
        "output_min": 0.25,
        "output_max": 1.0,
    },
    {
        "id": "feature-density",
        "enabled": True,
        "source": "feature.count",
        "target": "audio.note_density",
        "curve": "ease_out",
        "threshold": 0.0,
        "invert": False,
        "quantize_steps": 24,
        "smoothing": 0.25,
        "output_min": 2.0,
        "output_max": 24.0,
    },
    {
        "id": "activation-filter",
        "enabled": True,
        "source": "activation.delta",
        "target": "audio.filter_hz",
        "curve": "s_curve",
        "threshold": 0.0,
        "invert": False,
        "quantize_steps": 0,
        "smoothing": 0.65,
        "output_min": 250.0,
        "output_max": 8_000.0,
    },
    {
        "id": "tonality-energy",
        "enabled": True,
        "source": "tonality.score",
        "target": "visual.energy",
        "curve": "ease_out",
        "threshold": 0.0,
        "invert": False,
        "quantize_steps": 0,
        "smoothing": 0.25,
        "output_min": 0.3,
        "output_max": 1.0,
    },
    {
        "id": "feature-hue",
        "enabled": True,
        "source": "feature.top_index",
        "target": "visual.hue",
        "curve": "linear",
        "threshold": 0.0,
        "invert": False,
        "quantize_steps": 12,
        "smoothing": 0.2,
        "output_min": 0.0,
        "output_max": 360.0,
    },
    {
        "id": "activation-bars",
        "enabled": True,
        "source": "activation.total",
        "target": "visual.bar_scale",
        "curve": "ease_out",
        "threshold": 0.0,
        "invert": False,
        "quantize_steps": 0,
        "smoothing": 0.3,
        "output_min": 0.55,
        "output_max": 1.8,
    },
]


def default_emitter_mappings() -> list[dict[str, Any]]:
    """Return an independent starter instrument mapping list."""
    return deepcopy(_DEFAULT_MAPPINGS)


def emitter_mapping_catalogue() -> dict[str, Any]:
    """Return JSON-ready source/target metadata for the browser editor."""
    return {
        "signals": [vars(spec) for spec in SIGNAL_SPECS],
        "targets": [vars(spec) for spec in TARGET_SPECS],
        "curves": ["linear", "ease_in", "ease_out", "s_curve"],
        "max_mappings": MAX_MAPPINGS,
        "default_mappings": default_emitter_mappings(),
    }


def _finite_float(value: Any, fallback: float) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return fallback
    return converted if math.isfinite(converted) else fallback


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def coerce_emitter_mappings(raw_mappings: Any) -> list[dict[str, Any]]:
    """Validate untrusted live UI mapping rows and apply safe target bounds."""
    if not isinstance(raw_mappings, list):
        return []

    coerced: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_mappings[:MAX_MAPPINGS]):
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "")
        target = str(raw.get("target") or "")
        if source not in SIGNALS_BY_KEY or target not in TARGETS_BY_KEY:
            continue
        target_spec = TARGETS_BY_KEY[target]
        output_min = _clamp(
            _finite_float(raw.get("output_min"), target_spec.minimum),
            target_spec.minimum,
            target_spec.maximum,
        )
        output_max = _clamp(
            _finite_float(raw.get("output_max"), target_spec.maximum),
            target_spec.minimum,
            target_spec.maximum,
        )
        if output_min > output_max:
            output_min, output_max = output_max, output_min
        curve = str(raw.get("curve") or "linear")
        coerced.append(
            {
                "id": str(raw.get("id") or f"mapping-{index + 1}")[:80],
                "enabled": bool(raw.get("enabled", True)),
                "source": source,
                "target": target,
                "curve": curve if curve in CURVES else "linear",
                "threshold": _clamp(_finite_float(raw.get("threshold"), 0.0), 0.0, 0.99),
                "invert": bool(raw.get("invert", False)),
                "quantize_steps": int(_clamp(_finite_float(raw.get("quantize_steps"), 0), 0, 32)),
                "smoothing": _clamp(_finite_float(raw.get("smoothing"), 0.0), 0.0, 0.98),
                "output_min": output_min,
                "output_max": output_max,
            }
        )
    return coerced


def _feature_capacity(width: Any) -> int:
    text = str(width or "").strip().lower()
    known_widths = {"16k": 16_384, "65k": 65_536, "262k": 262_144, "1m": 1_048_576}
    if text in known_widths:
        return known_widths[text]
    if text.endswith("k"):
        return max(1, int(_finite_float(text[:-1], 65.0) * 1024))
    return max(1, int(_finite_float(text, 65_536)))


def _frequency_to_midi(frequency: float) -> float:
    if frequency <= 0:
        return 0.0
    return 69.0 + 12.0 * math.log2(frequency / 440.0)


def _curve(value: float, curve: str) -> float:
    value = _clamp(value, 0.0, 1.0)
    if curve == "ease_in":
        return value * value
    if curve == "ease_out":
        return 1.0 - ((1.0 - value) ** 2)
    if curve == "s_curve":
        return value * value * (3.0 - (2.0 * value))
    return value


class EmitterMappingRuntime:
    """Stateful per-run signal normalizer and mapping processor."""

    def __init__(self) -> None:
        self._adaptive_max: dict[str, float] = {}
        self._previous_total: float | None = None
        self._previous_tonality = ""
        self._smoothed: dict[str, tuple[tuple[Any, ...], float]] = {}

    def _adaptive_unit(self, key: str, value: float) -> float:
        previous = self._adaptive_max.get(key, 0.0)
        ceiling = max(abs(value), previous * 0.995, 1e-9)
        self._adaptive_max[key] = ceiling
        return _clamp(value / ceiling, 0.0, 1.0)

    def build_signals(
        self,
        *,
        active_features: list[dict[str, Any]],
        notes: list[dict[str, Any]],
        tonality: dict[str, Any] | None,
        elapsed_ms: float,
        token_index: int,
        max_tokens: int,
        width: Any,
        probe_values: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        amplitudes = [max(0.0, _finite_float(item.get("activation"), 0.0)) for item in active_features]
        total = sum(amplitudes)
        maximum = max(amplitudes, default=0.0)
        mean = total / len(amplitudes) if amplitudes else 0.0
        delta = 0.0 if self._previous_total is None else total - self._previous_total
        self._previous_total = total

        top_feature = max(active_features, key=lambda item: _finite_float(item.get("activation"), 0.0), default={})
        top_index = max(0, int(_finite_float(top_feature.get("index"), 0.0)))
        described = sum(1 for item in active_features if str(item.get("description") or "").strip())

        cluster_totals: dict[str, float] = {}
        for note in notes:
            cluster = note.get("cluster")
            if cluster is None:
                continue
            key = str(cluster)
            cluster_totals[key] = cluster_totals.get(key, 0.0) + max(
                0.0, _finite_float(note.get("amplitude"), 0.0)
            )
        cluster_sum = sum(cluster_totals.values())
        cluster_dominance = max(cluster_totals.values(), default=0.0) / cluster_sum if cluster_sum else 0.0

        matches = (tonality or {}).get("matches") or []
        primary = matches[0] if matches else {}
        tonality_name = str(primary.get("name") or "")
        tonality_score = _finite_float(primary.get("score"), -1.0)
        tonality_changed = 1.0 if self._previous_tonality and tonality_name != self._previous_tonality else 0.0
        if tonality_name:
            self._previous_tonality = tonality_name

        midis = [
            _frequency_to_midi(_finite_float(note.get("freq"), 0.0))
            for note in notes
            if _finite_float(note.get("freq"), 0.0) > 0
        ]
        pitch_mean = sum(midis) / len(midis) if midis else 0.0
        pitch_spread = max(midis) - min(midis) if midis else 0.0

        raw = {
            "activation.max": maximum,
            "activation.mean": mean,
            "activation.total": total,
            "activation.delta": delta,
            "feature.count": float(len(active_features)),
            "feature.top_index": float(top_index),
            "feature.top_share": maximum / total if total else 0.0,
            "feature.described_ratio": described / len(active_features) if active_features else 0.0,
            "cluster.count": float(len(cluster_totals)),
            "cluster.dominance": cluster_dominance,
            "tonality.score": tonality_score,
            "tonality.change": tonality_changed,
            "prompt.influence": _finite_float((tonality or {}).get("prompt_influence"), 0.0),
            "pitch.interpretation": _finite_float((tonality or {}).get("pitch_bias"), 0.0),
            "pitch.mean": pitch_mean,
            "pitch.spread": pitch_spread,
            "generation.elapsed": max(0.0, _finite_float(elapsed_ms, 0.0)),
            "token.progress": float(token_index),
        }

        delta_ceiling = max(abs(delta), self._adaptive_max.get("activation.delta", 0.0) * 0.995, 1e-9)
        self._adaptive_max["activation.delta"] = delta_ceiling
        progress = (
            token_index / max_tokens
            if max_tokens > 0
            else 1.0 - math.exp(-max(token_index, 0) / 32.0)
        )
        normalized = {
            "activation.max": self._adaptive_unit("activation.max", maximum),
            "activation.mean": self._adaptive_unit("activation.mean", mean),
            "activation.total": self._adaptive_unit("activation.total", total),
            "activation.delta": _clamp(0.5 + (0.5 * delta / delta_ceiling), 0.0, 1.0),
            "feature.count": _clamp(len(active_features) / 128.0, 0.0, 1.0),
            "feature.top_index": _clamp(top_index / max(_feature_capacity(width) - 1, 1), 0.0, 1.0),
            "feature.top_share": raw["feature.top_share"],
            "feature.described_ratio": raw["feature.described_ratio"],
            "cluster.count": _clamp(len(cluster_totals) / 16.0, 0.0, 1.0),
            "cluster.dominance": cluster_dominance,
            "tonality.score": _clamp((tonality_score + 1.0) / 2.0, 0.0, 1.0) if matches else 0.0,
            "tonality.change": tonality_changed,
            "prompt.influence": _clamp(raw["prompt.influence"], 0.0, 1.0),
            "pitch.interpretation": _clamp(raw["pitch.interpretation"], 0.0, 1.0),
            "pitch.mean": _clamp(pitch_mean / 127.0, 0.0, 1.0),
            "pitch.spread": _clamp(pitch_spread / 48.0, 0.0, 1.0),
            "generation.elapsed": raw["generation.elapsed"] / (raw["generation.elapsed"] + 500.0),
            "token.progress": _clamp(progress, 0.0, 1.0),
        }

        signals = {
            key: {
                "label": SIGNALS_BY_KEY[key].label,
                "group": SIGNALS_BY_KEY[key].group,
                "location": SIGNALS_BY_KEY[key].location,
                "kind": SIGNALS_BY_KEY[key].kind,
                "value_type": SIGNALS_BY_KEY[key].value_type,
                "unit": SIGNALS_BY_KEY[key].unit,
                "raw": raw[key],
                "normalized": normalized[key],
            }
            for key in raw
        }
        for key, sample in (probe_values or {}).items():
            spec = SIGNALS_BY_KEY.get(key)
            if spec is None or spec.value_type != "scalar" or not isinstance(sample, dict):
                continue
            probe_raw = _finite_float(sample.get("raw"), 0.0)
            provided_normalized = sample.get("normalized")
            probe_normalized = (
                self._adaptive_unit(key, max(0.0, probe_raw))
                if provided_normalized is None
                else _clamp(_finite_float(provided_normalized, 0.0), 0.0, 1.0)
            )
            signals[key] = {
                "label": spec.label,
                "group": spec.group,
                "location": spec.location,
                "kind": spec.kind,
                "value_type": spec.value_type,
                "unit": spec.unit,
                "raw": probe_raw,
                "normalized": probe_normalized,
            }
        return signals

    def build_streams(
        self,
        *,
        active_features: list[dict[str, Any]],
        probe_values: dict[str, Any] | None,
        selected_signal_keys: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Package explicitly selected non-scalar data without mapping it."""
        values = dict(probe_values or {})
        values["sae.active_features"] = deepcopy(active_features)
        streams: dict[str, dict[str, Any]] = {}
        for key in selected_signal_keys:
            spec = EMITTER_SIGNAL_REGISTRY.get(key)
            if spec is None or spec.value_type == "scalar" or key not in values:
                continue
            streams[key] = {
                "label": spec.label,
                "group": spec.group,
                "location": spec.location,
                "kind": spec.kind,
                "value_type": spec.value_type,
                "unit": spec.unit,
                "value": deepcopy(values[key]),
            }
        return streams

    def apply_mappings(
        self,
        signals: dict[str, dict[str, Any]],
        mappings: Any,
    ) -> tuple[dict[str, float], list[dict[str, Any]]]:
        controls: dict[str, float] = {}
        diagnostics: list[dict[str, Any]] = []
        for mapping in coerce_emitter_mappings(mappings):
            if not mapping["enabled"]:
                continue
            signal = signals.get(mapping["source"])
            if signal is None:
                continue
            value = _clamp(_finite_float(signal.get("normalized"), 0.0), 0.0, 1.0)
            if mapping["invert"]:
                value = 1.0 - value
            threshold = mapping["threshold"]
            value = 0.0 if value < threshold else (value - threshold) / (1.0 - threshold)
            value = _curve(value, mapping["curve"])
            steps = mapping["quantize_steps"]
            if steps >= 2:
                value = round(value * (steps - 1)) / (steps - 1)

            signature = (mapping["source"], mapping["target"], mapping["curve"])
            previous = self._smoothed.get(mapping["id"])
            if previous and previous[0] == signature:
                smoothing = mapping["smoothing"]
                value = (previous[1] * smoothing) + (value * (1.0 - smoothing))
            self._smoothed[mapping["id"]] = (signature, value)

            output = mapping["output_min"] + ((mapping["output_max"] - mapping["output_min"]) * value)
            target_spec = TARGETS_BY_KEY[mapping["target"]]
            output = _clamp(output, target_spec.minimum, target_spec.maximum)
            controls[mapping["target"]] = output
            diagnostics.append(
                {
                    "id": mapping["id"],
                    "source": mapping["source"],
                    "target": mapping["target"],
                    "input": signal["raw"],
                    "normalized": signal["normalized"],
                    "output": output,
                }
            )
        return controls, diagnostics

    def build_payload(
        self,
        *,
        active_features: list[dict[str, Any]],
        notes: list[dict[str, Any]],
        tonality: dict[str, Any] | None,
        mappings: Any,
        elapsed_ms: float,
        token_index: int,
        max_tokens: int,
        width: Any,
        probe_values: dict[str, Any] | None = None,
        selected_signal_keys: Any = None,
    ) -> dict[str, Any]:
        all_signals = self.build_signals(
            active_features=active_features,
            notes=notes,
            tonality=tonality,
            elapsed_ms=elapsed_ms,
            token_index=token_index,
            max_tokens=max_tokens,
            width=width,
            probe_values=probe_values,
        )
        selected = (
            default_emitter_signal_keys()
            if selected_signal_keys is None
            else coerce_emitter_signal_keys(selected_signal_keys)
        )
        visible_signals = {key: all_signals[key] for key in selected if key in all_signals}
        streams = self.build_streams(
            active_features=active_features,
            probe_values=probe_values,
            selected_signal_keys=selected,
        )
        controls, diagnostics = self.apply_mappings(all_signals, mappings)
        return {
            "signals": visible_signals,
            "streams": streams,
            "controls": controls,
            "mappings": diagnostics,
            "active_signal_keys": selected,
        }
