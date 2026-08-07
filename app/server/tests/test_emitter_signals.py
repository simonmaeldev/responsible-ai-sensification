"""Tests for the general, model-agnostic Emitter signal catalogue."""

import math
from types import SimpleNamespace

import pytest
import torch

from app.server.pipeline.emitter_mapping import EmitterMappingRuntime
from app.server.pipeline.emitter_signals import (
    LEGACY_SCALAR_SIGNAL_KEYS,
    default_emitter_signal_keys,
    emitter_signal_catalogue,
    coerce_emitter_signal_keys,
)
from app.server.pipeline.extract import capture_model_probe_values, inspect_live


def test_catalogue_preserves_legacy_sources_and_describes_general_probes():
    catalogue = emitter_signal_catalogue()
    entries = catalogue["signals"]
    keys = [entry["key"] for entry in entries]

    assert len(keys) == len(set(keys))
    assert set(LEGACY_SCALAR_SIGNAL_KEYS) <= set(keys)
    assert len(LEGACY_SCALAR_SIGNAL_KEYS) == 18
    assert {
        "model.residual.vector",
        "model.logits.top_k",
        "sae.active_features",
    } <= set(keys)
    assert all(
        {"key", "label", "group", "location", "kind", "value_type", "description"}
        <= set(entry)
        for entry in entries
    )

    raw_streams = {
        entry["key"]: entry
        for entry in entries
        if entry["value_type"] != "scalar"
    }
    assert raw_streams["model.residual.vector"]["default_active"] is False
    assert raw_streams["model.residual.vector"]["mappable"] is False
    assert raw_streams["model.residual.vector"]["cost"] == "high"
    assert set(default_emitter_signal_keys()) == set(catalogue["default_active"])
    assert not set(raw_streams) & set(catalogue["default_active"])


def test_signal_selection_filters_unknowns_and_duplicates_without_reordering():
    assert coerce_emitter_signal_keys(
        [
            "model.logits.top_k",
            "unknown.future.probe",
            "activation.max",
            "model.logits.top_k",
        ]
    ) == ["model.logits.top_k", "activation.max"]
    assert coerce_emitter_signal_keys("activation.max") == default_emitter_signal_keys()


def test_model_probe_capture_only_materializes_requested_values():
    residual = torch.tensor([3.0, 4.0])
    logits = torch.tensor([0.0, 2.0, 1.0])
    probes = capture_model_probe_values(
        residual,
        logits,
        {
            "model.residual.rms",
            "model.residual.vector",
            "model.logits.entropy",
            "model.logits.top_probability",
            "model.logits.top_k",
        },
        logits_top_k=2,
    )

    assert set(probes) == {
        "model.residual.rms",
        "model.residual.vector",
        "model.logits.entropy",
        "model.logits.top_probability",
        "model.logits.top_k",
    }
    assert probes["model.residual.rms"]["raw"] == pytest.approx(math.sqrt(12.5))
    assert probes["model.residual.vector"] == {
        "values": [3.0, 4.0],
        "shape": [2],
        "dtype": "float32",
    }
    assert 0 < probes["model.logits.entropy"]["normalized"] < 1
    assert probes["model.logits.top_probability"]["raw"] == pytest.approx(
        torch.softmax(logits, dim=-1).max().item()
    )
    top_k = probes["model.logits.top_k"]
    assert top_k["shape"] == [2]
    assert [item["token_id"] for item in top_k["items"]] == [1, 2]
    assert top_k["items"][0]["logit"] == 2.0


def test_live_probe_key_callback_changes_the_next_generated_token():
    class FakeHookHandle:
        def __init__(self, layer):
            self.layer = layer

        def remove(self):
            self.layer.hook = None

    class FakeLayer:
        hook = None

        def register_forward_hook(self, hook):
            self.hook = hook
            return FakeHookHandle(self)

    class FakeModel:
        def __init__(self):
            self.layer = FakeLayer()
            self.model = SimpleNamespace(layers=[self.layer])

        def __call__(self, input_ids):
            sequence_length = input_ids.shape[1]
            hidden = torch.full((1, sequence_length, 2), float(sequence_length))
            self.layer.hook(self.layer, (), (hidden,))
            logits = torch.tensor([[[0.0, 2.0, 1.0]]] * sequence_length)
            return SimpleNamespace(logits=logits)

    class FakeTokenizer:
        eos_token_id = 99

        def __call__(self, _prompt, **_kwargs):
            return {"input_ids": torch.tensor([[0]])}

        def decode(self, token_ids):
            return f"token-{token_ids[0]}"

    class FakeSae:
        def encode(self, _residual):
            return torch.tensor([[0.0, 1.0, 0.0]])

    selections = iter(
        [
            {"model.residual.rms"},
            {"model.residual.vector"},
        ]
    )
    generated = list(
        inspect_live(
            "test",
            FakeModel(),
            FakeTokenizer(),
            FakeSae(),
            0,
            SimpleNamespace(explanations={1: "test feature"}),
            max_new_tokens=2,
            probe_keys=lambda: next(selections),
        )
    )

    assert set(generated[0][0].probe_values) == {"model.residual.rms"}
    assert set(generated[1][0].probe_values) == {"model.residual.vector"}
    assert generated[1][0].probe_values["model.residual.vector"]["shape"] == [2]


