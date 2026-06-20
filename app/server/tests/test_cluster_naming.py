"""Tests for cluster_naming.py."""
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.server.pipeline.cluster_naming import (
    COLORBREWER_PAIRED_12,
    _build_cluster_prompt,
    _local_cluster_name,
    assign_cluster_colors,
    build_enriched_cluster_map,
    name_clusters,
)


# ── _build_cluster_prompt ────────────────────────────────────────────────────

def test_build_cluster_prompt_contains_features():
    descriptions = ["algebra", "calculus", "integration"]
    prompt = _build_cluster_prompt(descriptions)
    for desc in descriptions:
        assert f"- {desc}" in prompt


def test_build_cluster_prompt_ends_with_completion_cue():
    prompt = _build_cluster_prompt(["foo"])
    assert prompt.endswith('your answer: "')


def test_build_cluster_prompt_includes_few_shot_examples():
    prompt = _build_cluster_prompt(["foo"])
    assert '"transportation"' in prompt
    assert '"colors"' in prompt


# ── name_clusters (Claude API) ───────────────────────────────────────────────

def _mock_claude_response(text: str):
    """Build a minimal mock Anthropic response."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_name_clusters_prompt_format():
    """Mock Claude API: verify call is made and names are returned."""
    cluster_map = {
        0: {"cluster_id": 0, "instrument": "piano"},
        1: {"cluster_id": 0, "instrument": "piano"},
        2: {"cluster_id": 1, "instrument": "guitar"},
    }
    explanations = {0: "algebra", 1: "calculus", 2: "syntax"}

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = _mock_claude_response("math")

        result = name_clusters(cluster_map, explanations)

    assert set(result.keys()) == {0, 1}
    for name in result.values():
        assert isinstance(name, str)
        assert len(name) > 0
    # Claude was called once per cluster
    assert instance.messages.create.call_count == 2


def test_name_clusters_parses_output():
    """Verify output parsing: takes first 2 words, lowercases."""
    cluster_map = {0: {"cluster_id": 0, "instrument": "piano"}}
    explanations = {0: "foo"}

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = _mock_claude_response(
            "  Abstract Mathematics here  "
        )
        result = name_clusters(cluster_map, explanations)

    assert result[0] == "abstract mathematics"


def test_name_clusters_fallback_on_empty_output():
    """Fallback to cluster_N when Claude returns empty/whitespace."""
    cluster_map = {0: {"cluster_id": 0, "instrument": "piano"}}
    explanations = {0: "foo"}

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = _mock_claude_response("   ")
        result = name_clusters(cluster_map, explanations)

    assert result[0] == "cluster_0"


def test_name_clusters_fallback_on_api_error():
    """Fallback to local description-based names when the API call raises."""
    cluster_map = {0: {"cluster_id": 0, "instrument": "piano"}}
    explanations = {0: "recursive syntax", 1: "unused"}

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.side_effect = RuntimeError("network error")
        result = name_clusters(cluster_map, explanations)

    assert result[0] == "recursive syntax"


def test_name_clusters_fallback_when_client_cannot_start():
    """No Anthropic key should still produce usable local cluster names."""
    cluster_map = {
        0: {"cluster_id": 0, "instrument": "piano"},
        1: {"cluster_id": 0, "instrument": "piano"},
    }
    explanations = {0: "justice legal courts", 1: "rights legal claims"}

    with patch("anthropic.Anthropic", side_effect=RuntimeError("missing key")):
        result = name_clusters(cluster_map, explanations)

    assert result[0] == "legal justice"


def test_local_cluster_name_uses_meaningful_tokens():
    assert _local_cluster_name(
        ["The model tracks legal rights", "legal courts and legal claims"],
        2,
    ) == "legal rights"


# ── assign_cluster_colors ─────────────────────────────────────────────────────

def test_assign_cluster_colors_returns_12_colors():
    """All 12 cluster IDs should receive a color from COLORBREWER_PAIRED_12."""
    cluster_names = {i: f"cluster_{i}" for i in range(12)}
    mock_embed = MagicMock()
    mock_embed.encode = MagicMock(return_value=np.random.rand(12, 4))

    colors, sorted_ids = assign_cluster_colors(cluster_names, mock_embed)

    assert len(colors) == 12
    for color in colors.values():
        assert color in COLORBREWER_PAIRED_12


def test_assign_cluster_colors_all_unique():
    """No two clusters should receive the same color."""
    cluster_names = {i: f"name_{i}" for i in range(12)}
    mock_embed = MagicMock()
    mock_embed.encode = MagicMock(return_value=np.random.rand(12, 4))

    colors, sorted_ids = assign_cluster_colors(cluster_names, mock_embed)

    assert len(set(colors.values())) == 12


def test_assign_cluster_colors_sorted_ids_length():
    cluster_names = {i: f"name_{i}" for i in range(12)}
    mock_embed = MagicMock()
    mock_embed.encode = MagicMock(return_value=np.random.rand(12, 4))

    colors, sorted_ids = assign_cluster_colors(cluster_names, mock_embed)

    assert len(sorted_ids) == 12
    assert set(sorted_ids) == set(range(12))


# ── build_enriched_cluster_map disk cache ─────────────────────────────────────

def test_build_enriched_cluster_map_disk_cache(tmp_path, monkeypatch):
    """If cache file exists, load without calling Claude."""
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "neuronpedia_cache"
    cache_dir.mkdir()

    fake_cluster_map = {
        "0": {"cluster_id": 0, "instrument": "piano", "cluster_name": "math", "cluster_color": "#e31a1c"},
    }
    fake_palette = [{"cluster_id": 0, "name": "math", "color": "#e31a1c"}]
    cache_file = cache_dir / "gemma-3-1b_20_16k_clusters_12_enriched.json"
    with open(cache_file, "w") as f:
        json.dump({"cluster_map": fake_cluster_map, "palette": fake_palette}, f)

    mock_embed = MagicMock()
    mock_neuronpedia = MagicMock()
    mock_neuronpedia.explanations = {}

    with patch("anthropic.Anthropic") as MockClient:
        result = build_enriched_cluster_map(
            "gemma-3-1b", 20, "16k", mock_neuronpedia, mock_embed
        )
        # Claude should NOT have been called (cache hit)
        MockClient.return_value.messages.create.assert_not_called()

    assert result["palette"] == fake_palette
    assert 0 in result["cluster_map"]
