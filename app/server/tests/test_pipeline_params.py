"""Tests for PipelineParams update coercion."""

from app.server.session import PipelineParams


def test_pipeline_params_update_coerces_tonality_controls():
    params = PipelineParams()

    params.update(
        tonality_enabled="false",
        prompt_influence="0.75",
        tonality_pitch_bias="0.25",
    )

    assert params.tonality_enabled is False
    assert params.prompt_influence == 0.75
    assert params.tonality_pitch_bias == 0.25


def test_pipeline_params_update_ignores_unknown_keys():
    params = PipelineParams()

    params.update(unknown="x")

    assert not hasattr(params, "unknown")
