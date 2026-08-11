"""Tests for the passive, receiver-independent activation observer contract."""

import asyncio
import json

import pytest

from app.server.pipeline.external_output import build_activation_event
from app.server.routers import integrations
from app.server.routers.integrations import load_activation_fixture


class RecordingObserver:
    def __init__(self):
        self.messages = []

    async def send_text(self, message):
        self.messages.append(message)


class FailingObserver:
    async def send_text(self, _message):
        raise OSError("observer disconnected")


def activation_event():
    return build_activation_event(
        run_id="run-observer",
        token_id=7,
        token=" test",
        elapsed_ms=42,
        active_features=[
            {"index": 10, "activation": 0.5, "description": "small"},
            {"index": 20, "activation": 2.0, "description": "large"},
        ],
        notes=[
            {
                "feature_index": 20,
                "cluster": 3,
                "cluster_name": "shape",
                "cluster_color": "#123456",
            }
        ],
        tonality={"matches": [{"name": "focus", "score": 0.75}], "pitch_bias": 0.4},
        observation={
            "model": "google/gemma-3-1b-pt",
            "layer": 7,
            "sae_layer": 22,
            "sae_width": "65k",
        },
        sequence=3,
    )


def test_build_activation_event_sorts_normalizes_and_preserves_provenance():
    event = activation_event()

    assert event["type"] == "activation_token"
    assert event["schema_version"] == 1
    assert event["run_id"] == "run-observer"
    assert event["observation"] == {
        "model": "google/gemma-3-1b-pt",
        "layer": 7,
        "sae_layer": 22,
        "sae_width": "65k",
    }
    assert event["active_feature_count"] == 2
    assert event["active_features"][0] == {
        "slot": 0,
        "index": 20,
        "activation": 2.0,
        "activation_norm": 1.0,
        "description": "large",
        "cluster_id": 3,
        "cluster_name": "shape",
        "cluster_color": "#123456",
    }
    assert event["active_features"][1]["activation_norm"] == pytest.approx(0.25)
    assert event["tonality"] == {"primary": "focus", "score": 0.75, "pitch_bias": 0.4}


def test_activation_publish_broadcasts_rich_json_and_prunes_failed_observers():
    healthy = RecordingObserver()
    failing = FailingObserver()
    previous_observers = integrations._observers
    integrations._observers = {healthy, failing}
    event = activation_event()
    try:
        asyncio.run(integrations.publish_activation(event))
    finally:
        remaining_observers = integrations._observers
        integrations._observers = previous_observers

    assert json.loads(healthy.messages[0]) == event
    assert healthy in remaining_observers
    assert failing not in remaining_observers


def test_checked_in_fixture_uses_stable_schema_and_model_provenance():
    events = load_activation_fixture()

    assert len(events) == 3
    assert all(event["schema_version"] == 1 for event in events)
    assert all(event["run_id"] == "fixture-activation-v1" for event in events)
    assert all(event["observation"]["model"] == "google/gemma-3-1b-pt" for event in events)
    assert all(
        event["active_feature_count"] == len(event["active_features"])
        for event in events
    )
