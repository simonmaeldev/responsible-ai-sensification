"""session.py: Pipeline parameter dataclass and session state."""
import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.server.pipeline.emitter_mapping import (
    coerce_emitter_mappings,
    default_emitter_mappings,
)


@dataclass
class PipelineParams:
    OSC_MIN_PORT = 1
    OSC_MAX_PORT = 65_535
    OSC_MIN_NOTES = 1
    OSC_MAX_NOTES = 128

    prompt: str = "Hello world"
    model: str = "google/gemma-3-1b-pt"
    layer: int = 22
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
    emitter_mappings: list[dict] = field(default_factory=default_emitter_mappings)
    osc_enabled: bool = False
    osc_host: str = ""
    osc_port: int = 9000
    osc_max_notes_per_token: int = 32

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
                if key == "osc_port":
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
            setattr(self, key, value)


@dataclass
class PipelineSession:
    params: PipelineParams = field(default_factory=PipelineParams)
    task: asyncio.Task | None = None
    osc_output: Any | None = None

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
