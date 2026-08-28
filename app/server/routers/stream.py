"""stream.py: WebSocket endpoint for live pipeline streaming."""
import asyncio
import dataclasses
import json
import logging
import sys
import threading
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.server.pipeline.external_output import build_activation_event
from app.server.pipeline.osc_output import OscResult, OscRunOutput
from app.server.pipeline.ossia_probe_output import (
    OssiaProbeOutput,
    OssiaResult,
)
from app.server.routers.config import MODEL_CATALOGUE, SAE_REPO_MAP
from app.server.routers.integrations import publish_activation
from app.server.session import PipelineParams, PipelineSession

logger = logging.getLogger(__name__)
router = APIRouter()

# Language-model/tokenizer cache. Layer-specific SAEs use the separate exact
# provenance key below.
_model_cache: dict[str, dict] = {}

# Exact pretrained SAE runtime cache:
# (model, repo, category, layer, width, l0) -> SaeRuntime
_sae_runtime_cache: dict[tuple, object] = {}
_sae_runtime_lock = threading.RLock()

# Cluster map cache: (model_id, layer, width, clusters) -> cluster_map dict
_cluster_cache: dict[tuple, dict] = {}

# Enriched cluster map cache: (model_id, layer, width) -> {cluster_map, palette}
_enriched_cluster_cache: dict[tuple, dict] = {}

# Semantic tonality runtime cache: embed_model -> {cache, embedder}
_tonality_runtime_cache: dict[str, dict] = {}
_tonality_runtime_lock = threading.RLock()

# One shared session (single-user for now)
_session = PipelineSession()


def _resolve_sae_layer(requested: object, available_layers: list[int]) -> int:
    """Choose only a layer for which the selected model advertises an SAE."""
    if not available_layers:
        raise ValueError("Selected model has no configured SAE layers")
    ordered = sorted({int(layer) for layer in available_layers})
    try:
        selected = int(requested)
    except (TypeError, ValueError):
        return ordered[0]
    if selected in ordered:
        return selected
    if selected <= ordered[0]:
        return ordered[0]
    if selected >= ordered[-1]:
        return ordered[-1]
    return min(ordered, key=lambda layer: (abs(layer - selected), layer))


def _get_sae_runtime(params: PipelineParams, model_spec: dict, requested_layer: object):
    """Load or reuse the exact pretrained SAE bound to one advertised layer."""
    from app.server.pipeline.extract import (
        NeuronpediaScope,
        SaeRuntime,
        download_neuronpedia_explanations,
        load_sae,
    )

    layer = _resolve_sae_layer(requested_layer, list(model_spec.get("layers") or []))
    widths = [str(width) for width in model_spec.get("widths") or []]
    width = str(params.width) if str(params.width) in widths else widths[0]
    l0s = [str(value) for value in model_spec.get("l0s") or []]
    l0 = str(params.l0) if str(params.l0) in l0s else l0s[0]
    category = str(model_spec.get("sae_category") or "resid_post")
    repo_id = SAE_REPO_MAP[params.model]
    key = (params.model, repo_id, category, layer, width, l0)

    with _sae_runtime_lock:
        cached = _sae_runtime_cache.get(key)
        if cached is not None:
            return cached

        sae = load_sae(
            layer=layer,
            width=width,
            l0=l0,
            category=category,
            sae_repo_id=repo_id,
        )
        neuronpedia_model = params.model.split("/")[-1].replace("-pt", "")
        if model_spec.get("neuronpedia", True):
            neuronpedia = download_neuronpedia_explanations(
                neuronpedia_model,
                layer,
                width,
            )
        else:
            neuronpedia = NeuronpediaScope(
                model_id=neuronpedia_model,
                layer=layer,
                width=width,
                explanations={},
            )
        runtime = SaeRuntime(
            sae=sae,
            neuronpedia=neuronpedia,
            layer=layer,
            width=width,
            l0=l0,
            category=category,
            repo_id=repo_id,
            revision=str(getattr(sae, "source_revision", "") or ""),
        )
        _sae_runtime_cache[key] = runtime
        return runtime


