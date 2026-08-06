"""Semantic tonality helpers built on the shared MiniLM embedding space.

This module is the first local foundation for artist-defined tonal mappings:
verbal tonality descriptions and active SAE feature descriptions are embedded
with the same sentence-transformer model, then compared by cosine similarity.
It intentionally does not choose pitches yet; later audio policies can consume
the ranked tonality matches produced here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
DATA_DIR = Path(__file__).with_name("tonality_data")
DEFAULT_TONALITY_PATH = DATA_DIR / "default_tonalities.json"
DEFAULT_CACHE_DIR = Path("tonality_cache")


@dataclass(frozen=True)
class TonalityDescription:
    name: str
    description: str
    intervals: list[float] | None = None


@dataclass(frozen=True)
class TonalityDescriptionSet:
    name: str
    description: str
    tonalities: list[TonalityDescription]

    def description_map(self) -> dict[str, str]:
        return {entry.name: entry.description for entry in self.tonalities}


@dataclass(frozen=True)
class TonalityEmbeddingEntry:
    name: str
    description: str
    embedding: list[float]
    intervals: list[float] | None = None


@dataclass(frozen=True)
class TonalityEmbeddingCache:
    name: str
    description: str
    embed_model: str
    dimensions: int
    content_hash: str
    tonalities: list[TonalityEmbeddingEntry]


@dataclass(frozen=True)
class TonalityMatch:
    name: str
    score: float
    description: str
    intervals: list[float] | None = None


@dataclass(frozen=True)
class ActiveFeatureSignal:
    embedding: list[float]
    feature_count: int
    total_activation: float


@dataclass(frozen=True)
class ActiveFeatureTonalityResult:
    feature_count: int
    total_activation: float
    embed_model: str
    top_k: int
    matches: list[TonalityMatch]
    prompt_influence: float = 0.0


@dataclass
class TonalityMemory:
    """Run-level semantic tonality accumulator.

    Token-level matches remain the live signal. This memory gives replay/loop
    modes a slower summary of where the activation stream has tended overall.
    """

    scores: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    entries: dict[str, TonalityMatch] = field(default_factory=dict)
    token_count: int = 0

    def update(self, result: ActiveFeatureTonalityResult, *, top_k: int = 3) -> dict[str, Any]:
        self.token_count += 1
        weight = max(float(result.total_activation or 0.0), 1.0)
        for match in result.matches:
            normalized = _score_to_unit(match.score)
            self.scores[match.name] = self.scores.get(match.name, 0.0) + (normalized * weight)
            self.weights[match.name] = self.weights.get(match.name, 0.0) + weight
            self.entries[match.name] = match
        return self.payload(top_k=top_k)

    def payload(self, *, top_k: int = 3) -> dict[str, Any]:
        ranked: list[dict[str, Any]] = []
        for name, score_total in self.scores.items():
            weight = max(self.weights.get(name, 0.0), 1e-9)
            entry = self.entries[name]
            ranked.append(
                {
                    "name": name,
                    "score": score_total / weight,
                    "description": entry.description,
                    "intervals": entry.intervals,
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return {
            "token_count": self.token_count,
            "matches": ranked[: min(top_k, len(ranked))],
        }


def _coerce_intervals(raw: Any) -> list[float] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return None
        raw = [part.strip() for part in stripped.replace(";", ",").split(",") if part.strip()]
    if not isinstance(raw, list):
        raise ValueError("Tonality intervals must be a list of numbers")
    return [float(item) for item in raw]


def _coerce_description_set(raw: dict[str, Any]) -> TonalityDescriptionSet:
    if not isinstance(raw, dict):
        raise ValueError("Tonality description file must be a JSON object")

    name = str(raw.get("name") or "custom_tonalities")
    description = str(raw.get("description") or "")

    tonalities_raw = raw.get("tonalities")
    if tonalities_raw is None and isinstance(raw.get("keys"), dict):
        tonalities_raw = [
            {"name": key_name, "description": text}
            for key_name, text in raw["keys"].items()
        ]

    if not isinstance(tonalities_raw, list) or not tonalities_raw:
        raise ValueError("Tonality file must contain a non-empty 'tonalities' list")

    tonalities: list[TonalityDescription] = []
    seen: set[str] = set()
    for item in tonalities_raw:
        if not isinstance(item, dict):
            raise ValueError("Each tonality must be a JSON object")
        tonality_name = str(item.get("name") or "").strip()
        tonality_description = str(item.get("description") or "").strip()
        if not tonality_name:
            raise ValueError("Every tonality needs a non-empty name")
        if not tonality_description:
            raise ValueError(f"Tonality {tonality_name!r} needs a non-empty description")
        if tonality_name in seen:
            raise ValueError(f"Duplicate tonality name: {tonality_name}")
        seen.add(tonality_name)
        tonalities.append(
            TonalityDescription(
                name=tonality_name,
                description=tonality_description,
                intervals=_coerce_intervals(item.get("intervals")),
            )
        )

    return TonalityDescriptionSet(
        name=name,
        description=description,
        tonalities=tonalities,
    )


def load_tonality_descriptions(path: str | Path | None = None) -> TonalityDescriptionSet:
    target = Path(path) if path is not None else DEFAULT_TONALITY_PATH
    with open(target) as f:
        return _coerce_description_set(json.load(f))


def coerce_tonality_lenses(raw_lenses: list[dict[str, Any]]) -> TonalityDescriptionSet:
    """Coerce live GUI lens-editor payloads into a description set."""
    tonalities = []
    seen: set[str] = set()
    for raw in raw_lenses:
        if raw.get("enabled") is False:
            continue
        name = str(raw.get("name") or "").strip()
        description = str(raw.get("description") or "").strip()
        if not name or not description or name in seen:
            continue
        seen.add(name)
        tonalities.append(
            {
                "name": name,
                "description": description,
                "intervals": raw.get("intervals"),
            }
        )

    if not tonalities:
        return load_tonality_descriptions()

    return _coerce_description_set(
        {
            "name": "live_performance_lenses",
            "description": "Artist-edited live performance tonality lenses.",
            "tonalities": tonalities,
        }
    )


def _description_set_hash(tonality_set: TonalityDescriptionSet) -> str:
    payload = json.dumps(asdict(tonality_set), ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _vector(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def _encode_texts(
    texts: list[str],
    *,
    embed_model: str = DEFAULT_EMBED_MODEL,
    embedder: Any | None = None,
) -> list[list[float]]:
    if not texts:
        return []

    model = embedder
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(embed_model)

    try:
        encoded = model.encode(texts, show_progress_bar=False)
    except TypeError:
        encoded = model.encode(texts)

    return [_vector(row) for row in encoded]


def build_tonality_embedding_cache(
    tonality_set: TonalityDescriptionSet,
    *,
    embed_model: str = DEFAULT_EMBED_MODEL,
    embedder: Any | None = None,
) -> TonalityEmbeddingCache:
    descriptions = [entry.description for entry in tonality_set.tonalities]
    embeddings = _encode_texts(descriptions, embed_model=embed_model, embedder=embedder)
    dimensions = len(embeddings[0]) if embeddings else 0

    entries = [
        TonalityEmbeddingEntry(
            name=entry.name,
            description=entry.description,
            intervals=entry.intervals,
            embedding=embedding,
        )
        for entry, embedding in zip(tonality_set.tonalities, embeddings, strict=True)
    ]
    return TonalityEmbeddingCache(
        name=tonality_set.name,
        description=tonality_set.description,
        embed_model=embed_model,
        dimensions=dimensions,
        content_hash=_description_set_hash(tonality_set),
        tonalities=entries,
    )


def save_tonality_embedding_cache(
    cache: TonalityEmbeddingCache,
    output_path: str | Path | None = None,
) -> Path:
    DEFAULT_CACHE_DIR.mkdir(exist_ok=True)
    target = (
        Path(output_path)
        if output_path is not None
        else DEFAULT_CACHE_DIR / f"{cache.name}_{cache.embed_model.replace('/', '_')}.json"
    )
    with open(target, "w") as f:
        json.dump(asdict(cache), f, ensure_ascii=True, indent=2)
    return target


def load_tonality_embedding_cache(path: str | Path) -> TonalityEmbeddingCache:
    with open(path) as f:
        raw = json.load(f)

    tonalities_raw = raw.get("tonalities")
    if not isinstance(tonalities_raw, list) or not tonalities_raw:
        raise ValueError("Tonality embedding cache must contain tonalities")

    entries = [
        TonalityEmbeddingEntry(
            name=str(item["name"]),
            description=str(item["description"]),
            intervals=_coerce_intervals(item.get("intervals")),
            embedding=_vector(item["embedding"]),
        )
        for item in tonalities_raw
    ]
    return TonalityEmbeddingCache(
        name=str(raw.get("name") or ""),
        description=str(raw.get("description") or ""),
        embed_model=str(raw.get("embed_model") or DEFAULT_EMBED_MODEL),
        dimensions=int(raw.get("dimensions") or (len(entries[0].embedding) if entries else 0)),
        content_hash=str(raw.get("content_hash") or ""),
        tonalities=entries,
    )


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Embedding dimension mismatch: {len(a)} != {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_tonalities(
    semantic_embedding: Sequence[float],
    cache: TonalityEmbeddingCache,
    *,
    top_k: int = 3,
) -> list[TonalityMatch]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    ranked = [
        TonalityMatch(
            name=entry.name,
            score=cosine_similarity(semantic_embedding, entry.embedding),
            description=entry.description,
            intervals=entry.intervals,
        )
        for entry in cache.tonalities
    ]
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: min(top_k, len(ranked))]


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _score_to_unit(score: float) -> float:
    return max(0.0, min(1.0, (float(score) + 1.0) / 2.0))


def _blend_embeddings(
    feature_embedding: Sequence[float] | None,
    prompt_embedding: Sequence[float] | None,
    *,
    prompt_influence: float,
) -> list[float] | None:
    """Blend feature and prompt semantics in one embedding space.

    `prompt_influence=0` means feature-only, `1` means prompt-only. If only one
    side is present, that embedding is returned directly.
    """
    if feature_embedding is None and prompt_embedding is None:
        return None
    if feature_embedding is None:
        return list(prompt_embedding or [])
    if prompt_embedding is None:
        return list(feature_embedding)
    if len(feature_embedding) != len(prompt_embedding):
        raise ValueError(
            f"Embedding dimension mismatch: {len(feature_embedding)} != {len(prompt_embedding)}"
        )

    weight = _clamp_unit(prompt_influence)
    return [
        (feature_value * (1.0 - weight)) + (prompt_value * weight)
        for feature_value, prompt_value in zip(feature_embedding, prompt_embedding, strict=True)
    ]


def embed_text(
    text: str,
    *,
    embed_model: str = DEFAULT_EMBED_MODEL,
    embedder: Any | None = None,
) -> list[float]:
    text = text.strip()
    if not text:
        raise ValueError("Cannot embed empty text")
    return _encode_texts([text], embed_model=embed_model, embedder=embedder)[0]


def match_text_to_tonalities(
    text: str,
    cache: TonalityEmbeddingCache,
    *,
    top_k: int = 3,
    embedder: Any | None = None,
) -> list[TonalityMatch]:
    embedding = embed_text(text, embed_model=cache.embed_model, embedder=embedder)
    return rank_tonalities(embedding, cache, top_k=top_k)


def _feature_value(feature: Any, key: str, default: Any = None) -> Any:
    if isinstance(feature, dict):
        return feature.get(key, default)
    return getattr(feature, key, default)


def build_active_feature_signal(
    active_features: list[Any],
    *,
    embed_model: str = DEFAULT_EMBED_MODEL,
    embedder: Any | None = None,
) -> ActiveFeatureSignal | None:
    descriptions: list[str] = []
    weights: list[float] = []

    for feature in active_features:
        description = str(_feature_value(feature, "description", "") or "").strip()
        if not description:
            continue
        activation = float(_feature_value(feature, "activation", 1.0) or 0.0)
        descriptions.append(description)
        weights.append(max(activation, 0.0))

    if not descriptions:
        return None

    embeddings = _encode_texts(descriptions, embed_model=embed_model, embedder=embedder)
    total_weight = sum(weights)
    if total_weight <= 0.0:
        weights = [1.0 for _ in weights]
        total_weight = float(len(weights))

    dimensions = len(embeddings[0])
    pooled = [0.0 for _ in range(dimensions)]
    for embedding, weight in zip(embeddings, weights, strict=True):
        if len(embedding) != dimensions:
            raise ValueError("Feature embeddings must have consistent dimensions")
        for i, value in enumerate(embedding):
            pooled[i] += value * weight

    return ActiveFeatureSignal(
        embedding=[value / total_weight for value in pooled],
        feature_count=len(descriptions),
        total_activation=total_weight,
    )


def match_active_features_to_tonalities(
    active_features: list[Any],
    cache: TonalityEmbeddingCache,
    *,
    top_k: int = 3,
    embedder: Any | None = None,
) -> ActiveFeatureTonalityResult:
    signal = build_active_feature_signal(
        active_features,
        embed_model=cache.embed_model,
        embedder=embedder,
    )
    if signal is None:
        return ActiveFeatureTonalityResult(
            feature_count=0,
            total_activation=0.0,
            embed_model=cache.embed_model,
            top_k=top_k,
            matches=[],
        )

    return ActiveFeatureTonalityResult(
        feature_count=signal.feature_count,
        total_activation=signal.total_activation,
        embed_model=cache.embed_model,
        top_k=top_k,
        matches=rank_tonalities(signal.embedding, cache, top_k=top_k),
    )


def match_active_features_and_prompt_to_tonalities(
    active_features: list[Any],
    cache: TonalityEmbeddingCache,
    *,
    prompt: str | None = None,
    prompt_embedding: Sequence[float] | None = None,
    prompt_influence: float = 0.0,
    top_k: int = 3,
    embedder: Any | None = None,
) -> ActiveFeatureTonalityResult:
    """Rank tonalities from active features, optionally blended with the prompt.

    This implements the paper's proposal that the prompt embedding can be
    weighted during output while keeping active SAE features as the default
    signal. Callers that stream tokens can precompute `prompt_embedding` once.
    """
    signal = build_active_feature_signal(
        active_features,
        embed_model=cache.embed_model,
        embedder=embedder,
    )

    prompt_vector = prompt_embedding
    if prompt_vector is None and prompt and prompt.strip() and prompt_influence > 0.0:
        prompt_vector = embed_text(prompt, embed_model=cache.embed_model, embedder=embedder)

    blended = _blend_embeddings(
        signal.embedding if signal else None,
        prompt_vector,
        prompt_influence=prompt_influence,
    )

    if blended is None:
        return ActiveFeatureTonalityResult(
            feature_count=0,
            total_activation=0.0,
            embed_model=cache.embed_model,
            top_k=top_k,
            matches=[],
            prompt_influence=_clamp_unit(prompt_influence),
        )

    return ActiveFeatureTonalityResult(
        feature_count=signal.feature_count if signal else 0,
        total_activation=signal.total_activation if signal else 0.0,
        embed_model=cache.embed_model,
        top_k=top_k,
        matches=rank_tonalities(blended, cache, top_k=top_k),
        prompt_influence=_clamp_unit(prompt_influence),
    )


def tonality_result_to_payload(
    result: ActiveFeatureTonalityResult,
    *,
    pitch_bias: float = 0.0,
) -> dict[str, Any]:
    """Return a compact JSON-ready payload for WebSocket token events."""
    return {
        "feature_count": result.feature_count,
        "total_activation": result.total_activation,
        "embed_model": result.embed_model,
        "top_k": result.top_k,
        "prompt_influence": result.prompt_influence,
        "pitch_bias": _clamp_unit(pitch_bias),
        "matches": [
            {
                "name": match.name,
                "score": match.score,
                "description": match.description,
                "intervals": match.intervals,
            }
            for match in result.matches
        ],
    }


def frequency_to_midi(freq: float) -> float:
    if freq <= 0:
        raise ValueError("Frequency must be positive")
    return 69.0 + (12.0 * math.log2(freq / 440.0))


def midi_to_frequency(midi: float) -> float:
    return 440.0 * (2.0 ** ((float(midi) - 69.0) / 12.0))


def _nearest_interval_midi(
    raw_midi: float,
    intervals: Sequence[float],
    *,
    root_midi: float = 60.0,
) -> float:
    if not intervals:
        return raw_midi

    best = raw_midi
    best_distance: float | None = None
    center_octave = round((raw_midi - root_midi) / 12.0)
    for octave in range(center_octave - 2, center_octave + 3):
        for interval in intervals:
            candidate = root_midi + float(interval) + (12.0 * octave)
            distance = abs(candidate - raw_midi)
            if best_distance is None or distance < best_distance:
                best = candidate
                best_distance = distance
    return best


def apply_tonality_pitch_bias(
    notes: list[dict[str, Any]],
    result: ActiveFeatureTonalityResult,
    *,
    pitch_bias: float = 0.0,
    root_midi: float = 60.0,
) -> list[dict[str, Any]]:
    """Pull note frequencies toward the strongest tonality's interval set.

    The transformation is soft: `pitch_bias=0` preserves raw frequencies and
    `pitch_bias=1` snaps fully to the nearest interval. The raw and target
    values remain on each note so the GUI can show what happened.
    """
    bias = _clamp_unit(pitch_bias)
    primary = result.matches[0] if result.matches else None
    intervals = primary.intervals if primary else None

    biased_notes: list[dict[str, Any]] = []
    for note in notes:
        raw_freq = float(note.get("freq") or 440.0)
        raw_midi = frequency_to_midi(raw_freq)
        target_midi = (
            _nearest_interval_midi(raw_midi, intervals, root_midi=root_midi)
            if intervals
            else raw_midi
        )
        chosen_midi = raw_midi + ((target_midi - raw_midi) * bias)

        biased_note = {
            **note,
            "raw_freq": raw_freq,
            "raw_midi": raw_midi,
            "freq": midi_to_frequency(chosen_midi),
            "tonality_target_midi": target_midi,
            "tonality_pitch_bias": bias,
        }
        if primary:
            biased_note.update(
                {
                    "tonality_name": primary.name,
                    "tonality_score": primary.score,
                    "tonality_intervals": primary.intervals,
                }
            )
        biased_notes.append(biased_note)

    return biased_notes


def build_tonality_evidence(
    active_features: list[Any],
    notes: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return compact feature evidence for why the current sound is happening."""
    note_by_feature = {
        int(note["feature_index"]): note
        for note in notes
        if note.get("feature_index") is not None
    }

    rows: list[dict[str, Any]] = []
    for feature in active_features:
        feature_index = int(_feature_value(feature, "index", -1))
        if feature_index < 0:
            continue
        activation = float(_feature_value(feature, "activation", 0.0) or 0.0)
        note = note_by_feature.get(feature_index, {})
        raw_freq = note.get("raw_freq", note.get("freq"))
        shifted_freq = note.get("freq")
        pitch_shift = 0.0
        if raw_freq and shifted_freq:
            pitch_shift = frequency_to_midi(float(shifted_freq)) - frequency_to_midi(float(raw_freq))
        rows.append(
            {
                "feature_index": feature_index,
                "activation": activation,
                "description": str(_feature_value(feature, "description", "") or ""),
                "cluster_name": note.get("cluster_name") or "",
                "cluster_color": note.get("cluster_color") or "#888888",
                "raw_freq": raw_freq,
                "freq": shifted_freq,
                "pitch_shift_semitones": pitch_shift,
            }
        )

    rows.sort(key=lambda item: item["activation"], reverse=True)
    return rows[: max(0, limit)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and query semantic tonality embeddings")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build-cache", help="Embed tonality descriptions")
    build_parser.add_argument("--descriptions", type=Path, default=DEFAULT_TONALITY_PATH)
    build_parser.add_argument("--output", type=Path, default=None)
    build_parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)

    match_parser = subparsers.add_parser("match-text", help="Match text to a tonality cache")
    match_parser.add_argument("text")
    match_parser.add_argument("--cache", type=Path, required=True)
    match_parser.add_argument("--top-k", type=int, default=3)

    args = parser.parse_args()

    if args.command == "build-cache":
        tonality_set = load_tonality_descriptions(args.descriptions)
        cache = build_tonality_embedding_cache(
            tonality_set,
            embed_model=args.embed_model,
        )
        print(save_tonality_embedding_cache(cache, args.output))
    elif args.command == "match-text":
        cache = load_tonality_embedding_cache(args.cache)
        matches = match_text_to_tonalities(args.text, cache, top_k=args.top_k)
        print(json.dumps([asdict(match) for match in matches], indent=2))


if __name__ == "__main__":
    main()
