"""cluster_naming.py: Name SAE feature clusters and assign ColorBrewer colors."""
import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path("neuronpedia_cache")

# Pre-sorted by hue: red(0°) → orange → yellow → green → blue → purple(300°)
COLORBREWER_PAIRED_12 = [
    "#e31a1c",  # deep red       ~0°
    "#fb9a99",  # light pink     ~0°
    "#b15928",  # brown          ~22°
    "#ff7f00",  # orange         ~30°
    "#fdbf6f",  # light orange   ~34°
    "#ffff99",  # yellow         ~60°
    "#b2df8a",  # light green    ~96°
    "#33a02c",  # dark green     ~118°
    "#a6cee3",  # light blue     ~200°
    "#1f78b4",  # dark blue      ~210°
    "#6a3d9a",  # dark purple    ~275°
    "#cab2d6",  # light purple   ~288°
]

def _build_cluster_prompt(feature_descriptions: list[str]) -> str:
    """Build the few-shot prompt used in tests (kept for test compatibility)."""
    lines = "\n".join(f"- {desc}" for desc in feature_descriptions)
    return (
        "Here are a list of features descriptions from an LLM. They all belong to the same group. "
        "Please answer with 1-2 words that could describe to the best of your abilities what this cluster should be named.\n\n"
        "Features:\n"
        "- car\n"
        "- moving\n"
        "- plane\n"
        "- travelling\n"
        'your answer: "transportation"\n\n'
        "Features:\n"
        "- red\n"
        "- green\n"
        "- hue\n"
        "- color\n"
        "- pixel\n"
        'your answer: "colors"\n\n'
        f"Features:\n{lines}\n"
        'your answer: "'
    )


def name_clusters(
    cluster_map: dict,
    neuronpedia_explanations: dict,
) -> dict[int, str]:
    """Name each cluster by calling Claude Opus via the Anthropic API.

    Samples up to _MAX_FEATURES_FOR_NAMING descriptions per cluster to keep
    prompt size and cost low.  Returns {cluster_id: "name_string"}.
    """
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    # Group feature indices by cluster_id
    clusters: dict[int, list[int]] = {}
    for feat_idx, info in cluster_map.items():
        cid = info["cluster_id"]
        clusters.setdefault(cid, []).append(feat_idx)

    cluster_names: dict[int, str] = {}
    for cluster_id in sorted(clusters.keys()):
        feat_indices = clusters[cluster_id]
        descriptions = [
            neuronpedia_explanations[idx]
            for idx in feat_indices
            if idx in neuronpedia_explanations
        ]

        if not descriptions:
            cluster_names[cluster_id] = f"cluster_{cluster_id}"
            continue

        lines = "\n".join(f"- {d}" for d in descriptions)
        prompt = (
            "Below are feature descriptions from a sparse autoencoder cluster. "
            "The features were grouped by semantic similarity.\n\n"
            f"Features:\n{lines}\n\n"
            "Name this cluster in 1-2 words that best describes the common theme. "
            "Reply with ONLY the 1-2 word name, nothing else."
        )

        print(
            f"[cluster_naming] Naming cluster {cluster_id} ({len(descriptions)} features)...",
            file=sys.stderr,
            flush=True,
        )

        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            print(
                f"[cluster_naming] Cluster {cluster_id} raw output: {raw!r}",
                file=sys.stderr,
                flush=True,
            )
            words = re.findall(r"[a-zA-Z0-9]+", raw)
            name = " ".join(words[:2]).lower() if words else f"cluster_{cluster_id}"
        except Exception as exc:
            logger.warning("Claude naming failed for cluster %d: %s", cluster_id, exc)
            name = f"cluster_{cluster_id}"

        cluster_names[cluster_id] = name
        print(
            f"[cluster_naming] Cluster {cluster_id} → '{name}'",
            file=sys.stderr,
            flush=True,
        )

    return cluster_names


