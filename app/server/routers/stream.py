"""stream.py: WebSocket endpoint for live pipeline streaming."""
import asyncio
import dataclasses
import json
import logging
import sys
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.server.pipeline.osc_output import OscResult, OscRunOutput
from app.server.session import PipelineParams, PipelineSession  # noqa: F401 (PipelineSession used for _session)

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level model cache: (model_id, layer, width) -> {"model": ..., "tokenizer": ..., "sae": ..., "neuronpedia": ...}
_model_cache: dict[tuple, dict] = {}

# Cluster map cache: (model_id, layer, width, clusters) -> cluster_map dict
_cluster_cache: dict[tuple, dict] = {}

# Enriched cluster map cache: (model_id, layer, width) -> {cluster_map, palette}
_enriched_cluster_cache: dict[tuple, dict] = {}

# Semantic tonality runtime cache: embed_model -> {cache, embedder}
_tonality_runtime_cache: dict[str, dict] = {}

# One shared session (single-user for now)
_session = PipelineSession()


async def _send(ws: WebSocket, msg: dict) -> None:
    await ws.send_text(json.dumps(msg))


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
) -> OscResult:
    """Preserve the browser event, then mirror its final notes to OSC."""
    await _send(ws, event)
    return await _call_osc(ws, osc_output.emit_token, params, event)


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


def _get_tonality_cache_runtime(raw_lenses: list[dict] | None = None) -> dict:
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


