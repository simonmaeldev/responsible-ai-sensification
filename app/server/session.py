"""session.py: Pipeline parameter dataclass and session state."""
import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.server.pipeline.emitter_mapping import (
    coerce_emitter_mappings,
    default_emitter_mappings,
)
from app.server.pipeline.emitter_signals import (
    coerce_emitter_signal_keys,
    default_emitter_signal_keys,
)
from app.server.pipeline.model_probes import coerce_probe_rack, default_probe_rack


@dataclass
class PipelineParams:
    OSC_MIN_PORT = 1
    OSC_MAX_PORT = 65_535
    OSC_MIN_NOTES = 1
    OSC_MAX_NOTES = 128

    prompt: str = "Hello world"
    model: str = "google/gemma-3-1b-pt"
    layer: int = 22
    observation_layer: int = 22
    width: str = "65k"
    l0: str = "medium"
    max_tokens: int = 200
    strategy: str = "identity"   # "identity" | "cluster"
    clusters: int = 8
    loop: bool = False
    mode: str = "timed"          # "timed" | "sustain"
    bpm: int = 120
    tonality_enabled: bool = True
    prompt_influence: float = 0.2
    tonality_pitch_bias: float = 0.55
    tonality_lenses: list[dict] = field(default_factory=list)
    probe_rack: list[dict] = field(default_factory=default_probe_rack)
    emitter_signal_keys: list[str] = field(default_factory=default_emitter_signal_keys)
    emitter_mappings: list[dict] = field(default_factory=default_emitter_mappings)
    osc_enabled: bool = False
    osc_host: str = ""
    osc_port: int = 9000
    osc_max_notes_per_token: int = 32
    ossia_enabled: bool = False
    ossia_osc_port: int = 9010
    ossia_query_port: int = 5678

    def update(self, **kwargs) -> None:
        """Merge a dict of partial params into this instance."""
        for key, value in kwargs.items():
            if not hasattr(self, key) or value is None:
                continue
            current = getattr(self, key)
            if type(current) is bool:
                if isinstance(value, str):
                    value = value.lower() in {"1", "true", "yes", "on"}
                else:
                    value = bool(value)
            elif type(current) is int:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    continue
                if key in {"osc_port", "ossia_osc_port", "ossia_query_port"}:
                    value = max(self.OSC_MIN_PORT, min(self.OSC_MAX_PORT, value))
                elif key == "osc_max_notes_per_token":
                    value = max(self.OSC_MIN_NOTES, min(self.OSC_MAX_NOTES, value))
            elif type(current) is float:
                value = float(value)
            elif type(current) is str:
                value = str(value)
                if key == "osc_host":
                    value = value.strip()
            elif key == "emitter_mappings":
                value = coerce_emitter_mappings(value)
            elif key == "emitter_signal_keys":
                value = coerce_emitter_signal_keys(value)
            elif key == "probe_rack":
                value = coerce_probe_rack(value, sae_layer=self.layer)
            setattr(self, key, value)
        if "layer" in kwargs or "probe_rack" in kwargs:
            self.probe_rack = coerce_probe_rack(self.probe_rack, sae_layer=self.layer)


@dataclass
class PipelineSession:
    params: PipelineParams = field(default_factory=PipelineParams)
    task: asyncio.Task | None = None
    osc_output: Any | None = None
    ossia_output: Any | None = None

    def is_running(self) -> bool:
        return self.task is not None and not self.task.done()

    async def cancel(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        self.osc_output = None
        self.ossia_output = None
