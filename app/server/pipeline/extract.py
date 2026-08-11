"""extract.py: Extract SAE feature activations from a language model generation.

Usage:
    uv run python extract.py "your prompt" [--model MODEL] [--layer LAYER]
        [--width WIDTH] [--l0 L0] [--max-tokens N] [--output PATH] [--verbose]
        [--stream] [--loop]
"""
import argparse
import gzip
import itertools
import json
import math
import re
import sys
import time
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Generator

import requests
import torch
import torch.nn as nn
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, Field
from safetensors.torch import load_file
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.server.pipeline.export import export_to_json

torch.set_grad_enabled(False)
device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ActiveFeature(BaseModel):
    index: int
    activation: float
    description: str | None  # None if not found in Neuronpedia


class TokenAnalysis(BaseModel):
    token_id: int
    token: str
    l0: int  # total number of active features (activation > 0)
    active_features: list[ActiveFeature]
    probe_values: dict[str, object] = Field(default_factory=dict)
    probe_layer: int | None = None
    probes: list[dict[str, object]] = Field(default_factory=list)


class GenerationAnalysis(BaseModel):
    prompt: str
    model_id: str
    layer: int
    sae_width: str  # e.g. "65k"
    generated_tokens: list[TokenAnalysis]
    full_generated_text: str  # decoded full generation (all tokens joined)


class NeuronpediaScope(BaseModel):
    model_id: str
    layer: int
    width: str  # e.g. "65k"
    explanations: dict[int, str]  # feature_index -> description string


# ---------------------------------------------------------------------------
# Neuronpedia download layer
# ---------------------------------------------------------------------------

NEURONPEDIA_S3 = "https://neuronpedia-datasets.s3.us-east-1.amazonaws.com"
CACHE_DIR = Path("neuronpedia_cache")


def list_available_scopes(model_id: str) -> list[str]:
    """Return list of scope IDs available on Neuronpedia for model_id."""
    url = f"{NEURONPEDIA_S3}/?list-type=2&prefix=v1/{model_id}/&delimiter=/"
    resp = requests.get(url)
    resp.raise_for_status()
    prefixes = re.findall(r"<Prefix>v1/[^/]+/([^/]+)/</Prefix>", resp.text)
    return [p for p in prefixes if p != model_id]


