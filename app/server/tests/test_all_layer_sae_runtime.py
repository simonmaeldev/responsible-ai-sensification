"""Runtime selection for the Gemma Scope 2 across-layer example."""

from types import SimpleNamespace
from unittest.mock import patch

from app.server.routers.config import MODEL_CATALOGUE


def test_runtime_cache_loads_each_exact_all_layer_sae_only_once():
    from app.server.routers.stream import _get_sae_runtime, _sae_runtime_cache

    params = SimpleNamespace(
        model="google/gemma-3-270m",
        layer=17,
        width="16k",
        l0="small",
    )
    model_spec = MODEL_CATALOGUE[params.model]
    fake_sae = SimpleNamespace(source_revision="scope-revision")
    _sae_runtime_cache.clear()

    with patch("app.server.pipeline.extract.load_sae", return_value=fake_sae) as load:
        first = _get_sae_runtime(params, model_spec, 17)
        second = _get_sae_runtime(params, model_spec, 17)

    assert first is second
    assert first.layer == 17
    assert first.width == "16k"
    assert first.l0 == "small"
    assert first.category == "resid_post_all"
    assert first.repo_id == "google/gemma-scope-2-270m-pt"
    assert first.revision == "scope-revision"
    assert first.neuronpedia.explanations == {}
    load.assert_called_once_with(
        layer=17,
        width="16k",
        l0="small",
        category="resid_post_all",
        sae_repo_id="google/gemma-scope-2-270m-pt",
    )


def test_live_runtime_resolver_tracks_the_requested_layer_but_not_untrained_sites():
    from app.server.routers.stream import (
        _live_sae_runtime_resolver,
        _sae_runtime_cache,
    )

    params = SimpleNamespace(
        model="google/gemma-3-270m",
        layer=0,
        width="16k",
        l0="small",
    )
    model_spec = MODEL_CATALOGUE[params.model]
    _sae_runtime_cache.clear()

    def fake_sae(layer, **_kwargs):
        return SimpleNamespace(source_revision="scope-revision", selected_layer=layer)

    with patch("app.server.pipeline.extract.load_sae", side_effect=fake_sae):
        resolve = _live_sae_runtime_resolver(params, model_spec)
        assert resolve().layer == 0
        params.layer = 8
        assert resolve().layer == 8
        params.layer = 999
        assert resolve().layer == 17

    fixed_params = SimpleNamespace(
        model="google/gemma-3-1b-pt",
        layer=7,
        width="65k",
        l0="medium",
    )
    fixed_spec = MODEL_CATALOGUE[fixed_params.model]
    _sae_runtime_cache.clear()
    empty_scope = SimpleNamespace(width="65k", explanations={})
    with patch("app.server.pipeline.extract.load_sae", side_effect=fake_sae), \
         patch(
             "app.server.pipeline.extract.download_neuronpedia_explanations",
             return_value=empty_scope,
         ):
        fixed = _live_sae_runtime_resolver(fixed_params, fixed_spec)
        assert fixed().layer == 22
