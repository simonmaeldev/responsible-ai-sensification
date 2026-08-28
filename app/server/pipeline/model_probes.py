"""Bounded, provenance-bearing observation probes for supported model adapters.

The browser selects *what* to observe.  This module is responsible for mapping
those selections to real Gemma modules and returning canonical observations;
Connectors consume those observations later and never install model hooks.
"""

from __future__ import annotations

import math
import re
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import torch

MAX_PROBE_SLOTS = 8
PROBE_SITES = (
    "residual_post",
    "attention_output",
    "mlp_output",
    "sae",
)
PROBE_CAPTURE_MODES = ("summary", "vector")


def _boolean(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _probe_id(value: Any, fallback: str) -> str:
    identifier = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip())
    return identifier.strip("-")[:48] or fallback


def default_probe_rack(sae_layer: int = 22) -> list[dict[str, Any]]:
    """Return the two truthful observations shown by a new Emitter session."""
    return [
        {
            "id": "residual",
            "site": "residual_post",
            "layer": max(0, int(sae_layer)),
            "capture": "summary",
            "enabled": True,
            "publish": True,
        },
        {
            "id": "sae",
            "site": "sae",
            "layer": max(0, int(sae_layer)),
            "capture": "summary",
            "enabled": True,
            "publish": True,
        },
    ]


def coerce_probe_rack(
    raw_probes: Any,
    *,
    sae_layer: int = 22,
) -> list[dict[str, Any]]:
    """Validate an untrusted rack without inventing unsupported hook points."""
    if not isinstance(raw_probes, list):
        return default_probe_rack(sae_layer)

    selected: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, raw in enumerate(raw_probes):
        if len(selected) >= MAX_PROBE_SLOTS or not isinstance(raw, dict):
            continue
        site = str(raw.get("site") or "")
        if site not in PROBE_SITES:
            continue
        identifier = _probe_id(raw.get("id"), f"probe-{index + 1}")
        if identifier in identifiers:
            continue
        identifiers.add(identifier)
        try:
            layer = max(0, min(255, int(raw.get("layer", sae_layer))))
        except (TypeError, ValueError):
            layer = max(0, int(sae_layer))
        capture = str(raw.get("capture") or "summary")
        if capture not in PROBE_CAPTURE_MODES:
            capture = "summary"
        if site == "sae":
            layer = max(0, int(sae_layer))
            capture = "summary"
        selected.append(
            {
                "id": identifier,
                "site": site,
                "layer": layer,
                "capture": capture,
                "enabled": _boolean(raw.get("enabled"), True),
                "publish": _boolean(raw.get("publish"), True),
            }
        )
    return selected


def _decoder_layers_and_prefix(model: Any) -> tuple[Sequence[Any], str]:
    inner = model.model
    if hasattr(inner, "layers"):
        return inner.layers, "model.layers"
    if hasattr(inner, "language_model") and hasattr(inner.language_model, "layers"):
        return inner.language_model.layers, "model.language_model.layers"
    raise AttributeError(
        f"Cannot locate decoder layers in {type(inner).__name__}. "
        "Expected .layers or .language_model.layers."
    )


def _tensor_from_output(output: Any) -> torch.Tensor:
    if torch.is_tensor(output):
        return output
    if isinstance(output, (tuple, list)):
        for item in output:
            try:
                return _tensor_from_output(item)
            except TypeError:
                continue
    raise TypeError(f"Probe hook returned no tensor: {type(output).__name__}")


def _last_token_vector(output: Any) -> torch.Tensor:
    tensor = _tensor_from_output(output).detach().float()
    if tensor.ndim >= 3:
        tensor = tensor[0, -1]
    elif tensor.ndim == 2:
        tensor = tensor[-1]
    return tensor.reshape(-1)


def _tensor_summary(vector: torch.Tensor) -> dict[str, float]:
    if not vector.numel():
        return {"rms": 0.0, "max_abs": 0.0, "mean": 0.0}
    return {
        "rms": float(torch.sqrt(torch.mean(vector.square())).item()),
        "max_abs": float(vector.abs().max().item()),
        "mean": float(vector.mean().item()),
    }


