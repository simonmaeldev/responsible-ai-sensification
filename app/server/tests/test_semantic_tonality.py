"""Tests for local semantic tonality matching."""
import json

import pytest

from app.server.pipeline.semantic_tonality import (
    DEFAULT_EMBED_MODEL,
    TonalityMemory,
    TonalityDescriptionSet,
    TonalityEmbeddingCache,
    TonalityEmbeddingEntry,
    apply_tonality_pitch_bias,
    build_active_feature_signal,
    build_tonality_evidence,
    build_tonality_embedding_cache,
    coerce_tonality_lenses,
    frequency_to_midi,
    load_tonality_descriptions,
    load_tonality_embedding_cache,
    match_active_features_and_prompt_to_tonalities,
    match_active_features_to_tonalities,
    match_text_to_tonalities,
    midi_to_frequency,
    rank_tonalities,
    save_tonality_embedding_cache,
    tonality_result_to_payload,
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


def test_disabled_live_tonality_lens_is_excluded():
    tonality_set = coerce_tonality_lenses(
        [
            {"name": "off", "description": "disabled", "intervals": [0], "enabled": False},
            {"name": "on", "description": "enabled", "intervals": [0, 7], "enabled": True},
        ]
    )

    assert [item.name for item in tonality_set.tonalities] == ["on"]


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


def test_prompt_influence_can_shift_active_feature_tonality():
    result = match_active_features_and_prompt_to_tonalities(
        [{"description": "bright feature", "activation": 1.0}],
        _simple_cache(),
        prompt_embedding=[0.0, 1.0],
        prompt_influence=0.8,
        top_k=2,
        embedder=FakeEmbedder(),
    )

    assert result.feature_count == 1
    assert result.matches[0].name == "mournful tension"
    assert result.prompt_influence == pytest.approx(0.8)


def test_prompt_only_tonality_when_no_feature_descriptions():
    result = match_active_features_and_prompt_to_tonalities(
        [{"description": "", "activation": 10.0}],
        _simple_cache(),
        prompt_embedding=[1.0, 0.0],
        prompt_influence=1.0,
        top_k=2,
        embedder=FakeEmbedder(),
    )

    assert result.feature_count == 0
    assert result.matches[0].name == "luminous resolve"


def test_tonality_payload_is_json_ready():
    result = match_active_features_to_tonalities(
        [{"description": "bright feature", "activation": 2.0}],
        _simple_cache(),
        top_k=1,
        embedder=FakeEmbedder(),
    )

    payload = tonality_result_to_payload(result, pitch_bias=0.5)

    assert payload["feature_count"] == 1
    assert payload["pitch_bias"] == 0.5
    assert payload["matches"][0]["name"] == "luminous resolve"
    assert payload["matches"][0]["intervals"] == [0, 4, 7]


def test_tonality_pitch_bias_moves_frequency_toward_intervals():
    raw_freq = midi_to_frequency(61)
    result = match_active_features_to_tonalities(
        [{"description": "bright feature", "activation": 2.0}],
        _simple_cache(),
        top_k=1,
        embedder=FakeEmbedder(),
    )

    biased = apply_tonality_pitch_bias(
        [{"freq": raw_freq, "amplitude": 1.0, "feature_index": 42}],
        result,
        pitch_bias=1.0,
        root_midi=60,
    )

    assert frequency_to_midi(biased[0]["freq"]) == pytest.approx(60)
    assert biased[0]["raw_freq"] == pytest.approx(raw_freq)
    assert biased[0]["tonality_name"] == "luminous resolve"
    assert biased[0]["tonality_intervals"] == [0, 4, 7]


def test_partial_tonality_pitch_bias_keeps_raw_and_target_metadata():
    raw_freq = midi_to_frequency(61)
    result = match_active_features_to_tonalities(
        [{"description": "bright feature", "activation": 2.0}],
        _simple_cache(),
        top_k=1,
        embedder=FakeEmbedder(),
    )

    biased = apply_tonality_pitch_bias(
        [{"freq": raw_freq, "amplitude": 1.0, "feature_index": 42}],
        result,
        pitch_bias=0.5,
        root_midi=60,
    )

    assert frequency_to_midi(biased[0]["freq"]) == pytest.approx(60.5)
    assert biased[0]["tonality_target_midi"] == pytest.approx(60)


def test_coerce_tonality_lenses_accepts_live_editor_payload():
    tonality_set = coerce_tonality_lenses([
        {
            "name": "bureaucratic pressure",
            "description": "cold procedural legal administrative pressure",
            "intervals": "0, 1, 6, 10",
            "root": 2,
        },
        {"name": "", "description": "ignored"},
    ])

    assert tonality_set.name == "live_performance_lenses"
    assert len(tonality_set.tonalities) == 1
    assert tonality_set.tonalities[0].intervals == [0.0, 1.0, 6.0, 10.0]
    assert tonality_set.tonalities[0].root == 2


def test_lens_root_transposes_the_actual_pitch_target():
    tonality_set = coerce_tonality_lenses([
        {
            "name": "D major idea",
            "description": "bright feature",
            "intervals": [0, 4, 7],
            "root": 2,
        }
    ])
    cache = build_tonality_embedding_cache(
        tonality_set,
        embed_model="fake-model",
        embedder=FakeEmbedder(),
    )
    result = match_active_features_to_tonalities(
        [{"description": "bright feature", "activation": 1.0}],
        cache,
        top_k=1,
        embedder=FakeEmbedder(),
    )

    biased = apply_tonality_pitch_bias(
        [{"freq": midi_to_frequency(61), "amplitude": 1.0}],
        result,
        pitch_bias=1.0,
        root_midi=60,
    )

    assert frequency_to_midi(biased[0]["freq"]) == pytest.approx(62)
    assert biased[0]["tonality_root"] == 2
    assert tonality_result_to_payload(result)["matches"][0]["root"] == 2


def test_tonality_memory_accumulates_run_level_signal():
    memory = TonalityMemory()
    bright = match_active_features_to_tonalities(
        [{"description": "bright feature", "activation": 2.0}],
        _simple_cache(),
        top_k=2,
        embedder=FakeEmbedder(),
    )
    dark = match_active_features_to_tonalities(
        [{"description": "dark feature", "activation": 8.0}],
        _simple_cache(),
        top_k=2,
        embedder=FakeEmbedder(),
    )

    memory.update(bright)
    payload = memory.update(dark, top_k=2)

    assert payload["token_count"] == 2
    assert payload["matches"][0]["name"] == "mournful tension"
    assert payload["matches"][0]["score"] > payload["matches"][1]["score"]


def test_build_tonality_evidence_sorts_features_by_activation():
    evidence = build_tonality_evidence(
        [
            {"index": 1, "activation": 0.2, "description": "small feature"},
            {"index": 2, "activation": 3.5, "description": "large feature"},
        ],
        [
            {"feature_index": 1, "freq": 440.0, "raw_freq": 430.0, "cluster_name": "one"},
            {"feature_index": 2, "freq": 660.0, "raw_freq": 640.0, "cluster_name": "two"},
        ],
        limit=1,
    )

    assert evidence[0]["feature_index"] == 2
    assert evidence[0]["description"] == "large feature"
    assert evidence[0]["cluster_name"] == "two"
    assert evidence[0]["pitch_shift_semitones"] == pytest.approx(
        frequency_to_midi(660.0) - frequency_to_midi(640.0)
    )
