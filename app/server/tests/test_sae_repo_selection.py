"""Tests for SAE repo selection logic."""
from unittest.mock import MagicMock, patch

import pytest

from app.server.routers.config import MODEL_CATALOGUE, SAE_REPO_MAP


def test_sae_repo_map_covers_all_catalogue_models():
    """Every model in MODEL_CATALOGUE must have a matching SAE_REPO_MAP entry."""
    for model_id in MODEL_CATALOGUE:
        assert model_id in SAE_REPO_MAP, (
            f"No SAE repo mapped for model {model_id!r}. Add it to SAE_REPO_MAP in config.py."
        )


def test_model_catalogue_exposes_architecture_separately_from_sae_layers():
    one_b = MODEL_CATALOGUE["google/gemma-3-1b-pt"]

    assert one_b["layers"] == [22]
    assert one_b["architecture"]["layer_count"] == 26
    assert one_b["architecture"]["hidden_size"] == 1152
    assert one_b["observation_layers"] == list(range(26))


def test_270m_catalogue_exposes_every_matching_pretrained_sae_layer():
    small = MODEL_CATALOGUE["google/gemma-3-270m"]

    assert small["layers"] == list(range(18))
    assert small["observation_layers"] == list(range(18))
    assert small["widths"] == ["16k"]
    assert small["l0s"] == ["small"]
    assert small["sae_category"] == "resid_post_all"
    assert small["live_sae_layers"] is True
    assert small["neuronpedia"] is False
    assert small["architecture"]["layer_count"] == 18
    assert small["architecture"]["hidden_size"] == 640


def test_270m_model_maps_to_official_gemma_scope_2_repo():
    assert SAE_REPO_MAP["google/gemma-3-270m"] == "google/gemma-scope-2-270m-pt"


def test_1b_model_maps_to_correct_sae_repo():
    assert SAE_REPO_MAP["google/gemma-3-1b-pt"] == "google/gemma-scope-2-1b-pt"


def test_4b_model_maps_to_correct_sae_repo():
    assert SAE_REPO_MAP["google/gemma-3-4b-pt"] == "google/gemma-scope-2-4b-pt"


@pytest.mark.parametrize("model_id,expected_repo", list(SAE_REPO_MAP.items()))
def test_load_sae_called_with_correct_repo(model_id, expected_repo):
    """load_sae must be called with the repo matching the selected model."""
    fake_tensors = {
        "w_enc": MagicMock(),
        "b_enc": MagicMock(),
        "threshold": MagicMock(),
        "w_dec": MagicMock(),
        "b_dec": MagicMock(),
    }

    with patch("app.server.pipeline.extract.hf_hub_download", return_value="/fake/path") as mock_download, \
         patch("app.server.pipeline.extract.load_file", return_value=fake_tensors), \
         patch("app.server.pipeline.extract.JumpReluSAE") as mock_sae_cls:
        mock_sae_instance = MagicMock()
        mock_sae_cls.return_value = mock_sae_instance
        mock_sae_instance.to.return_value = mock_sae_instance
        mock_sae_instance.eval.return_value = mock_sae_instance

        from app.server.pipeline.extract import load_sae
        load_sae(layer=22, width="65k", l0="medium", sae_repo_id=expected_repo)

        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args
        assert call_kwargs.kwargs.get("repo_id") == expected_repo or call_kwargs.args[0] == expected_repo or \
               (call_kwargs.kwargs.get("repo_id") or call_kwargs.args[0]) == expected_repo


def test_all_layer_loader_selects_the_exact_official_layer_path():
    fake_tensors = {
        "w_enc": MagicMock(),
        "b_enc": MagicMock(),
        "threshold": MagicMock(),
        "w_dec": MagicMock(),
        "b_dec": MagicMock(),
    }

    with patch("app.server.pipeline.extract.hf_hub_download", return_value="/fake/path") as mock_download, \
         patch("app.server.pipeline.extract.load_file", return_value=fake_tensors), \
         patch("app.server.pipeline.extract.JumpReluSAE") as mock_sae_cls:
        mock_sae_instance = MagicMock()
        mock_sae_cls.return_value = mock_sae_instance
        mock_sae_instance.to.return_value = mock_sae_instance
        mock_sae_instance.eval.return_value = mock_sae_instance

        from app.server.pipeline.extract import load_sae

        load_sae(
            layer=17,
            width="16k",
            l0="small",
            category="resid_post_all",
            sae_repo_id="google/gemma-scope-2-270m-pt",
        )

        assert mock_download.call_args.kwargs == {
            "repo_id": "google/gemma-scope-2-270m-pt",
            "filename": "resid_post_all/layer_17_width_16k_l0_small/params.safetensors",
        }
