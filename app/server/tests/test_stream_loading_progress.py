"""Structured loading feedback exposed by the Emitter WebSocket."""

import pytest

from app.server.routers.stream import LOADING_STAGES, _loading_event


def test_loading_events_report_stable_order_and_normalized_progress():
    assert [stage.key for stage in LOADING_STAGES] == [
        "model",
        "sae",
        "neuronpedia",
        "features",
        "tonality",
        "generation",
    ]

    active = _loading_event(
        "sae",
        "active",
        "Layer 22 · width 65k",
    )
    assert active == {
        "type": "loading",
        "stage_key": "sae",
        "label": "Sparse autoencoder",
        "state": "active",
        "detail": "Layer 22 · width 65k",
        "step": 2,
        "total": 6,
        "progress": pytest.approx(1 / 6),
    }

    cached = _loading_event(
        "neuronpedia",
        "cached",
        "65,536 descriptions from local cache",
    )
    assert cached["step"] == 3
    assert cached["progress"] == pytest.approx(3 / 6)
    assert cached["state"] == "cached"

    with pytest.raises(ValueError, match="Unknown loading stage"):
        _loading_event("not-a-stage", "active")


def test_loading_event_rejects_unknown_states():
    with pytest.raises(ValueError, match="Unknown loading state"):
        _loading_event("model", "mystery")