def _live_sae_runtime_resolver(params: PipelineParams, model_spec: dict):
    """Resolve mutable session selection at the next token boundary."""
    return lambda: _get_sae_runtime(params, model_spec, params.layer)


@dataclasses.dataclass(frozen=True)
class LoadingStage:
    """One stable preparation stage shown by the browser Emitter."""

    key: str
    label: str


LOADING_STAGES = (
    LoadingStage("model", "Language model"),
    LoadingStage("sae", "Sparse autoencoder"),
    LoadingStage("neuronpedia", "Neuronpedia descriptions"),
    LoadingStage("features", "Feature organization"),
    LoadingStage("tonality", "Semantic tonalities"),
    LoadingStage("generation", "Generation"),
)
_LOADING_STATES = {"active", "complete", "cached", "skipped"}


def _loading_event(
    stage_key: str,
    state: str,
    detail: str = "",
) -> dict:
    """Build a stable, JSON-ready progress event for a preparation stage."""
    if state not in _LOADING_STATES:
        raise ValueError(f"Unknown loading state: {state}")
    try:
        stage_index, stage = next(
            (index, stage)
            for index, stage in enumerate(LOADING_STAGES)
            if stage.key == stage_key
        )
    except StopIteration as exc:
        raise ValueError(f"Unknown loading stage: {stage_key}") from exc

    completed_steps = stage_index if state == "active" else stage_index + 1
    return {
        "type": "loading",
        "stage_key": stage.key,
        "label": stage.label,
        "state": state,
        "detail": detail,
        "step": stage_index + 1,
        "total": len(LOADING_STAGES),
        "progress": completed_steps / len(LOADING_STAGES),
    }


async def _send(ws: WebSocket, msg: dict) -> None:
    await ws.send_text(json.dumps(msg))


async def _receive_command(ws: WebSocket) -> dict:
    """Decode browser text frames and score 3.8 binary JSON frames alike."""
    frame = await ws.receive()
    if frame.get("type") == "websocket.disconnect":
        raise WebSocketDisconnect(frame.get("code", 1000))

    raw = frame.get("text")
    if raw is None:
        payload = frame.get("bytes")
        if payload is None:
            raise ValueError("Invalid JSON")
        try:
            raw = payload.decode("utf8")
        except UnicodeDecodeError as exc:
            raise ValueError("Invalid JSON") from exc

    try:
        message = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Invalid JSON") from exc
    if not isinstance(message, dict):
        raise ValueError("Invalid JSON")
    return message


def _token_event_queue() -> asyncio.Queue:
    """Keep a bounded handoff between model generation and event forwarding."""
    return asyncio.Queue(maxsize=1)


def _put_token_event(
    queue: asyncio.Queue,
    event: dict,
    event_loop: asyncio.AbstractEventLoop,
    activation_event: dict | None = None,
) -> None:
    """Block the model thread until the current token has been presented.

    Queue capacity alone lets generation begin the next forward as soon as the
    consumer calls ``get``. The delivery event keeps the live parameter window
    aligned with the token the browser or score interface just saw.
    """
    delivered = threading.Event()
    event_loop.call_soon_threadsafe(
        queue.put_nowait,
        (event, activation_event, delivered),
    )
    delivered.wait()


def _observation_payload(token_analysis, params: PipelineParams) -> dict:
    """Describe the actual dense and token-bound SAE representations."""
    payload = {
        "model": params.model,
        "site": "residual_post",
        "layer": token_analysis.probe_layer,
        "module_path": token_analysis.probe_module_path,
        "shape": token_analysis.probe_shape,
        "dtype": token_analysis.probe_dtype,
        "representation": token_analysis.probe_representation,
        "sae_layer": getattr(token_analysis, "sae_layer", params.layer),
        "sae_width": getattr(token_analysis, "sae_width", params.width),
        "sae_module_path": token_analysis.sae_module_path,
        "sae_shape": token_analysis.sae_shape,
        "sae_dtype": token_analysis.sae_dtype,
        "sae_representation": token_analysis.sae_representation,
    }
    for field in ("sae_l0", "sae_category", "sae_repo_id", "sae_revision"):
        if hasattr(token_analysis, field):
            payload[field] = getattr(token_analysis, field)
    return payload


