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
