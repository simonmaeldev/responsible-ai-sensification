"""config.py: Configuration and defaults API routes."""
import dataclasses

from fastapi import APIRouter

from app.server.pipeline.semantic_tonality import load_tonality_descriptions
from app.server.session import PipelineParams

router = APIRouter(prefix="/api/config")

_DEFAULTS = PipelineParams()

MODEL_CATALOGUE = {
    "google/gemma-3-1b-pt": {"layers": [22], "widths": ["65k"]},
    "google/gemma-3-4b-pt": {"layers": [22], "widths": ["65k"]},
}

SAE_REPO_MAP = {
    "google/gemma-3-1b-pt": "google/gemma-scope-2-1b-pt",
    "google/gemma-3-4b-pt": "google/gemma-scope-2-4b-pt",
}

STRATEGY_DESCRIPTIONS = {
    "identity": ("Identity", "Maps each active SAE feature directly to a frequency proportional to its index. Fast, no clustering."),
    "cluster": ("Cluster", "Groups features by semantic similarity (k-means on Neuronpedia embeddings). Each cluster becomes a distinct instrument colour."),
}

MODE_DESCRIPTIONS = {
    "timed": ("Timed", "Each token's notes play for a fixed duration derived from the BPM setting, then stop."),
    "sustain": ("Sustain", "Notes hold until the next token arrives, creating overlapping, drone-like textures."),
}


@router.get("/defaults")
def get_defaults() -> dict:
    return dataclasses.asdict(_DEFAULTS)


@router.get("/model-options")
def get_model_options() -> dict:
    return {
        "models": list(MODEL_CATALOGUE.keys()),
        "model_catalogue": MODEL_CATALOGUE,
        "strategies": [
            {"value": k, "label": v[0], "description": v[1]}
            for k, v in STRATEGY_DESCRIPTIONS.items()
        ],
        "modes": [
            {"value": k, "label": v[0], "description": v[1]}
            for k, v in MODE_DESCRIPTIONS.items()
        ],
    }


@router.get("/tonalities")
def get_tonalities() -> dict:
    tonality_set = load_tonality_descriptions()
    return {
        "name": tonality_set.name,
        "description": tonality_set.description,
        "tonalities": [
            dataclasses.asdict(tonality)
            for tonality in tonality_set.tonalities
        ],
    }