async def _stop_session(ws: WebSocket, session: PipelineSession) -> None:
    """Cancel once and avoid duplicating the pipeline's final stopped event."""
    pipeline_will_report = session.is_running()
    await session.cancel()
    if not pipeline_will_report:
        await _send(ws, {"type": "stopped"})


async def _send_loading(
    ws: WebSocket,
    stage_key: str,
    state: str,
    detail: str = "",
) -> None:
    await _send(ws, _loading_event(stage_key, state, detail))


async def _call_osc(
    ws: WebSocket,
    operation,
    *args,
    report_status: bool = False,
) -> OscResult:
    """Run a failure-isolated OSC operation outside the WebSocket event loop."""
    try:
        result = await asyncio.to_thread(operation, *args)
    except Exception as exc:  # defensive: the OSC helper itself must not escape
        logger.exception("Unexpected OSC output error")
        result = OscResult("error", f"OSC output error: {exc}", error=str(exc))

    if report_status or result.state == "error":
        try:
            await _send(
                ws,
                {
                    "type": "osc_status",
                    "status": result.state,
                    "message": result.message,
                },
            )
        except Exception:
            logger.debug("Could not send OSC status to browser", exc_info=True)
    return result


async def _forward_token_event(
    ws: WebSocket,
    event: dict,
    params: PipelineParams,
    osc_output: OscRunOutput,
    ossia_output: OssiaProbeOutput | None = None,
    *,
    activation_event: dict | None = None,
) -> OscResult:
    """Forward one token to each independent browser and connector consumer."""
    await _send(ws, event)
    result = await _call_osc(ws, osc_output.emit_token, params, event)
    if ossia_output is not None:
        await _call_ossia(ws, ossia_output.emit_token, params, event)
    if activation_event is not None:
        await publish_activation(activation_event)
    return result


async def _call_ossia(
    ws: WebSocket,
    operation,
    *args,
    report_status: bool = False,
) -> OssiaResult:
    """Run the optional libossia sidecar without risking generation."""
    try:
        result = await asyncio.to_thread(operation, *args)
    except Exception as exc:
        logger.exception("Unexpected libossia Connector error")
        result = OssiaResult("error", f"libossia Connector error: {exc}", str(exc))
    if report_status or result.state == "error":
        try:
            await _send(
                ws,
                {
                    "type": "ossia_status",
                    "status": result.state,
                    "message": result.message,
                },
            )
        except Exception:
            logger.debug("Could not send libossia status to browser", exc_info=True)
    return result


async def _sync_live_ossia(
    ws: WebSocket,
    params: PipelineParams,
    ossia_output: OssiaProbeOutput,
) -> OssiaResult:
    return await _call_ossia(
        ws,
        ossia_output.sync,
        params,
        report_status=True,
    )


async def _sync_live_osc_controls(
    ws: WebSocket,
    params: PipelineParams,
    osc_output: OscRunOutput,
    changed_fields: set[str],
) -> OscResult:
    """Apply live OSC destination/control edits without restarting the run."""
    return await _call_osc(
        ws,
        osc_output.sync_controls,
        params,
        changed_fields,
        report_status=True,
    )


def _get_tonality_runtime() -> dict:
    """Load the shared MiniLM tonality cache/embedder once per process."""
    from app.server.pipeline.semantic_tonality import DEFAULT_EMBED_MODEL
    from sentence_transformers import SentenceTransformer
    import torch

    embedder_key = f"{DEFAULT_EMBED_MODEL}:embedder"
    if embedder_key in _tonality_runtime_cache:
        return _tonality_runtime_cache[embedder_key]

    embed_device = "cuda" if torch.cuda.is_available() else "cpu"
    embedder = SentenceTransformer(DEFAULT_EMBED_MODEL, device=embed_device)
    runtime = {"embedder": embedder}
    _tonality_runtime_cache[embedder_key] = runtime
    return runtime


