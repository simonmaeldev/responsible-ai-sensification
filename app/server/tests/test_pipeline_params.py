"""Tests for PipelineParams update coercion."""

from app.server.session import PipelineParams
from app.server.pipeline.emitter_signals import default_emitter_signal_keys


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


def test_pipeline_params_accepts_live_observation_layer():
    params = PipelineParams()

    params.update(observation_layer="7")

    assert params.observation_layer == 7


def test_pipeline_params_update_accepts_live_tonality_lenses():
    params = PipelineParams()
    lenses = [
        {
            "name": "live lens",
            "description": "bright pressure",
            "intervals": [0, 2, 7],
        }
    ]

    params.update(tonality_lenses=lenses)

    assert params.tonality_lenses == lenses


def test_pipeline_params_update_coerces_and_bounds_osc_settings():
    params = PipelineParams()

    params.update(
        osc_enabled="true",
        osc_host="  ableton-host.local  ",
        osc_port="70000",
        osc_max_notes_per_token="0",
    )

    assert params.osc_enabled is True
    assert params.osc_host == "ableton-host.local"
    assert params.osc_port == 65_535
    assert params.osc_max_notes_per_token == 1

    params.update(osc_port="invalid", osc_max_notes_per_token=999)

    assert params.osc_port == 65_535
    assert params.osc_max_notes_per_token == 128


def test_pipeline_params_coerces_live_emitter_mappings():
    params = PipelineParams()

    params.update(
        emitter_mappings=[
            {
                "id": "live",
                "source": "activation.max",
                "target": "audio.pitch_semitones",
                "output_min": -999,
                "output_max": 999,
            }
        ]
    )

    assert params.emitter_mappings[0]["id"] == "live"
    assert params.emitter_mappings[0]["output_min"] == -24
    assert params.emitter_mappings[0]["output_max"] == 24


def test_pipeline_params_coerces_live_emitter_signal_selection():
    params = PipelineParams()

    assert params.emitter_signal_keys == default_emitter_signal_keys()
    params.update(
        emitter_signal_keys=[
            "activation.max",
            "model.residual.vector",
            "not.registered",
            "activation.max",
        ]
    )

    assert params.emitter_signal_keys == ["activation.max", "model.residual.vector"]
