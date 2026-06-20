"""Tests for config route payload helpers."""

from app.server.routers.config import get_tonalities


def test_get_tonalities_returns_default_interval_payload():
    payload = get_tonalities()

    assert payload["name"] == "default_artist_tonalities"
    assert payload["tonalities"]
    first = payload["tonalities"][0]
    assert set(first) == {"name", "description", "intervals"}
    assert first["intervals"]