def _get_tonality_cache_runtime_unlocked(raw_lenses: list[dict] | None = None) -> dict:
    """Return an embedded tonality cache for the current live lens set."""
    import hashlib

    from app.server.pipeline.semantic_tonality import (
        DEFAULT_EMBED_MODEL,
        build_tonality_embedding_cache,
        coerce_tonality_lenses,
        load_tonality_descriptions,
    )

    lenses = raw_lenses or []
    lens_hash = "default"
    if lenses:
        payload = json.dumps(lenses, ensure_ascii=True, sort_keys=True, default=str)
        lens_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    cache_key = f"{DEFAULT_EMBED_MODEL}:cache:{lens_hash}"
    if cache_key in _tonality_runtime_cache:
        return _tonality_runtime_cache[cache_key]

    embed_runtime = _get_tonality_runtime()
    tonality_set = coerce_tonality_lenses(lenses) if lenses else load_tonality_descriptions()
    tonality_cache = build_tonality_embedding_cache(
        tonality_set,
        embed_model=DEFAULT_EMBED_MODEL,
        embedder=embed_runtime["embedder"],
    )
    runtime = {
        "cache": tonality_cache,
        "embedder": embed_runtime["embedder"],
        "lens_count": len(tonality_cache.tonalities),
    }
    _tonality_runtime_cache[cache_key] = runtime
    return runtime


def _get_tonality_cache_runtime(raw_lenses: list[dict] | None = None) -> dict:
    """Serialize MiniLM cache builds so live edits cannot race generation."""
    with _tonality_runtime_lock:
        return _get_tonality_cache_runtime_unlocked(raw_lenses)


async def _prepare_live_tonality_lenses(ws: WebSocket, lenses: list[dict]) -> None:
    """Re-embed edited lens text and report an honest browser-visible status."""
    await _send(ws, {"type": "tonality_lenses_status", "status": "embedding"})
    try:
        runtime = await asyncio.to_thread(_get_tonality_cache_runtime, lenses)
    except Exception as exc:
        logger.exception("Could not embed live tonality lenses")
        await _send(
            ws,
            {
                "type": "tonality_lenses_status",
                "status": "error",
                "message": str(exc),
            },
        )
        return
    await _send(
        ws,
        {
            "type": "tonality_lenses_status",
            "status": "ready",
            "lens_count": runtime["lens_count"],
        },
    )