def assign_cluster_colors(
    cluster_names: dict[int, str],
    embed_model,
) -> tuple[dict[int, str], list[int]]:
    """Assign ColorBrewer colors to clusters sorted by 1D PCA of name embeddings.

    Returns:
        ({cluster_id: "#hexcolor"}, sorted_cluster_ids)
    """
    from sklearn.decomposition import PCA

    cluster_ids = sorted(cluster_names.keys())
    names = [cluster_names[cid] for cid in cluster_ids]

    try:
        embeddings = embed_model.encode(names)
        pca = PCA(n_components=1)
        scores = pca.fit_transform(embeddings).flatten()
        pc_scores = {cid: float(scores[i]) for i, cid in enumerate(cluster_ids)}
    except Exception as exc:
        logger.warning("PCA color assignment failed: %s — falling back to cluster_id order", exc)
        pc_scores = {cid: float(cid) for cid in cluster_ids}

    sorted_cluster_ids = sorted(cluster_ids, key=lambda cid: pc_scores[cid])

    colors: dict[int, str] = {}
    for i, cid in enumerate(sorted_cluster_ids):
        colors[cid] = COLORBREWER_PAIRED_12[i % len(COLORBREWER_PAIRED_12)]

    return colors, sorted_cluster_ids


def build_enriched_cluster_map(
    model_id: str,
    layer: int,
    sae_width: str,
    neuronpedia_scope,
    embed_model,
) -> dict:
    """Build (or load from cache) an enriched cluster map with names and colors.

    Returns a dict with keys:
        "cluster_map": {feature_index: {cluster_id, instrument, cluster_name, cluster_color}}
        "palette": [{cluster_id, name, color}] ordered by 1D PCA position
    """
    n_clusters = 12
    safe_model_id = model_id.replace("/", "_")
    cache_path = CACHE_DIR / f"{safe_model_id}_{layer}_{sae_width}_clusters_{n_clusters}_enriched.json"

    if cache_path.exists():
        print(
            f"[cluster_naming] Loading enriched cluster map from cache: {cache_path}",
            file=sys.stderr,
            flush=True,
        )
        try:
            with open(cache_path) as f:
                data = json.load(f)
            data["cluster_map"] = {int(k): v for k, v in data["cluster_map"].items()}
            return data
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Cache file corrupted (%s), rebuilding: %s", cache_path, exc)

    from app.server.pipeline.transform import build_cluster_map

    print(
        f"[cluster_naming] Building base cluster map (n_clusters={n_clusters})...",
        file=sys.stderr,
        flush=True,
    )
    base_map = build_cluster_map(model_id, layer, sae_width, n_clusters, "all-MiniLM-L6-v2")

    if not base_map:
        logger.warning("Base cluster map is empty — skipping enrichment")
        return {"cluster_map": {}, "palette": []}

    print("[cluster_naming] Naming clusters via Claude API...", file=sys.stderr, flush=True)
    cluster_names = name_clusters(base_map, neuronpedia_scope.explanations)

    print("[cluster_naming] Assigning cluster colors...", file=sys.stderr, flush=True)
    cluster_colors, sorted_cluster_ids = assign_cluster_colors(cluster_names, embed_model)

    # Merge into enriched map
    enriched_map: dict[int, dict] = {}
    for feat_idx, info in base_map.items():
        cid = info["cluster_id"]
        enriched_map[feat_idx] = {
            "cluster_id": cid,
            "instrument": info["instrument"],
            "cluster_name": cluster_names.get(cid, f"cluster_{cid}"),
            "cluster_color": cluster_colors.get(cid, "#888888"),
        }

    palette = [
        {
            "cluster_id": cid,
            "name": cluster_names.get(cid, f"cluster_{cid}"),
            "color": cluster_colors.get(cid, "#888888"),
        }
        for cid in sorted_cluster_ids
    ]

    result = {"cluster_map": enriched_map, "palette": palette}

    CACHE_DIR.mkdir(exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(
            {
                "cluster_map": {str(k): v for k, v in enriched_map.items()},
                "palette": palette,
            },
            f,
        )
    print(
        f"[cluster_naming] Enriched cluster map saved to {cache_path}",
        file=sys.stderr,
        flush=True,
    )

    return result
