"""Tests for config route payload helpers."""

from app.server.routers.config import get_emitter_mapping, get_tonalities


def test_get_tonalities_returns_default_interval_payload():
    payload = get_tonalities()

    assert payload["name"] == "default_artist_tonalities"
    assert payload["tonalities"]
    first = payload["tonalities"][0]
    assert set(first) == {"name", "description", "intervals"}
    assert first["intervals"]


def test_get_emitter_mapping_returns_editor_catalogue():
    payload = get_emitter_mapping()

    assert payload["signals"]
    assert payload["targets"]
    assert payload["default_mappings"]