async def _run_pipeline(ws: WebSocket, params: PipelineParams) -> None:
    """Background task: load model (cached), run inspect_live, stream token events."""
    run_id = uuid.uuid4().hex
    osc_output = OscRunOutput(run_id)
    ossia_output = OssiaProbeOutput(run_id)
    _session.osc_output = osc_output
    _session.ossia_output = ossia_output
    try:
        await _sync_live_ossia(ws, params, ossia_output)
        model_spec = MODEL_CATALOGUE.get(params.model)
        if model_spec is None:
            raise ValueError(f"Unsupported model: {params.model}")
        params.layer = _resolve_sae_layer(params.layer, model_spec["layers"])
        if str(params.width) not in model_spec["widths"]:
            params.width = str(model_spec["widths"][0])
        if str(params.l0) not in model_spec["l0s"]:
            params.l0 = str(model_spec["l0s"][0])

        if params.model in _model_cache:
            print("[pipeline] Using cached language model.", file=sys.stderr, flush=True)
            cached = _model_cache[params.model]
            model = cached["model"]
            tokenizer = cached["tokenizer"]
            await _send_loading(ws, "model", "cached", f"{params.model} · runtime memory")
        else:
            print(f"[pipeline] Loading language model: {params.model}", file=sys.stderr, flush=True)
            await _send_loading(ws, "model", "active", params.model)

            def _load_model():
                from transformers import AutoModelForCausalLM, AutoTokenizer
                _model = AutoModelForCausalLM.from_pretrained(params.model, device_map="auto")
                _tokenizer = AutoTokenizer.from_pretrained(params.model)
                return _model, _tokenizer

            model, tokenizer = await asyncio.to_thread(_load_model)
            print("[pipeline] Language model loaded.", file=sys.stderr, flush=True)
            await _send_loading(ws, "model", "complete", f"{params.model} ready")
            _model_cache[params.model] = {
                "model": model,
                "tokenizer": tokenizer,
            }

        runtime_key = (
            params.model,
            SAE_REPO_MAP[params.model],
            model_spec["sae_category"],
            params.layer,
            params.width,
            params.l0,
        )
        runtime_was_cached = runtime_key in _sae_runtime_cache
        await _send_loading(
            ws,
            "sae",
            "cached" if runtime_was_cached else "active",
            f"Layer {params.layer} · {model_spec['sae_category']} · "
            f"width {params.width} · L0 {params.l0}",
        )
        initial_sae_runtime = await asyncio.to_thread(
            _get_sae_runtime,
            params,
            model_spec,
            params.layer,
        )
        sae = initial_sae_runtime.sae
        neuronpedia = initial_sae_runtime.neuronpedia
        if not runtime_was_cached:
            await _send_loading(
                ws,
                "sae",
                "complete",
                f"Layer {params.layer} · width {params.width} ready",
            )
        if model_spec.get("neuronpedia", True):
            await _send_loading(
                ws,
                "neuronpedia",
                "cached" if runtime_was_cached else "complete",
                f"{len(neuronpedia.explanations):,} exact-scope descriptions ready",
            )
        else:
            await _send_loading(
                ws,
                "neuronpedia",
                "skipped",
                "No descriptions are assigned to the all-layer SAE series",
            )
        resolve_live_sae = _live_sae_runtime_resolver(params, model_spec)

        from app.server.pipeline.extract import describe_model_architecture

        await _send(
            ws,
            {
                "type": "model_structure",
                "model": params.model,
                "architecture": describe_model_architecture(model),
            },
        )

        # Do not borrow descriptions or cluster assignments from a different
        # SAE family merely because its layer and width happen to match.
        raw_all_layer_sae = not model_spec.get("neuronpedia", True)
        cluster_map: dict = {}
        if raw_all_layer_sae:
            enriched_data = {"cluster_map": {}, "palette": []}
            await _send_loading(
                ws,
                "features",
                "skipped",
                "Raw layer-specific features; no cross-SAE semantic assignments",
            )
        else:
            enriched_key = (params.model, params.layer, params.width)
            enriched_was_cached = enriched_key in _enriched_cluster_cache
            cluster_was_cached = params.strategy != "cluster"
            await _send_loading(
                ws,
                "features",
                "active",
                "Reading feature organization from memory"
                if enriched_was_cached
                else "Naming feature clusters and preparing colours",
            )
            if not enriched_was_cached:

                def _build_enriched():
                    from app.server.pipeline.cluster_naming import build_enriched_cluster_map
                    from sentence_transformers import SentenceTransformer
                    import torch
                    embed_device = "cuda" if torch.cuda.is_available() else "cpu"
                    _embed_model = SentenceTransformer("all-MiniLM-L6-v2", device=embed_device)
                    np_model_id = params.model.split("/")[-1].replace("-pt", "")
                    return build_enriched_cluster_map(
                        np_model_id,
                        params.layer,
                        params.width,
                        neuronpedia,
                        _embed_model,
                    )

                enriched_data = await asyncio.to_thread(_build_enriched)
                _enriched_cluster_cache[enriched_key] = enriched_data
                print(
                    f"[pipeline] Enriched cluster map ready: {len(enriched_data.get('cluster_map', {}))} entries.",
                    file=sys.stderr, flush=True,
                )
            else:
                enriched_data = _enriched_cluster_cache[enriched_key]
                print("[pipeline] Enriched cluster map from cache.", file=sys.stderr, flush=True)

            if params.strategy == "cluster":
                from app.server.pipeline.transform import build_cluster_map

                cluster_key = (params.model, params.layer, params.width, params.clusters)
                cluster_was_cached = cluster_key in _cluster_cache
                if cluster_was_cached:
                    cluster_map = _cluster_cache[cluster_key]
                    print(f"[pipeline] Cluster map from in-memory cache: {len(cluster_map)} entries.", file=sys.stderr, flush=True)
                    logger.info("Cluster map loaded from in-memory cache: %d entries", len(cluster_map))
                else:
                    await _send_loading(
                        ws,
                        "features",
                        "active",
                        f"Building {params.clusters}-cluster performance map",
                    )
                    print(f"[pipeline] Building cluster map (clusters={params.clusters})...", file=sys.stderr, flush=True)

                    def _build_clusters():
                        np_model_id = params.model.split("/")[-1].replace("-pt", "")
                        return build_cluster_map(
                            np_model_id,
                            params.layer,
                            params.width,
                            params.clusters,
                            "all-MiniLM-L6-v2",
                        )

                    cluster_map = await asyncio.to_thread(_build_clusters)
                    _cluster_cache[cluster_key] = cluster_map

                print(f"[pipeline] Cluster map ready: {len(cluster_map)} entries.", file=sys.stderr, flush=True)
                logger.info("Cluster map ready: %d entries", len(cluster_map))

            features_cached = enriched_was_cached and cluster_was_cached
            await _send_loading(
                ws,
                "features",
                "cached" if features_cached else "complete",
                f"{len(enriched_data.get('cluster_map', {})):,} feature assignments ready",
            )

        enriched_map = enriched_data.get("cluster_map", {})
        palette = enriched_data.get("palette", [])

        await _send(ws, {"type": "cluster_palette", "palette": palette})

        tonality_runtime: dict | None = None
        prompt_embedding = None
        if params.tonality_enabled:
            await _send_loading(ws, "tonality", "active", "Embedding active verbal lenses")
            tonality_runtime = await asyncio.to_thread(_get_tonality_cache_runtime, params.tonality_lenses)

            if params.prompt.strip():
                def _embed_prompt():
                    from app.server.pipeline.semantic_tonality import embed_text

                    return embed_text(
                        params.prompt,
                        embed_model=tonality_runtime["cache"].embed_model,
                        embedder=tonality_runtime["embedder"],
                    )

                prompt_embedding = await asyncio.to_thread(_embed_prompt)
            await _send_loading(
                ws,
                "tonality",
                "complete",
                f"{tonality_runtime['lens_count']} verbal lenses ready",
            )
        else:
            await _send_loading(ws, "tonality", "skipped", "Disabled for this run")

        await _send_loading(ws, "generation", "active", "Waiting for the first token")

        from app.server.pipeline.extract import inspect_live
        from app.server.pipeline.emitter_mapping import EmitterMappingRuntime
        from app.server.pipeline.semantic_tonality import (
            TonalityMemory,
            apply_tonality_pitch_bias,
            build_tonality_evidence,
            match_active_features_and_prompt_to_tonalities,
            tonality_result_to_payload,
        )
        from app.server.pipeline.transform import apply_identity, apply_cluster

        print(f"[pipeline] Starting pipeline: prompt={params.prompt!r} strategy={params.strategy} clusters={params.clusters}", file=sys.stderr, flush=True)
        logger.info("Starting pipeline: prompt=%r strategy=%s clusters=%s", params.prompt, params.strategy, params.clusters)
        await _call_osc(ws, osc_output.begin, params, report_status=True)

        # Producer + synthesizer: run generation concurrently with timed playback
        queue = _token_event_queue()
        collected: list[tuple[dict, dict | None]] = []
        event_loop = asyncio.get_running_loop()
        tonality_memory = TonalityMemory()
        emitter_mapping_runtime = EmitterMappingRuntime()

        async def _producer():
            try:
                token_count = 0

                def _generate():
                    nonlocal prompt_embedding, token_count
                    print(f"[pipeline] Generation starting (max_tokens={params.max_tokens})...", file=sys.stderr, flush=True)
                    logger.info("Starting generation: max_tokens=%d", params.max_tokens)
                    def _requested_probe_keys() -> set[str]:
                        mapping_sources = {
                            str(mapping.get("source") or "")
                            for mapping in params.emitter_mappings
                            if mapping.get("enabled", True)
                        }
                        return set(params.emitter_signal_keys) | mapping_sources

                    for token_analysis, elapsed_ms in inspect_live(
                        params.prompt, model, tokenizer, sae,
                        params.layer, neuronpedia,
                        max_new_tokens=params.max_tokens,
                        probe_keys=_requested_probe_keys,
                        observation_layer=lambda: params.observation_layer,
                        probe_rack=lambda: params.probe_rack,
                        sae_runtime=resolve_live_sae,
                    ):
                        token_count += 1
                        active_features = [f.model_dump() for f in token_analysis.active_features]
                        if params.strategy == "cluster":
                            notes = apply_cluster(active_features, cluster_map)
                        else:
                            notes = apply_identity(active_features)

                        # Enrich notes with cluster visualization metadata
                        for note, feat in zip(notes, active_features):
                            idx = feat["index"]
                            if idx in enriched_map:
                                entry = enriched_map[idx]
                                note["cluster"] = entry["cluster_id"]   # align with enriched map for viz consistency
                                note["cluster_name"] = entry["cluster_name"]
                                note["cluster_color"] = entry["cluster_color"]
                            else:
                                note["cluster"] = None                  # exclude from cluster totals
                                note["cluster_name"] = ""
                                note["cluster_color"] = "#888888"
                            note["feature_index"] = idx
                            note["feature_description"] = feat.get("description") or ""

                        tonality_payload = None
                        if params.tonality_enabled:
                            current_tonality_runtime = _get_tonality_cache_runtime(params.tonality_lenses)
                            if prompt_embedding is None and params.prompt.strip():
                                from app.server.pipeline.semantic_tonality import embed_text

                                prompt_embedding = embed_text(
                                    params.prompt,
                                    embed_model=current_tonality_runtime["cache"].embed_model,
                                    embedder=current_tonality_runtime["embedder"],
                                )
                            tonality_result = match_active_features_and_prompt_to_tonalities(
                                active_features,
                                current_tonality_runtime["cache"],
                                prompt_embedding=prompt_embedding,
                                prompt_influence=params.prompt_influence,
                                top_k=3,
                                embedder=current_tonality_runtime["embedder"],
                            )
                            notes = apply_tonality_pitch_bias(
                                notes,
                                tonality_result,
                                pitch_bias=params.tonality_pitch_bias,
                            )
                            tonality_payload = tonality_result_to_payload(
                                tonality_result,
                                pitch_bias=params.tonality_pitch_bias,
                            )
                            tonality_payload["lens_count"] = current_tonality_runtime["lens_count"]
                            tonality_payload["lens_set"] = current_tonality_runtime["cache"].name
                            tonality_payload["memory"] = tonality_memory.update(tonality_result)
                            tonality_payload["evidence"] = build_tonality_evidence(active_features, notes)

                        event = {
                            "type": "token",
                            "token": token_analysis.token,
                            "token_id": token_analysis.token_id,
                            "elapsed_ms": elapsed_ms,
                            "notes": notes,
                            "probes": [
                                {**probe, "model": params.model}
                                for probe in token_analysis.probes
                            ],
                            "observation": _observation_payload(
                                token_analysis,
                                params,
                            ),
                            "emitter": emitter_mapping_runtime.build_payload(
                                active_features=active_features,
                                notes=notes,
                                tonality=tonality_payload,
                                mappings=params.emitter_mappings,
                                elapsed_ms=elapsed_ms,
                                token_index=token_count,
                                max_tokens=params.max_tokens,
                                width=params.width,
                                probe_values=token_analysis.probe_values,
                                selected_signal_keys=params.emitter_signal_keys,
                            ),
                        }
                        if tonality_payload is not None:
                            event["tonality"] = tonality_payload
                        activation_event = build_activation_event(
                            run_id=osc_output.run_id,
                            token_id=token_analysis.token_id,
                            token=token_analysis.token,
                            elapsed_ms=elapsed_ms,
                            active_features=active_features,
                            observation=event["observation"],
                            notes=notes,
                            tonality=tonality_payload,
                            sequence=token_count,
                        )
                        logger.debug("Token %d generated in %dms: %r", token_count, elapsed_ms, token_analysis.token)
                        _put_token_event(
                            queue,
                            event,
                            event_loop,
                            activation_event,
                        )

                await asyncio.to_thread(_generate)
                print(f"[pipeline] Generation complete: {token_count} tokens.", file=sys.stderr, flush=True)
                logger.info("Generation complete: %d tokens", token_count)
            except Exception as exc:
                logger.exception("Generation error (producer)")
                print(f"[pipeline] Generation error: {exc}", file=sys.stderr, flush=True)
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "message": str(exc)}), event_loop
                ).result()
            finally:
                await queue.put(None)  # always signal done, even on error

        async def _synthesizer():
            # Initial playback: drain the queue
            first_token_ready = False
            while True:
                queued = await queue.get()
                if queued is None:
                    queue.task_done()
                    break
                if isinstance(queued, tuple) and len(queued) == 3:
                    event, activation_event, delivered = queued
                else:
                    event, activation_event, delivered = queued, None, None
                try:
                    collected.append((event, activation_event))
                    if event.get("type") == "token":
                        if not first_token_ready:
                            first_token_ready = True
                            await _send_loading(
                                ws,
                                "generation",
                                "complete",
                                "First token ready · streaming live",
                            )
                        await _forward_token_event(
                            ws,
                            event,
                            params,
                            osc_output,
                            ossia_output,
                            activation_event=activation_event,
                        )
                    else:
                        await _send(ws, event)
                    if params.mode == "timed":
                        await asyncio.sleep(60.0 / params.bpm)
                finally:
                    if delivered is not None:
                        delivered.set()
                    queue.task_done()

            if not first_token_ready:
                await _send_loading(
                    ws,
                    "generation",
                    "complete",
                    "Generation finished without token events",
                )

            await _send(ws, {"type": "done"})
            await _call_osc(ws, osc_output.emit_done, params)

            # Post-generation: loop or idle until cancelled
            loop_count = 0
            was_looping = False
            while True:
                if params.loop:
                    was_looping = True
                    loop_count += 1
                    for event, activation_event in collected:
                        if not params.loop:
                            break
                        loop_event = {**event, "loop_count": loop_count}
                        if event.get("type") == "token":
                            loop_activation_event = (
                                {**activation_event, "loop_count": loop_count}
                                if activation_event is not None
                                else None
                            )
                            await _forward_token_event(
                                ws,
                                loop_event,
                                params,
                                osc_output,
                                ossia_output,
                                activation_event=loop_activation_event,
                            )
                        else:
                            await _send(ws, loop_event)
                        if params.mode == "timed":
                            await asyncio.sleep(60.0 / params.bpm)
                else:
                    if was_looping:
                        was_looping = False
                        await _send(ws, {"type": "silent"})
                        await _call_osc(ws, osc_output.emit_silent, params)
                    await asyncio.sleep(0.1)

        producer_task = asyncio.create_task(_producer())
        await _synthesizer()
        await producer_task  # re-raises any exception from generation

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Pipeline error")
        try:
            await _send(ws, {"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        await _call_osc(ws, osc_output.stop, params)
        await _call_ossia(ws, ossia_output.close)
        if _session.osc_output is osc_output:
            _session.osc_output = None
        if _session.ossia_output is ossia_output:
            _session.ossia_output = None
        try:
            await _send(ws, {"type": "stopped"})
        except Exception:
            pass


@router.websocket("/ws/stream")
async def ws_stream(ws: WebSocket) -> None:
    await ws.accept()
    await _send(ws, {"type": "ready", "params": dataclasses.asdict(_session.params)})

    try:
        while True:
            try:
                msg = await _receive_command(ws)
            except ValueError:
                await _send(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            action = msg.get("action")

            if action == "start":
                await _session.cancel()
                raw_params = msg.get("params", {})
                _session.params = PipelineParams()
                _session.params.update(**raw_params)
                _session.task = asyncio.create_task(
                    _run_pipeline(ws, _session.params)
                )

            elif action == "stop":
                await _stop_session(ws, _session)

            elif action == "update_params":
                raw_params = msg.get("params", {})
                _session.params.update(**raw_params)
                if "tonality_lenses" in raw_params:
                    await _prepare_live_tonality_lenses(
                        ws,
                        _session.params.tonality_lenses,
                    )
                if _session.osc_output is not None:
                    await _sync_live_osc_controls(
                        ws,
                        _session.params,
                        _session.osc_output,
                        set(raw_params),
                    )
                if (
                    _session.ossia_output is not None
                    and set(raw_params) & {"ossia_enabled", "ossia_osc_port", "ossia_query_port"}
                ):
                    await _sync_live_ossia(
                        ws,
                        _session.params,
                        _session.ossia_output,
                    )

            else:
                await _send(ws, {"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        await _session.cancel()
    except Exception:
        logger.exception("WebSocket error")
        await _session.cancel()
