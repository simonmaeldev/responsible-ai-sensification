"""Behavioral tests for the Gemma neuroscience-style probe rack."""

from types import SimpleNamespace

import pytest
import torch

from app.server.pipeline.extract import inspect_live
from app.server.pipeline.model_probes import (
    MAX_PROBE_SLOTS,
    GemmaProbeManager,
    build_sae_probe_observations,
    coerce_probe_rack,
    default_probe_rack,
)


class FakeHookHandle:
    def __init__(self, module, hook):
        self.module = module
        self.hook = hook

    def remove(self):
        self.module.hooks.remove(self.hook)


class FakeModule:
    def __init__(self):
        self.hooks = []

    def register_forward_hook(self, hook):
        self.hooks.append(hook)
        return FakeHookHandle(self, hook)

    def emit(self, value):
        for hook in list(self.hooks):
            hook(self, (), value)


class FakeLayer(FakeModule):
    def __init__(self, index):
        super().__init__()
        self.index = index
        self.self_attn = FakeModule()
        self.mlp = FakeModule()


class FakeGemma:
    def __init__(self, layer_count=3):
        self.layers = [FakeLayer(index) for index in range(layer_count)]
        self.model = SimpleNamespace(layers=self.layers)

    def __call__(self, input_ids):
        length = input_ids.shape[1]
        for layer in self.layers:
            index = float(layer.index)
            layer.self_attn.emit(torch.full((1, length, 2), 10.0 + index))
            layer.mlp.emit(torch.full((1, length, 2), 20.0 + index))
            layer.emit((torch.full((1, length, 2), 30.0 + index),))
        return SimpleNamespace(logits=torch.tensor([[[0.0, 2.0, 1.0]]] * length))


def probe(probe_id, site, layer=0, *, capture="summary", publish=True, enabled=True):
    return {
        "id": probe_id,
        "site": site,
        "layer": layer,
        "capture": capture,
        "publish": publish,
        "enabled": enabled,
    }


def test_probe_rack_coercion_is_bounded_unique_and_keeps_sae_fixed():
    raw = [
        probe("residual", "residual_post", -4, capture="vector"),
        probe("residual", "mlp_output", 2),
        probe("attention", "attention_output", 999, capture="invented"),
        probe("sae-anywhere", "sae", 3, capture="vector"),
        probe("unknown", "q_projection", 2),
    ] + [probe(f"extra-{index}", "residual_post", index) for index in range(20)]

    coerced = coerce_probe_rack(raw, sae_layer=22)

    assert len(coerced) == MAX_PROBE_SLOTS
    assert len({entry["id"] for entry in coerced}) == len(coerced)
    assert coerced[0] == probe("residual", "residual_post", 0, capture="vector")
    assert coerced[1]["id"] == "attention"
    assert coerced[1]["capture"] == "summary"
    sae = next(entry for entry in coerced if entry["site"] == "sae")
    assert sae["layer"] == 22
    assert sae["capture"] == "summary"
    assert all(entry["site"] != "q_projection" for entry in coerced)
    assert {entry["site"] for entry in default_probe_rack(22)} == {
        "residual_post",
        "sae",
    }


def test_real_residual_attention_and_mlp_modules_are_captured_with_provenance():
    model = FakeGemma(layer_count=2)
    rack = [
        probe("res", "residual_post", 0, capture="vector"),
        probe("attn", "attention_output", 1),
        probe("mlp", "mlp_output", 1),
    ]
    manager = GemmaProbeManager(model, rack, sae_layer=1)

    with manager.capture():
        model(torch.tensor([[0, 1]]))
    observations = manager.tensor_observations(
        model_id="test/gemma",
        token_index=4,
    )

    assert [item["site"] for item in observations] == [
        "residual_post",
        "attention_output",
        "mlp_output",
    ]
    assert observations[0]["layer"] == 0
    assert observations[0]["module_path"].endswith("layers.0")
    assert observations[0]["shape"] == [2]
    assert observations[0]["summary"] == {
        "rms": 30.0,
        "max_abs": 30.0,
        "mean": 30.0,
    }
    assert observations[0]["vector"] == [30.0, 30.0]
    assert "vector" not in observations[1]
    assert observations[1]["summary"]["rms"] == pytest.approx(11.0)
    assert observations[1]["module_path"].endswith("layers.1.self_attn")
    assert observations[2]["summary"]["rms"] == pytest.approx(21.0)
    assert observations[2]["module_path"].endswith("layers.1.mlp")
    assert all(not layer.hooks for layer in model.layers)
    assert all(not layer.self_attn.hooks for layer in model.layers)
    assert all(not layer.mlp.hooks for layer in model.layers)


def test_sae_probe_reports_sparse_measurements_at_only_the_trained_layer():
    observations = build_sae_probe_observations(
        [probe("scope", "sae", 0, capture="vector", publish=True)],
        [
            {"index": 8, "activation": 2.5, "description": "curve"},
            {"index": 2, "activation": 1.5, "description": None},
        ],
        sae_layer=22,
        sae_width="65k",
        sae_size=65536,
        model_id="google/gemma-3-1b-pt",
        token_index=3,
    )

    assert observations == [
        {
            "id": "scope",
            "site": "sae",
            "layer": 22,
            "module_path": "gemma_scope.resid_post.layer_22.width_65k",
            "capture": "summary",
            "publish": True,
            "model": "google/gemma-3-1b-pt",
            "token_index": 3,
            "shape": [65536],
            "dtype": "sparse_float32",
            "summary": {
                "active_count": 2,
                "max_activation": 2.5,
                "total_activation": 4.0,
                "top_index": 8,
                "top_activation": 2.5,
            },
        }
    ]


def test_live_probe_rack_changes_hook_site_on_the_next_token():
    class FakeTokenizer:
        eos_token_id = 99

        def __call__(self, _prompt, **_kwargs):
            return {"input_ids": torch.tensor([[0]])}

        def decode(self, token_ids):
            return f"token-{token_ids[0]}"

    class FakeSae:
        def encode(self, _residual):
            return torch.tensor([[0.0, 1.0, 0.0]])

    racks = iter(
        [
            [probe("moving", "attention_output", 0)],
            [probe("moving", "mlp_output", 2, capture="vector")],
        ]
    )
    generated = list(
        inspect_live(
            "test",
            FakeGemma(layer_count=3),
            FakeTokenizer(),
            FakeSae(),
            1,
            SimpleNamespace(explanations={1: "test feature"}),
            max_new_tokens=2,
            probe_keys=(),
            observation_layer=1,
            probe_rack=lambda: next(racks),
        )
    )

    first, second = [analysis for analysis, _elapsed in generated]
    assert first.probes[0]["site"] == "attention_output"
    assert first.probes[0]["layer"] == 0
    assert first.probes[0]["summary"]["rms"] == pytest.approx(10.0)
    assert second.probes[0]["site"] == "mlp_output"
    assert second.probes[0]["layer"] == 2
    assert second.probes[0]["vector"] == [22.0, 22.0]
