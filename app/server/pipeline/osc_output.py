"""Failure-isolated OSC v1 output for live post-tonality token events."""

from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)

OSC_ROOT = "/rai/v1"

CONTROL_ADDRESSES = {
    "bpm": f"{OSC_ROOT}/control/bpm",
    "mode": f"{OSC_ROOT}/control/mode",
    "loop": f"{OSC_ROOT}/control/loop",
    "tonality_enabled": f"{OSC_ROOT}/control/tonality_enabled",
    "prompt_influence": f"{OSC_ROOT}/control/prompt_influence",
    "tonality_pitch_bias": f"{OSC_ROOT}/control/tonality_pitch_bias",
}


@dataclass(frozen=True)
class OscResult:
    """Outcome of one non-throwing OSC operation."""

    state: str
    message: str
    sent: int = 0
    error: str | None = None
    sequence: int | None = None


class OscRunOutput:
    """Send one run's versioned OSC messages to a live-configurable UDP target.

    The object deliberately reads the mutable pipeline parameters for every
    operation. Destination and note-cap edits therefore take effect on the next
    message without rebuilding the generation pipeline. All transport errors are
    converted to :class:`OscResult` values so they cannot stop model generation.
    """

    def __init__(
        self,
        run_id: str,
        *,
        client_factory: Callable[[str, int], Any] = SimpleUDPClient,
    ) -> None:
        self.run_id = str(run_id)
        self._client_factory = client_factory
        self._client: Any | None = None
        self._destination: tuple[str, int] | None = None
        self._started = False
        self._begun = False
        self._sequence = 0
        self._last_controls: dict[str, Any] = {}
        self._lock = threading.RLock()

    @property
    def sequence(self) -> int:
        return self._sequence

    def describe(self, params: Any) -> OscResult:
        """Describe the configured UDP target without claiming connectivity."""
        with self._lock:
            return self._configuration_status(params)

    def begin(self, params: Any) -> OscResult:
        """Begin the run and emit start plus the initial control snapshot."""
        with self._lock:
            self._begun = True
            prepared = self._prepare_destination(params)
            if prepared is not None:
                return prepared
            return self._ensure_started(params)

    def sync_controls(self, params: Any, changed_fields: Iterable[str]) -> OscResult:
        """Apply a live destination change and emit changed receiver controls."""
        with self._lock:
            if not self._begun:
                return self._configuration_status(params)

            prepared = self._prepare_destination(params)
            if prepared is not None:
                return prepared
            started = self._ensure_started(params)
            if started.state != "ready":
                return started

            sent = started.sent
            changed = set(changed_fields)
            for field in CONTROL_ADDRESSES:
                if field not in changed:
                    continue
                value = self._control_value(field, params)
                if self._last_controls.get(field) == value:
                    continue
                error = self._send(CONTROL_ADDRESSES[field], value)
                if error:
                    return self._error_result(error, sent=sent)
                self._last_controls[field] = value
                sent += 1
            return self._ready_result(sent=sent)

    def emit_token(self, params: Any, event: dict[str, Any]) -> OscResult:
        """Emit one canonical post-tonality token event and its bounded notes."""
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
            if not self._begun:
                self._begun = True

            prepared = self._prepare_destination(params)
            if prepared is not None:
                return OscResult(**{**prepared.__dict__, "sequence": sequence})
            started = self._ensure_started(params)
            if started.state != "ready":
                return OscResult(**{**started.__dict__, "sequence": sequence})

            sent = started.sent
            token_args = [
                self.run_id,
                sequence,
                int(event.get("token_id") or 0),
                str(event.get("token") or ""),
                int(event.get("elapsed_ms") or 0),
            ]
            error = self._send(f"{OSC_ROOT}/token", token_args)
            if error:
                return self._error_result(error, sent=sent, sequence=sequence)
            sent += 1

            notes = self._bounded_notes(event.get("notes") or [], params)
            for note_index, note in enumerate(notes):
                note_args = [
                    self.run_id,
                    sequence,
                    note_index,
                    int(note.get("feature_index") if note.get("feature_index") is not None else -1),
                    float(note.get("freq") or 440.0),
                    float(note.get("amplitude") or 0.0),
                    int(note.get("cluster") if note.get("cluster") is not None else -1),
                    str(note.get("instrument") or "default"),
                ]
                error = self._send(f"{OSC_ROOT}/note", note_args)
                if error:
                    return self._error_result(error, sent=sent, sequence=sequence)
                sent += 1

            tonality = event.get("tonality") or {}
            matches = tonality.get("matches") or []
            if matches:
                primary = matches[0]
                tonality_args = [
                    self.run_id,
                    sequence,
                    str(primary.get("name") or ""),
                    float(primary.get("score") or 0.0),
                    float(tonality.get("pitch_bias") or 0.0),
                ]
                error = self._send(f"{OSC_ROOT}/tonality", tonality_args)
                if error:
                    return self._error_result(error, sent=sent, sequence=sequence)
                sent += 1

            error = self._send(
                f"{OSC_ROOT}/token/end",
                [self.run_id, sequence, len(notes)],
            )
            if error:
                return self._error_result(error, sent=sent, sequence=sequence)
            return self._ready_result(sent=sent + 1, sequence=sequence)

    def emit_done(self, params: Any) -> OscResult:
        return self._emit_lifecycle(params, "done")

    def emit_silent(self, params: Any) -> OscResult:
        return self._emit_lifecycle(params, "silent")

    def stop(self, params: Any) -> OscResult:
        """Emit the final stop when possible and retire this run output."""
        with self._lock:
            if not self._begun:
                return self._configuration_status(params)

            prepared = self._prepare_destination(params)
            if prepared is not None:
                self._begun = False
                return prepared
            started = self._ensure_started(params)
            if started.state != "ready":
                self._begun = False
                return started

            error = self._send(f"{OSC_ROOT}/run/stop", self.run_id)
            self._begun = False
            self._started = False
            if error:
                result = self._error_result(error, sent=started.sent)
            else:
                result = self._ready_result(sent=started.sent + 1)
            self._clear_destination()
            return result

    def _emit_lifecycle(self, params: Any, event_name: str) -> OscResult:
        with self._lock:
            if not self._begun:
                self._begun = True
            prepared = self._prepare_destination(params)
            if prepared is not None:
                return prepared
            started = self._ensure_started(params)
            if started.state != "ready":
                return started
            error = self._send(f"{OSC_ROOT}/run/{event_name}", self.run_id)
            if error:
                return self._error_result(error, sent=started.sent)
            return self._ready_result(sent=started.sent + 1)

    def _prepare_destination(self, params: Any) -> OscResult | None:
        enabled = bool(getattr(params, "osc_enabled", False))
        host = str(getattr(params, "osc_host", "") or "").strip()
        if not enabled or not host:
            self._clear_destination()
            return self._configuration_status(params)

        port = int(getattr(params, "osc_port", 9000))
        desired = (host, port)
        if desired == self._destination and self._client is not None:
            return None

        previous_destination = self._destination
        transition_error = None
        if self._client is not None and self._started:
            transition_error = self._send(f"{OSC_ROOT}/run/stop", self.run_id)

        self._clear_destination()
        try:
            self._client = self._client_factory(host, port)
            self._destination = desired
        except Exception as exc:  # defensive: constructor behavior varies by client
            self._clear_destination()
            return self._error_result(str(exc), destination=desired)
        if transition_error:
            return self._error_result(
                transition_error,
                destination=previous_destination,
            )
        return None

    def _ensure_started(self, params: Any) -> OscResult:
        if self._client is None or self._destination is None:
            return self._configuration_status(params)
        if self._started:
            return self._ready_result()

        error = self._send(
            f"{OSC_ROOT}/run/start",
            [self.run_id, int(getattr(params, "bpm", 120)), str(getattr(params, "mode", "timed"))],
        )
        if error:
            return self._error_result(error)
        self._started = True
        sent = 1

        for field in CONTROL_ADDRESSES:
            value = self._control_value(field, params)
            error = self._send(CONTROL_ADDRESSES[field], value)
            if error:
                return self._error_result(error, sent=sent)
            self._last_controls[field] = value
            sent += 1
        return self._ready_result(sent=sent)

    def _bounded_notes(self, notes: Iterable[dict[str, Any]], params: Any) -> list[dict[str, Any]]:
        cap = int(getattr(params, "osc_max_notes_per_token", 32))
        cap = max(1, min(128, cap))

        def activation(note: dict[str, Any]) -> float:
            value = float(note.get("amplitude") or 0.0)
            return value if math.isfinite(value) else float("-inf")

        return sorted(list(notes), key=activation, reverse=True)[:cap]

    @staticmethod
    def _control_value(field: str, params: Any) -> Any:
        value = getattr(params, field)
        if field in {"loop", "tonality_enabled"}:
            return int(bool(value))
        if field in {"prompt_influence", "tonality_pitch_bias"}:
            return float(value)
        if field == "bpm":
            return int(value)
        return str(value)

    def _send(self, address: str, value: Any) -> str | None:
        try:
            self._client.send_message(address, value)
            return None
        except Exception as exc:  # OSC must never interrupt generation
            logger.warning("OSC send failed for %s: %s", address, exc)
            return str(exc)

    def _clear_destination(self) -> None:
        client = self._client
        self._client = None
        self._destination = None
        self._started = False
        self._last_controls = {}
        close = getattr(client, "close", None)
        if close is not None:
            try:
                close()
            except Exception:
                logger.debug("Could not close OSC UDP client", exc_info=True)

    def _configuration_status(self, params: Any) -> OscResult:
        if not bool(getattr(params, "osc_enabled", False)):
            return OscResult("disabled", "OSC disabled")
        host = str(getattr(params, "osc_host", "") or "").strip()
        if not host:
            return OscResult("unconfigured", "OSC enabled; enter destination host/IP")
        port = int(getattr(params, "osc_port", 9000))
        return OscResult(
            "ready",
            f"OSC targeting {host}:{port} via UDP; delivery unconfirmed",
        )

    def _ready_result(self, *, sent: int = 0, sequence: int | None = None) -> OscResult:
        destination = self._destination
        if destination is None:
            return OscResult("unconfigured", "OSC destination is not configured", sequence=sequence)
        host, port = destination
        return OscResult(
            "ready",
            f"OSC targeting {host}:{port} via UDP; delivery unconfirmed",
            sent=sent,
            sequence=sequence,
        )

    def _error_result(
        self,
        error: str,
        *,
        sent: int = 0,
        sequence: int | None = None,
        destination: tuple[str, int] | None = None,
    ) -> OscResult:
        target = destination or self._destination
        suffix = f" for {target[0]}:{target[1]}" if target else ""
        return OscResult(
            "error",
            f"OSC send failed{suffix}: {error}",
            sent=sent,
            error=error,
            sequence=sequence,
        )
