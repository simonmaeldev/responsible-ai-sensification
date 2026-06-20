"""Tests for local semantic tonality matching."""
import json

import pytest

from app.server.pipeline.semantic_tonality import (
    DEFAULT_EMBED_MODEL,
    TonalityDescriptionSet,
    TonalityEmbeddingCache,
    TonalityEmbeddingEntry,
    build_active_feature_signal,
    build_tonality_embedding_cache,
    load_tonality_descriptions,
    load_tonality_embedding_cache,
    match_active_features_to_tonalities,
    match_text_to_tonalities,
    rank_tonalities,
    save_tonality_embedding_cache,
)


class FakeEmbedder:
    def encode(self, texts, **kwargs):
        vectors = {
            "bright open stable consonant clear hopeful arrival gentle major-like release": [1.0, 0.0],
            "sad longing dark minor unresolved lament fragile suspended grief": [0.0, 1.0],
            "bright feature": [1.0, 0.0],
            "dark feature": [0.0, 1.0],
            "mixed text": [0.6, 0.4],
        }
        return [vectors[text] for text in texts]


def _simple_cache() -> TonalityEmbeddingCache:
    return TonalityEmbeddingCache(
        name="test_tonalities",
        description="test",
        embed_model="fake-model",
        dimensions=2,
        content_hash="abc",
        tonalities=[
            TonalityEmbeddingEntry(
                name="luminous resolve",
                description="bright",
                embedding=[1.0, 0.0],
                intervals=[0, 4, 7],
            ),
            TonalityEmbeddingEntry(
                name="mournful tension",
                description="dark",
                embedding=[0.0, 1.0],
                intervals=[0, 3, 7],
            ),
        ],
    )


def test_default_embed_model_is_minilm():
    assert DEFAULT_EMBED_MODEL == "all-MiniLM-L6-v2"


def test_load_default_tonality_descriptions():
    tonality_set = load_tonality_descriptions()

    assert isinstance(tonality_set, TonalityDescriptionSet)
    assert tonality_set.name == "default_artist_tonalities"
    assert len(tonality_set.tonalities) >= 4
    assert tonality_set.tonalities[0].intervals


def test_load_legacy_key_style_descriptions(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({
        "name": "legacy_keys",
        "description": "old schema",
        "keys": {
            "C major": "bright simple stable",
            "C minor": "sad longing dark",
        },
    }))

    tonality_set = load_tonality_descriptions(path)

    assert tonality_set.name == "legacy_keys"
    assert tonality_set.description_map()["C major"] == "bright simple stable"


def test_build_and_reload_tonality_embedding_cache(tmp_path):
    tonality_set = load_tonality_descriptions()
    subset = TonalityDescriptionSet(
        name="subset",
        description="small",
        tonalities=tonality_set.tonalities[:2],
    )
    cache = build_tonality_embedding_cache(
        subset,
        embed_model="fake-model",
        embedder=FakeEmbedder(),
    )
    path = save_tonality_embedding_cache(cache, tmp_path / "cache.json")

    reloaded = load_tonality_embedding_cache(path)

    assert reloaded.name == "subset"
    assert reloaded.embed_model == "fake-model"
    assert reloaded.dimensions == 2
    assert reloaded.tonalities[0].embedding == [1.0, 0.0]


def test_rank_tonalities_by_cosine_similarity():
    matches = rank_tonalities([0.9, 0.1], _simple_cache(), top_k=2)

    assert [match.name for match in matches] == [
        "luminous resolve",
        "mournful tension",
    ]
    assert matches[0].score > matches[1].score


def test_match_text_to_tonalities_uses_cache_embed_model():
    matches = match_text_to_tonalities(
        "mixed text",
        _simple_cache(),
        top_k=2,
        embedder=FakeEmbedder(),
    )

    assert matches[0].name == "luminous resolve"


def test_build_active_feature_signal_weights_by_activation():
    signal = build_active_feature_signal(
        [
            {"description": "bright feature", "activation": 3.0},
            {"description": "dark feature", "activation": 1.0},
            {"description": "", "activation": 100.0},
        ],
        embed_model="fake-model",
        embedder=FakeEmbedder(),
    )

    assert signal is not None
    assert signal.feature_count == 2
    assert signal.total_activation == 4.0
    assert signal.embedding == pytest.approx([0.75, 0.25])


def test_match_active_features_to_tonalities_returns_empty_without_descriptions():
    result = match_active_features_to_tonalities(
        [{"description": "", "activation": 1.0}],
        _simple_cache(),
        embedder=FakeEmbedder(),
    )

    assert result.feature_count == 0
    assert result.matches == []


def test_match_active_features_to_tonalities_ranks_weighted_signal():
    result = match_active_features_to_tonalities(
        [
            {"description": "bright feature", "activation": 1.0},
            {"description": "dark feature", "activation": 4.0},
        ],
        _simple_cache(),
        top_k=2,
        embedder=FakeEmbedder(),
    )

    assert result.feature_count == 2
    assert result.matches[0].name == "mournful tension"