class GemmaProbeManager:
    """Install one-forward hooks for a validated set of Gemma probe slots."""

    def __init__(self, model: Any, rack: Any, *, sae_layer: int) -> None:
        self.model = model
        self.layers, self.layer_prefix = _decoder_layers_and_prefix(model)
        self.rack = coerce_probe_rack(rack, sae_layer=sae_layer)
        self._captures: dict[str, torch.Tensor] = {}
        self._resolved: dict[str, tuple[int, str]] = {}
        self._handles: list[Any] = []

    def _resolve(self, probe: dict[str, Any]) -> tuple[Any, int, str]:
        layer = min(max(int(probe["layer"]), 0), max(len(self.layers) - 1, 0))
        decoder_layer = self.layers[layer]
        if probe["site"] == "residual_post":
            return decoder_layer, layer, f"{self.layer_prefix}.{layer}"
        if probe["site"] == "attention_output":
            module = getattr(decoder_layer, "self_attn", None)
            if module is None:
                raise AttributeError(f"Decoder block {layer} has no self_attn module")
            return module, layer, f"{self.layer_prefix}.{layer}.self_attn"
        if probe["site"] == "mlp_output":
            module = getattr(decoder_layer, "mlp", None)
            if module is None:
                raise AttributeError(f"Decoder block {layer} has no mlp module")
            return module, layer, f"{self.layer_prefix}.{layer}.mlp"
        raise ValueError(f"Site {probe['site']!r} is not a tensor hook")

    def _install(self) -> None:
        self._captures.clear()
        self._resolved.clear()
        for probe in self.rack:
            if not probe["enabled"] or probe["site"] == "sae":
                continue
            module, layer, module_path = self._resolve(probe)
            identifier = probe["id"]

            def capture_hook(_module, _inputs, output, *, probe_id=identifier):
                self._captures[probe_id] = _last_token_vector(output)

            self._resolved[identifier] = (layer, module_path)
            self._handles.append(module.register_forward_hook(capture_hook))

    def _remove(self) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    @contextmanager
    def capture(self) -> Iterator["GemmaProbeManager"]:
        self._install()
        try:
            yield self
        finally:
            self._remove()

    def tensor_observations(
        self,
        *,
        model_id: str,
        token_index: int,
    ) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for probe in self.rack:
            identifier = probe["id"]
            if not probe["enabled"] or probe["site"] == "sae" or identifier not in self._captures:
                continue
            vector = self._captures[identifier]
            layer, module_path = self._resolved[identifier]
            observation = {
                "id": identifier,
                "site": probe["site"],
                "layer": layer,
                "module_path": module_path,
                "capture": probe["capture"],
                "publish": probe["publish"],
                "model": model_id,
                "token_index": int(token_index),
                "shape": [int(vector.numel())],
                "dtype": "float32",
                "summary": _tensor_summary(vector),
            }
            if probe["capture"] == "vector":
                observation["vector"] = vector.cpu().tolist()
            observations.append(observation)
        return observations


def build_sae_probe_observations(
    rack: Any,
    active_features: Sequence[dict[str, Any]],
    *,
    sae_layer: int,
    sae_width: str,
    sae_category: str = "resid_post",
    sae_l0: str = "",
    sae_repo_id: str = "",
    sae_revision: str = "",
    sae_size: int,
    model_id: str,
    token_index: int,
) -> list[dict[str, Any]]:
    """Build fixed-layer sparse observations for enabled SAE rack slots."""
    features = sorted(
        (
            {
                "index": int(feature.get("index", -1)),
                "activation": float(feature.get("activation", 0.0)),
            }
            for feature in active_features
            if float(feature.get("activation", 0.0)) > 0
        ),
        key=lambda feature: feature["activation"],
        reverse=True,
    )
    maximum = features[0] if features else {"index": -1, "activation": 0.0}
    total = math.fsum(feature["activation"] for feature in features)
    observations: list[dict[str, Any]] = []
    for probe in coerce_probe_rack(rack, sae_layer=sae_layer):
        if not probe["enabled"] or probe["site"] != "sae":
            continue
        observation = {
                "id": probe["id"],
                "site": "sae",
                "layer": int(sae_layer),
                "module_path": (
                    f"gemma_scope.{sae_category}.layer_{sae_layer}.width_{sae_width}"
                ),
                "capture": "summary",
                "publish": probe["publish"],
                "model": model_id,
                "token_index": int(token_index),
                "shape": [max(0, int(sae_size))],
                "dtype": "sparse_float32",
                "summary": {
                    "active_count": len(features),
                    "max_activation": float(maximum["activation"]),
                    "total_activation": float(total),
                    "top_index": int(maximum["index"]),
                    "top_activation": float(maximum["activation"]),
                },
            }
        if sae_l0 or sae_repo_id or sae_revision:
            observation.update(
                {
                    "sae_category": str(sae_category),
                    "sae_width": str(sae_width),
                    "sae_l0": str(sae_l0),
                    "sae_repo_id": str(sae_repo_id),
                    "sae_revision": str(sae_revision),
                }
            )
        observations.append(observation)
    return observations