def download_neuronpedia_explanations(
    model_id: str,
    layer: int,
    width: str,
) -> NeuronpediaScope:
    """Download all feature explanation descriptions for the given scope.

    Uses a local cache at neuronpedia_cache/{model_id}_{layer}_{width}.jsonl.
    Returns a NeuronpediaScope with explanations dict populated.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{model_id}_{layer}_{width}.jsonl"

    explanations: dict[int, str] = {}

    if cache_file.exists():
        with open(cache_file) as f:
            for line in f:
                entry = json.loads(line)
                explanations[entry["index"]] = entry["description"]
        return NeuronpediaScope(
            model_id=model_id,
            layer=layer,
            width=width,
            explanations=explanations,
        )

    # Discover batch count
    scope_id = f"{layer}-gemmascope-2-res-{width}"
    prefix = f"v1/{model_id}/{scope_id}/explanations/"
    list_url = f"{NEURONPEDIA_S3}/?list-type=2&prefix={prefix}&delimiter=/"
    resp = requests.get(list_url)
    resp.raise_for_status()
    batch_keys = re.findall(
        r"<Key>(" + re.escape(prefix) + r"batch-\d+\.jsonl\.gz)</Key>", resp.text
    )

    with open(cache_file, "w") as out:
        for key in sorted(
            batch_keys, key=lambda k: int(k.split("batch-")[1].split(".")[0])
        ):
            url = f"{NEURONPEDIA_S3}/{key}"
            data = requests.get(url).content
            for line in gzip.decompress(data).decode().splitlines():
                entry = json.loads(line)
                idx = int(entry["index"])
                desc = entry["description"]
                explanations[idx] = desc
                out.write(json.dumps({"index": idx, "description": desc}) + "\n")

    return NeuronpediaScope(
        model_id=model_id,
        layer=layer,
        width=width,
        explanations=explanations,
    )


# ---------------------------------------------------------------------------
# SAE
# ---------------------------------------------------------------------------


class JumpReluSAE(nn.Module):
    def __init__(self, w_enc, b_enc, threshold, w_dec, b_dec):
        super().__init__()
        self.w_enc = nn.Parameter(w_enc)
        self.b_enc = nn.Parameter(b_enc)
        self.threshold = nn.Parameter(threshold)
        self.w_dec = nn.Parameter(w_dec)
        self.b_dec = nn.Parameter(b_dec)

    def encode(self, x):
        pre_acts = x @ self.w_enc + self.b_enc
        mask = pre_acts > self.threshold
        acts = mask * torch.relu(pre_acts)
        return acts


def load_sae(
    layer=22, width="65k", l0="medium", category="resid_post", device=device,
    sae_repo_id: str = "google/gemma-scope-2-1b-pt",
) -> JumpReluSAE:
    path = f"{category}/layer_{layer}_width_{width}_l0_{l0}/params.safetensors"
    print(f"[load_sae] Locating SAE weights from HuggingFace: {path}", file=sys.stderr, flush=True)
    local_path = hf_hub_download(repo_id=sae_repo_id, filename=path)
    print(f"[load_sae] SAE weights file: {local_path}", file=sys.stderr, flush=True)
    tensors = load_file(local_path)
    print(f"[load_sae] SAE tensors loaded. Moving to device={device}...", file=sys.stderr, flush=True)
    sae = JumpReluSAE(
        w_enc=tensors["w_enc"],
        b_enc=tensors["b_enc"],
        threshold=tensors["threshold"],
        w_dec=tensors["w_dec"],
        b_dec=tensors["b_dec"],
    )
    result = sae.to(device).eval()
    print(f"[load_sae] SAE ready on {device}.", file=sys.stderr, flush=True)
    return result


# ---------------------------------------------------------------------------
# Generation-time inspection
# ---------------------------------------------------------------------------


def _get_decoder_layers(model):
    """Return the nn.ModuleList of decoder layers for a CausalLM model.

    Gemma-3 1b uses Gemma2ForCausalLM → model.model.layers
    Gemma-3 4b uses Gemma3ForCausalLM → model.model.language_model.layers
    """
    inner = model.model  # unwrap the CausalLM shell
    if hasattr(inner, "layers"):
        return inner.layers
    if hasattr(inner, "language_model") and hasattr(inner.language_model, "layers"):
        return inner.language_model.layers
    raise AttributeError(
        f"Cannot locate decoder layers in {type(inner).__name__}. "
        "Expected .layers or .language_model.layers."
    )


def _safe_layer_index(value: object, layer_count: int, fallback: int) -> int:
    """Resolve a live probe selection to a valid decoder-layer index."""
    try:
        selected = int(value)
    except (TypeError, ValueError):
        selected = int(fallback)
    return min(max(selected, 0), max(layer_count - 1, 0))


def summarize_layer_residuals(
    residuals: Collection[torch.Tensor],
) -> list[dict[str, float | int | None]]:
    """Describe how one token's residual stream changes across decoder blocks.

    The compact profile intentionally keeps only aggregate measurements. Full
    residual vectors remain available for the independently selected layer.
    """
    vectors = [tensor.detach().float().reshape(-1) for tensor in residuals]
    if not vectors:
        return []
    matrix = torch.stack(vectors)
    root_mean_squares = torch.sqrt(torch.mean(matrix.square(), dim=1))
    maximums = matrix.abs().amax(dim=1)
    if len(vectors) > 1:
        previous = matrix[:-1]
        current = matrix[1:]
        deltas = torch.sqrt(torch.mean((current - previous).square(), dim=1))
        denominators = torch.linalg.vector_norm(current, dim=1) * torch.linalg.vector_norm(previous, dim=1)
        cosines = torch.where(
            denominators > 0,
            torch.sum(current * previous, dim=1) / denominators,
            torch.zeros_like(denominators),
        ).clamp(-1.0, 1.0)
        delta_values = deltas.cpu().tolist()
        cosine_values = cosines.cpu().tolist()
    else:
        delta_values = []
        cosine_values = []
    rms_values = root_mean_squares.cpu().tolist()
    maximum_values = maximums.cpu().tolist()
    return [
        {
            "layer": layer_index,
            "rms": rms_values[layer_index],
            "max_abs": maximum_values[layer_index],
            "delta_rms": None if layer_index == 0 else delta_values[layer_index - 1],
            "cosine_to_previous": None if layer_index == 0 else cosine_values[layer_index - 1],
        }
        for layer_index in range(len(vectors))
    ]


def describe_model_architecture(model) -> dict[str, object]:
    """Return browser-safe decoder facts from the model that was loaded."""
    decoder_layers = _get_decoder_layers(model)
    config = model.config
    text_config = getattr(config, "text_config", config)

    def _integer(name: str) -> int | None:
        value = getattr(text_config, name, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    raw_layer_types = getattr(text_config, "layer_types", None)
    if isinstance(raw_layer_types, (tuple, list)) and len(raw_layer_types) == len(decoder_layers):
        layer_types = [str(value) for value in raw_layer_types]
    else:
        layer_types = []
        for decoder_layer in decoder_layers:
            layer_type = getattr(decoder_layer, "attention_type", None)
            if layer_type is None:
                layer_type = getattr(getattr(decoder_layer, "self_attn", None), "layer_type", None)
            layer_types.append(str(layer_type or "unknown"))

    return {
        "model_type": str(getattr(text_config, "model_type", "unknown")),
        "layer_count": len(decoder_layers),
        "hidden_size": _integer("hidden_size"),
        "intermediate_size": _integer("intermediate_size"),
        "attention_heads": _integer("num_attention_heads"),
        "key_value_heads": _integer("num_key_value_heads"),
        "head_dim": _integer("head_dim"),
        "sliding_window": _integer("sliding_window"),
        "max_position_embeddings": _integer("max_position_embeddings"),
        "layer_types": layer_types,
    }


def capture_model_probe_values(
    residual_last: torch.Tensor,
    logits_last: torch.Tensor,
    requested_keys: Collection[str],
    *,
    logits_top_k: int = 8,
) -> dict[str, object]:
    """Materialize only requested observations from two real model locations."""
    requested = set(requested_keys)
    probes: dict[str, object] = {}
    residual_keys = {
        "model.residual.rms",
        "model.residual.max_abs",
        "model.residual.vector",
    }
    if requested & residual_keys:
        residual = residual_last.detach().float().reshape(-1)
        if "model.residual.rms" in requested:
            rms = torch.sqrt(torch.mean(residual.square())).item() if residual.numel() else 0.0
            probes["model.residual.rms"] = {"raw": rms, "normalized": None}
        if "model.residual.max_abs" in requested:
            maximum = residual.abs().max().item() if residual.numel() else 0.0
            probes["model.residual.max_abs"] = {"raw": maximum, "normalized": None}
        if "model.residual.vector" in requested:
            probes["model.residual.vector"] = {
                "values": residual.cpu().tolist(),
                "shape": [residual.numel()],
                "dtype": "float32",
            }

    logits_keys = {
        "model.logits.entropy",
        "model.logits.top_probability",
        "model.logits.margin",
        "model.logits.top_k",
    }
    if requested & logits_keys:
        logits = logits_last.detach().float().reshape(-1)
        probabilities = torch.softmax(logits, dim=-1)
        count = logits.numel()
        top_count = min(max(1, int(logits_top_k)), count) if count else 0
        top_logits, top_indices = torch.topk(logits, top_count) if top_count else (logits, logits.long())
        top_probabilities = probabilities[top_indices] if top_count else probabilities

        if "model.logits.entropy" in requested:
            entropy = -(probabilities * probabilities.clamp_min(1e-12).log()).sum().item()
            maximum_entropy = math.log(count) if count > 1 else 1.0
            probes["model.logits.entropy"] = {
                "raw": entropy,
                "normalized": min(max(entropy / maximum_entropy, 0.0), 1.0),
            }
        if "model.logits.top_probability" in requested:
            probability = top_probabilities[0].item() if top_count else 0.0
            probes["model.logits.top_probability"] = {
                "raw": probability,
                "normalized": probability,
            }
        if "model.logits.margin" in requested:
            margin = (top_logits[0] - top_logits[1]).item() if top_count > 1 else 0.0
            probes["model.logits.margin"] = {
                "raw": margin,
                "normalized": 1.0 - math.exp(-max(0.0, margin)),
            }
        if "model.logits.top_k" in requested:
            probes["model.logits.top_k"] = {
                "items": [
                    {
                        "token_id": int(token_id),
                        "logit": float(logit),
                        "probability": float(probability),
                    }
                    for token_id, logit, probability in zip(
                        top_indices.cpu().tolist(),
                        top_logits.cpu().tolist(),
                        top_probabilities.cpu().tolist(),
                    )
                ],
                "shape": [top_count],
                "dtype": "token_logit",
            }
    return probes


def inspect_live(
    prompt: str,
    model,
    tokenizer,
    sae: JumpReluSAE,
    layer: int,
    neuronpedia: NeuronpediaScope,
    max_new_tokens: int = 200,
    probe_keys: Collection[str] | Callable[[], Collection[str]] | None = None,
    observation_layer: int | Callable[[], int] | None = None,
    probe_rack: Collection[dict] | Callable[[], Collection[dict]] | None = None,
) -> Generator[tuple[TokenAnalysis, int], None, None]:
    """Generate tokens and observe distinct dense and sparse model locations.

    ``layer`` is the attachment site of the loaded SAE. ``observation_layer``
    independently selects the residual stream used by model probes and may be a
    callback so browser changes affect the next token. Yields
    ``(TokenAnalysis, elapsed_ms)`` per token.
    """
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=True)
    input_ids = inputs["input_ids"].to(device)
    print(f"[inspect_live] Starting generation loop (max_new_tokens={max_new_tokens or 'unlimited'}, input_len={input_ids.shape[1]})", file=sys.stderr, flush=True)

    _steps = range(max_new_tokens) if max_new_tokens > 0 else itertools.count()
    for step in _steps:
        if step == 0:
            print("[inspect_live] Running first forward pass...", file=sys.stderr, flush=True)
        t0 = time.perf_counter()
        decoder_layers = _get_decoder_layers(model)
        requested_layer = observation_layer() if callable(observation_layer) else observation_layer
        probe_layer = _safe_layer_index(
            layer if requested_layer is None else requested_layer,
            len(decoder_layers),
            layer,
        )
        requested_probe_keys = probe_keys() if callable(probe_keys) else (probe_keys or ())
        requested_probe_rack = probe_rack() if callable(probe_rack) else probe_rack
        if requested_probe_rack is None:
            requested_probe_rack = []
        capture_layers = (
            range(len(decoder_layers))
            if "model.layer_profile" in requested_probe_keys
            else {layer, probe_layer}
        )
        captured_residuals: dict[int, torch.Tensor] = {}

        def make_residual_hook(layer_index: int):
            def residual_hook(_module, _input, output):
                hidden = output[0] if isinstance(output, (tuple, list)) else output
                captured_residuals[layer_index] = hidden.detach().squeeze(0)[-1, :]

            return residual_hook

        hooks = [
            decoder_layers[layer_index].register_forward_hook(
                make_residual_hook(layer_index)
            )
            for layer_index in sorted(capture_layers)
        ]
        from app.server.pipeline.model_probes import GemmaProbeManager

        probe_manager = GemmaProbeManager(
            model,
            requested_probe_rack,
            sae_layer=layer,
        )
        try:
            with probe_manager.capture():
                outputs = model(input_ids)
        finally:
            for hook in hooks:
                hook.remove()
        if step == 0:
            print("[inspect_live] First forward pass complete.", file=sys.stderr, flush=True)

        sae_residual_last = captured_residuals[layer]
        probe_residual_last = captured_residuals[probe_layer]

        next_token_id = int(outputs.logits[0, -1].argmax().item())

        probe_values = capture_model_probe_values(
            probe_residual_last,
            outputs.logits[0, -1],
            requested_probe_keys,
        )
        if "model.layer_profile" in requested_probe_keys:
            layer_profile = summarize_layer_residuals(
                [captured_residuals[index] for index in range(len(decoder_layers))]
            )
            probe_values["model.layer_profile"] = {
                "layers": layer_profile,
                "shape": [len(layer_profile)],
                "dtype": "layer_profile",
            }

        sae_acts = sae.encode(sae_residual_last.float().unsqueeze(0)).squeeze(0)

        active_indices = (sae_acts > 0).nonzero(as_tuple=True)[0].tolist()
        l0 = len(active_indices)
        active_features = [
            ActiveFeature(
                index=i,
                activation=sae_acts[i].item(),
                description=neuronpedia.explanations.get(i),
            )
            for i in active_indices
        ]

        active_feature_payloads = [feature.model_dump() for feature in active_features]
        from app.server.pipeline.model_probes import build_sae_probe_observations

        probe_observations = probe_manager.tensor_observations(
            model_id=str(getattr(model, "name_or_path", "") or getattr(getattr(model, "config", None), "_name_or_path", "") or "unknown"),
            token_index=step + 1,
        )
        probe_observations.extend(
            build_sae_probe_observations(
                requested_probe_rack,
                active_feature_payloads,
                sae_layer=layer,
                sae_width=str(getattr(neuronpedia, "width", "unknown")),
                model_id=str(getattr(model, "name_or_path", "") or getattr(getattr(model, "config", None), "_name_or_path", "") or "unknown"),
                token_index=step + 1,
            )
        )

        token_str = tokenizer.decode([next_token_id])
        token_analysis = TokenAnalysis(
            token_id=next_token_id,
            token=token_str,
            l0=l0,
            active_features=active_features,
            probe_values=probe_values,
            probe_layer=probe_layer,
            probes=probe_observations,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        yield token_analysis, elapsed_ms

        if next_token_id == tokenizer.eos_token_id:
            break

        input_ids = torch.cat(
            [input_ids, torch.tensor([[next_token_id]], device=device)],
            dim=1,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract SAE feature activations from a language model generation."
    )
    parser.add_argument("prompt", type=str, help="Prompt to generate from")
    parser.add_argument(
        "--model", default="google/gemma-3-1b-pt", help="HuggingFace model ID"
    )
    parser.add_argument("--layer", type=int, default=22, help="Transformer layer index")
    parser.add_argument("--width", default="65k", help="SAE width (e.g. 65k)")
    parser.add_argument("--l0", default="medium", help="SAE L0 target (e.g. medium)")
    parser.add_argument(
        "--max-tokens", type=int, default=200, help="Maximum new tokens to generate"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/analysis.json"),
        help="Output JSON path",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    parser.add_argument(
        "--stream", action="store_true", help="Emit NDJSON per token to stdout"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Replay recorded tokens indefinitely after generation (Ctrl+C to stop)",
    )
    args = parser.parse_args()

    def log(msg: str) -> None:
        if args.verbose:
            print(msg, file=sys.stderr)

    log(f"Loading model {args.model}...")
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    log(f"Loading SAE (layer={args.layer}, width={args.width}, l0={args.l0})...")
    sae = load_sae(layer=args.layer, width=args.width, l0=args.l0, device=device)

    log(f"Downloading Neuronpedia explanations for layer {args.layer} {args.width}...")
    neuronpedia = download_neuronpedia_explanations("gemma-3-1b", args.layer, args.width)
    log(f"  Loaded {len(neuronpedia.explanations)} feature descriptions.")

    if args.stream:
        meta = {
            "type": "meta",
            "model_id": args.model,
            "layer": args.layer,
            "sae_width": args.width,
        }
        print(json.dumps(meta), flush=True)

    log(f"Running generation for prompt: {args.prompt!r}")

    results: list[tuple[TokenAnalysis, int]] = []
    try:
        for token_analysis, elapsed_ms in inspect_live(
            args.prompt,
            model,
            tokenizer,
            sae,
            args.layer,
            neuronpedia,
            max_new_tokens=args.max_tokens,
        ):
            results.append((token_analysis, elapsed_ms))

            is_eos = token_analysis.token_id == tokenizer.eos_token_id
            if is_eos:
                print(f"[extract] EOS token received after {len(results)} tokens", file=sys.stderr, flush=True)

            if args.stream:
                event = {
                    "type": "token",
                    "token_id": token_analysis.token_id,
                    "token": token_analysis.token,
                    "l0": token_analysis.l0,
                    "active_features": [f.model_dump() for f in token_analysis.active_features],
                    "elapsed_ms": elapsed_ms,
                }
                print(json.dumps(event), flush=True)
    except KeyboardInterrupt:
        sys.exit(0)

    token_analyses = [ta for ta, _ in results]
    full_text = tokenizer.decode(
        [t.token_id for t in token_analyses], skip_special_tokens=True
    )
    result = GenerationAnalysis(
        prompt=args.prompt,
        model_id=args.model,
        layer=args.layer,
        sae_width=args.width,
        generated_tokens=token_analyses,
        full_generated_text=full_text,
    )

    export_to_json(result, args.output)
    log(f"Exported analysis to {args.output}")

    if args.loop:
        token_events = [
            {
                "type": "token",
                "token_id": ta.token_id,
                "token": ta.token,
                "l0": ta.l0,
                "active_features": [f.model_dump() for f in ta.active_features],
                "elapsed_ms": elapsed_ms,
            }
            for ta, elapsed_ms in results
        ]
        try:
            loop_count = 0
            while True:
                loop_count += 1
                print(f"[loop] starting replay iteration {loop_count} ({len(token_events)} tokens)", file=sys.stderr, flush=True)
                for event in token_events:
                    print(json.dumps(event), flush=True)
                    time.sleep(event["elapsed_ms"] / 1000)
        except KeyboardInterrupt:
            pass
