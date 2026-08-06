"""General signal metadata for the GPU-hosted Emitter.

The registry describes observable data without deciding how an artist should
interpret it or which Connector should carry it.  Model-specific probe adapters
can register additional entries without changing the browser's catalogue shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class EmitterSignalSpec:
    """Discoverable metadata for one raw or derived Emitter signal."""

    key: str
    label: str
    group: str
    location: str
    kind: str
    value_type: str
    description: str
    unit: str = ""
    default_active: bool = True
    mappable: bool = True
    cost: str = "low"


class EmitterSignalRegistry:
    """Small ordered registry used by runtime, API, and future probe adapters."""

    def __init__(self, specs: Iterable[EmitterSignalSpec] = ()) -> None:
        self._specs: dict[str, EmitterSignalSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: EmitterSignalSpec) -> None:
        if not spec.key or spec.key in self._specs:
            raise ValueError(f"Duplicate or empty Emitter signal key: {spec.key!r}")
        self._specs[spec.key] = spec

    def get(self, key: str) -> EmitterSignalSpec | None:
        return self._specs.get(key)

    def all(self) -> tuple[EmitterSignalSpec, ...]:
        return tuple(self._specs.values())

    def default_keys(self) -> list[str]:
        return [spec.key for spec in self._specs.values() if spec.default_active]

    def coerce_selection(self, raw_keys: Any) -> list[str]:
        if not isinstance(raw_keys, list):
            return self.default_keys()
        selected: list[str] = []
        seen: set[str] = set()
        for raw_key in raw_keys:
            key = str(raw_key)
            if key in self._specs and key not in seen:
                selected.append(key)
                seen.add(key)
        return selected

    def catalogue(self) -> dict[str, Any]:
        return {
            "signals": [asdict(spec) for spec in self._specs.values()],
            "default_active": self.default_keys(),
        }


LEGACY_SCALAR_SIGNAL_SPECS = (
    EmitterSignalSpec("activation.max", "Maximum activation", "SAE", "sae.output", "derived", "scalar", "Strongest active SAE feature.", "activation"),
    EmitterSignalSpec("activation.mean", "Mean activation", "SAE", "sae.output", "derived", "scalar", "Mean activation over active SAE features.", "activation"),
    EmitterSignalSpec("activation.total", "Total activation", "SAE", "sae.output", "derived", "scalar", "Sum of active SAE feature activations.", "activation"),
    EmitterSignalSpec("activation.delta", "Activation change", "SAE", "sae.output", "derived", "scalar", "Token-to-token change in total activation.", "activation"),
    EmitterSignalSpec("feature.count", "Active feature count", "SAE", "sae.output", "derived", "scalar", "Number of SAE features above threshold.", "features"),
    EmitterSignalSpec("feature.top_index", "Strongest feature index", "SAE", "sae.output", "derived", "scalar", "Index of the strongest active SAE feature.", "index"),
    EmitterSignalSpec("feature.top_share", "Strongest activation share", "SAE", "sae.output", "derived", "scalar", "Share of activation held by the strongest feature.", "ratio"),
    EmitterSignalSpec("feature.described_ratio", "Neuronpedia-described ratio", "Neuronpedia", "sae.metadata", "derived", "scalar", "Share of active features with a Neuronpedia description.", "ratio"),
    EmitterSignalSpec("cluster.count", "Active cluster count", "Clusters", "feature.clusters", "derived", "scalar", "Number of represented feature clusters.", "clusters"),
    EmitterSignalSpec("cluster.dominance", "Dominant cluster share", "Clusters", "feature.clusters", "derived", "scalar", "Activation share of the dominant cluster.", "ratio"),
    EmitterSignalSpec("tonality.score", "Dominant tonality similarity", "Semantic", "semantic.tonality", "derived", "scalar", "Similarity to the strongest active verbal tonality lens.", "cosine"),
    EmitterSignalSpec("tonality.change", "Tonality changed", "Semantic", "semantic.tonality", "derived", "scalar", "Gate indicating a change of dominant tonality lens.", "gate"),
    EmitterSignalSpec("prompt.influence", "Prompt influence", "Semantic", "semantic.prompt", "derived", "scalar", "Configured prompt contribution to semantic matching.", "ratio"),
    EmitterSignalSpec("pitch.interpretation", "Raw/interpreted blend", "Semantic", "semantic.pitch", "derived", "scalar", "Configured blend between raw and interpreted pitch.", "ratio"),
    EmitterSignalSpec("pitch.mean", "Mean final pitch", "Pitch", "notes.post_tonality", "derived", "scalar", "Mean pitch after current tonal interpretation.", "MIDI"),
    EmitterSignalSpec("pitch.spread", "Final pitch spread", "Pitch", "notes.post_tonality", "derived", "scalar", "Pitch range after current tonal interpretation.", "semitones"),
    EmitterSignalSpec("generation.elapsed", "Token inference time", "Generation", "generation.step", "derived", "scalar", "Elapsed time for the current generation step.", "ms"),
    EmitterSignalSpec("token.progress", "Generation progress", "Generation", "generation.step", "derived", "scalar", "Position in the requested generation length.", "ratio"),
)

LEGACY_SCALAR_SIGNAL_KEYS = tuple(spec.key for spec in LEGACY_SCALAR_SIGNAL_SPECS)

MODEL_SCALAR_SIGNAL_SPECS = (
    EmitterSignalSpec("model.residual.rms", "Residual RMS", "Model", "decoder.layer.selected.residual", "derived", "scalar", "Root-mean-square magnitude of the selected layer residual stream.", "RMS"),
    EmitterSignalSpec("model.residual.max_abs", "Residual peak", "Model", "decoder.layer.selected.residual", "derived", "scalar", "Maximum absolute value in the selected layer residual stream.", "activation"),
    EmitterSignalSpec("model.logits.entropy", "Logit entropy", "Model", "model.output.logits", "derived", "scalar", "Entropy of the next-token probability distribution.", "nats"),
    EmitterSignalSpec("model.logits.top_probability", "Top-token probability", "Model", "model.output.logits", "derived", "scalar", "Probability assigned to the selected next token.", "ratio"),
    EmitterSignalSpec("model.logits.margin", "Top-logit margin", "Model", "model.output.logits", "derived", "scalar", "Difference between the largest and second-largest logits.", "logit"),
)

RAW_STREAM_SIGNAL_SPECS = (
    EmitterSignalSpec("model.residual.vector", "Residual vector", "Model", "decoder.layer.selected.residual", "raw", "vector", "Full residual vector captured at the selected decoder layer for the current token.", default_active=False, mappable=False, cost="high"),
    EmitterSignalSpec("model.logits.top_k", "Top-k logits", "Model", "model.output.logits", "raw", "structured", "Highest model-output logits with token IDs and probabilities.", default_active=False, mappable=False, cost="medium"),
    EmitterSignalSpec("sae.active_features", "Sparse SAE activations", "SAE", "sae.output", "raw", "sparse_vector", "Active SAE feature indices, activations, and available descriptions.", default_active=False, mappable=False, cost="high"),
)

EMITTER_SIGNAL_REGISTRY = EmitterSignalRegistry(
    (*LEGACY_SCALAR_SIGNAL_SPECS, *MODEL_SCALAR_SIGNAL_SPECS, *RAW_STREAM_SIGNAL_SPECS)
)


def emitter_signal_catalogue() -> dict[str, Any]:
    """Return the JSON-ready catalogue used by the browser Signal Explorer."""
    return EMITTER_SIGNAL_REGISTRY.catalogue()


def default_emitter_signal_keys() -> list[str]:
    """Return a fresh list of low-cost signals selected in a new session."""
    return EMITTER_SIGNAL_REGISTRY.default_keys()


def coerce_emitter_signal_keys(raw_keys: Any) -> list[str]:
    """Validate untrusted browser selection while preserving user order."""
    return EMITTER_SIGNAL_REGISTRY.coerce_selection(raw_keys)


def mappable_signal_specs() -> tuple[EmitterSignalSpec, ...]:
    """Return scalar sources supported by the existing mapping matrix."""
    return tuple(spec for spec in EMITTER_SIGNAL_REGISTRY.all() if spec.mappable)