async def _run_pipeline(ws: WebSocket, params: PipelineParams) -> None:
    """Background task: load model (cached), run inspect_live, stream token events."""
    osc_output = OscRunOutput(uuid.uuid4().hex)
    _session.osc_output = osc_output
    try:
        cache_key = (params.model, params.layer, params.width)

        if cache_key in _model_cache:
            print("[pipeline] Using cached model/SAE/neuronpedia.", file=sys.stderr, flush=True)
            await _send(ws, {"type": "loading", "stage": "cached"})
            cached = _model_cache[cache_key]
            model = cached["model"]
            tokenizer = cached["tokenizer"]
            sae = cached["sae"]
            neuronpedia = cached["neuronpedia"]
        else:
            # Load model
            print(f"[pipeline] Loading language model: {params.model}", file=sys.stderr, flush=True)
            await _send(ws, {"type": "loading", "stage": "Loading language model..."})

            def _load_model():
                from transformers import AutoModelForCausalLM, AutoTokenizer
                _model = AutoModelForCausalLM.from_pretrained(params.model, device_map="auto")
                _tokenizer = AutoTokenizer.from_pretrained(params.model)
                return _model, _tokenizer

            model, tokenizer = await asyncio.to_thread(_load_model)
            print("[pipeline] Language model loaded.", file=sys.stderr, flush=True)

            # Load SAE
            print(f"[pipeline] Loading SAE (layer={params.layer}, width={params.width}, l0={params.l0})", file=sys.stderr, flush=True)
            await _send(ws, {"type": "loading", "stage": f"Loading SAE (layer={params.layer}, width={params.width})..."})

            def _load_sae():
                from app.server.pipeline.extract import load_sae
                from app.server.routers.config import SAE_REPO_MAP
                sae_repo_id = SAE_REPO_MAP.get(params.model, "google/gemma-scope-2-1b-pt")
                return load_sae(layer=params.layer, width=params.width, l0=params.l0,
                                sae_repo_id=sae_repo_id)

            sae = await asyncio.to_thread(_load_sae)
            print("[pipeline] SAE loaded.", file=sys.stderr, flush=True)

            # Load Neuronpedia
            print("[pipeline] Loading Neuronpedia explanations...", file=sys.stderr, flush=True)
            await _send(ws, {"type": "loading", "stage": "Downloading Neuronpedia explanations..."})

            def _load_neuronpedia():
                from app.server.pipeline.extract import download_neuronpedia_explanations
                # Neuronpedia uses "gemma-3-1b" style key, strip the HF org prefix
                np_model_id = params.model.split("/")[-1].replace("-pt", "")
                return download_neuronpedia_explanations(np_model_id, params.layer, params.width)

            neuronpedia = await asyncio.to_thread(_load_neuronpedia)
            print(f"[pipeline] Neuronpedia loaded: {len(neuronpedia.explanations)} features.", file=sys.stderr, flush=True)

            _model_cache[cache_key] = {
                "model": model,
                "tokenizer": tokenizer,
                "sae": sae,
                "neuronpedia": neuronpedia,
            }

        # Build enriched cluster map (names + colors) — cached after first run
        enriched_key = (params.model, params.layer, params.width)
        if enriched_key not in _enriched_cluster_cache:
            await _send(ws, {"type": "loading", "stage": "Naming clusters..."})

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

        enriched_map = enriched_data.get("cluster_map", {})
        palette = enriched_data.get("palette", [])

        await _send(ws, {"type": "cluster_palette", "palette": palette})

        tonality_runtime: dict | None = None
        prompt_embedding = None
        if params.tonality_enabled:
            await _send(ws, {"type": "loading", "stage": "Loading semantic tonalities..."})
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

        await _send(ws, {"type": "loading", "stage": "Running generation..."})

        from app.server.pipeline.extract import inspect_live
        from app.server.pipeline.semantic_tonality import (
            TonalityMemory,
            apply_tonality_pitch_bias,
            build_tonality_evidence,
            match_active_features_and_prompt_to_tonalities,
            tonality_result_to_payload,
        )
        from app.server.pipeline.transform import apply_identity, apply_cluster, build_cluster_map

        cluster_map: dict = {}
        if params.strategy == "cluster":
            cluster_key = (params.model, params.layer, params.width, params.clusters)
            if cluster_key in _cluster_cache:
                cluster_map = _cluster_cache[cluster_key]
                print(f"[pipeline] Cluster map from in-memory cache: {len(cluster_map)} entries.", file=sys.stderr, flush=True)
                logger.info("Cluster map loaded from in-memory cache: %d entries", len(cluster_map))
            else:
                print(f"[pipeline] Building cluster map (clusters={params.clusters})...", file=sys.stderr, flush=True)
                await _send(ws, {"type": "loading", "stage": "Building cluster map..."})

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

        print(f"[pipeline] Starting pipeline: prompt={params.prompt!r} strategy={params.strategy} clusters={params.clusters}", file=sys.stderr, flush=True)
        logger.info("Starting pipeline: prompt=%r strategy=%s clusters=%s", params.prompt, params.strategy, params.clusters)
        await _call_osc(ws, osc_output.begin, params, report_status=True)

        # Producer + synthesizer: run generation concurrently with timed playback
        queue: asyncio.Queue = asyncio.Queue()
        collected: list[dict] = []
        event_loop = asyncio.get_running_loop()
        tonality_memory = TonalityMemory()

        async def _producer():
            try:
                token_count = 0

                def _generate():
                    nonlocal prompt_embedding, token_count
                    print(f"[pipeline] Generation starting (max_tokens={params.max_tokens})...", file=sys.stderr, flush=True)
                    logger.info("Starting generation: max_tokens=%d", params.max_tokens)
                    for token_analysis, elapsed_ms in inspect_live(
                        params.prompt, model, tokenizer, sae,
                        params.layer, neuronpedia,
                        max_new_tokens=params.max_tokens,
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
                        }
                        if tonality_payload is not None:
                            event["tonality"] = tonality_payload
                        logger.debug("Token %d generated in %dms: %r", token_count, elapsed_ms, token_analysis.token)
                        asyncio.run_coroutine_threadsafe(queue.put(event), event_loop).result()

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
            while True:
                event = await queue.get()
                if event is None:
                    break
                collected.append(event)
                if event.get("type") == "token":
                    await _forward_token_event(ws, event, params, osc_output)
                else:
                    await _send(ws, event)
                if params.mode == "timed":
                    await asyncio.sleep(60.0 / params.bpm)

            await _send(ws, {"type": "done"})
            await _call_osc(ws, osc_output.emit_done, params)

            # Post-generation: loop or idle until cancelled
            loop_count = 0
            was_looping = False
            while True:
                if params.loop:
                    was_looping = True
                    loop_count += 1
                    for event in collected:
                        if not params.loop:
                            break
                        loop_event = {**event, "loop_count": loop_count}
                        if event.get("type") == "token":
                            await _forward_token_event(ws, loop_event, params, osc_output)
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
        if _session.osc_output is osc_output:
            _session.osc_output = None
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
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
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
                await _session.cancel()
                await _send(ws, {"type": "stopped"})

            elif action == "update_params":
                raw_params = msg.get("params", {})
                _session.params.update(**raw_params)
                if _session.osc_output is not None:
                    await _sync_live_osc_controls(
                        ws,
                        _session.params,
                        _session.osc_output,
                        set(raw_params),
                    )

            else:
                await _send(ws, {"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        await _session.cancel()
    except Exception:
        logger.exception("WebSocket error")
        await _session.cancel()