def test_dense_probe_can_move_layers_without_moving_the_sae():
    class FakeHookHandle:
        def __init__(self, layer):
            self.layer = layer

        def remove(self):
            self.layer.hooks.remove(self.hook)

    class FakeLayer:
        def __init__(self, index):
            self.index = index
            self.hooks = []

        def register_forward_hook(self, hook):
            self.hooks.append(hook)
            handle = FakeHookHandle(self)
            handle.hook = hook
            return handle

    class FakeModel:
        def __init__(self):
            self.layers = [FakeLayer(index) for index in range(3)]
            self.model = SimpleNamespace(layers=self.layers)

        def __call__(self, input_ids):
            sequence_length = input_ids.shape[1]
            for layer in self.layers:
                hidden = torch.full(
                    (1, sequence_length, 2),
                    float(layer.index + 1),
                )
                for hook in list(layer.hooks):
                    hook(layer, (), (hidden,))
            logits = torch.tensor([[[0.0, 2.0, 1.0]]] * sequence_length)
            return SimpleNamespace(logits=logits)

    class FakeTokenizer:
        eos_token_id = 99

        def __call__(self, _prompt, **_kwargs):
            return {"input_ids": torch.tensor([[0]])}

        def decode(self, token_ids):
            return f"token-{token_ids[0]}"

    class RecordingSae:
        def __init__(self):
            self.inputs = []

        def encode(self, residual):
            self.inputs.append(residual.clone())
            return torch.tensor([[0.0, 1.0, 0.0]])

    observation_layers = iter([0, 2])
    sae = RecordingSae()
    generated = list(
        inspect_live(
            "test",
            FakeModel(),
            FakeTokenizer(),
            sae,
            1,
            SimpleNamespace(explanations={1: "test feature"}),
            max_new_tokens=2,
            probe_keys={"model.residual.vector"},
            observation_layer=lambda: next(observation_layers),
        )
    )

    assert [token.probe_layer for token, _elapsed in generated] == [0, 2]
    assert generated[0][0].probe_values["model.residual.vector"]["values"] == [1.0, 1.0]
    assert generated[1][0].probe_values["model.residual.vector"]["values"] == [3.0, 3.0]
    assert [item.tolist() for item in sae.inputs] == [[[2.0, 2.0]], [[2.0, 2.0]]]


def test_invalid_observation_layer_is_clamped_without_stopping_generation():
    class FakeHookHandle:
        def remove(self):
            pass

    class FakeLayer:
        def __init__(self, value):
            self.value = value

        def register_forward_hook(self, hook):
            self.hook = hook
            return FakeHookHandle()

    layers = [FakeLayer(1.0), FakeLayer(2.0)]

    class FakeModel:
        model = SimpleNamespace(layers=layers)

        def __call__(self, input_ids):
            length = input_ids.shape[1]
            for layer in layers:
                layer.hook(layer, (), (torch.full((1, length, 1), layer.value),))
            return SimpleNamespace(logits=torch.tensor([[[0.0, 2.0]]] * length))

    class FakeTokenizer:
        eos_token_id = 1

        def __call__(self, _prompt, **_kwargs):
            return {"input_ids": torch.tensor([[0]])}

        def decode(self, _token_ids):
            return "done"

    class FakeSae:
        def encode(self, _residual):
            return torch.tensor([[0.0]])

    generated = list(
        inspect_live(
            "test",
            FakeModel(),
            FakeTokenizer(),
            FakeSae(),
            0,
            SimpleNamespace(explanations={}),
            max_new_tokens=1,
            probe_keys={"model.residual.vector"},
            observation_layer=99,
        )
    )

    assert generated[0][0].probe_layer == 1
    assert generated[0][0].probe_values["model.residual.vector"]["values"] == [2.0]


def test_payload_hides_unselected_signals_without_breaking_mapping_dependencies():
    runtime = EmitterMappingRuntime()
    payload = runtime.build_payload(
        active_features=[{"index": 3, "activation": 1.0, "description": "edge"}],
        notes=[{"feature_index": 3, "amplitude": 1.0, "freq": 440.0, "cluster": 1}],
        tonality=None,
        mappings=[
            {
                "id": "residual-pan",
                "source": "model.residual.rms",
                "target": "audio.pan",
                "output_min": -1,
                "output_max": 1,
            }
        ],
        elapsed_ms=10,
        token_index=1,
        max_tokens=2,
        width="65k",
        probe_values={"model.residual.rms": {"raw": 2.0, "normalized": 0.75}},
        selected_signal_keys=["activation.max"],
    )

    assert set(payload["signals"]) == {"activation.max"}
    assert payload["controls"]["audio.pan"] == pytest.approx(0.5)
    assert payload["streams"] == {}
    assert payload["active_signal_keys"] == ["activation.max"]


def test_raw_streams_are_only_added_to_payload_when_selected():
    runtime = EmitterMappingRuntime()
    common = {
        "active_features": [{"index": 3, "activation": 1.0, "description": "edge"}],
        "notes": [{"feature_index": 3, "amplitude": 1.0, "freq": 440.0, "cluster": 1}],
        "tonality": None,
        "mappings": [],
        "elapsed_ms": 10,
        "token_index": 1,
        "max_tokens": 2,
        "width": "65k",
        "probe_values": {
            "model.residual.vector": {
                "values": [0.25, -0.5],
                "shape": [2],
                "dtype": "float32",
            }
        },
    }

    default_payload = runtime.build_payload(**common)
    selected_payload = runtime.build_payload(
        **common,
        selected_signal_keys=["model.residual.vector", "sae.active_features"],
    )

    assert default_payload["streams"] == {}
    assert selected_payload["streams"]["model.residual.vector"]["value"]["shape"] == [2]
    assert selected_payload["streams"]["sae.active_features"]["value"] == [
        {"index": 3, "activation": 1.0, "description": "edge"}
    ]
