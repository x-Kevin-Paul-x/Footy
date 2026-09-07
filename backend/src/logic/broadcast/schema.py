"""Immutable, deterministic data contracts for Broadcast V2.

These are schemas only.  They do not make camera, graphic, replay, or encoding
decisions and therefore cannot alter canonical simulation state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Tuple


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def freeze_event(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return an immutable copy of a canonical event without mutating it."""
    return _freeze(dict(event))


@dataclass(frozen=True)
class StatsSnapshot:
    source_step: int
    score: Tuple[int, int]
    possession: Tuple[float, float]
    shots: Tuple[int, int]
    shots_on_target: Tuple[int, int]
    xg: Tuple[float, float]
    passes_attempted: Tuple[int, int]
    passes_completed: Tuple[int, int]
    events: Tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", tuple(int(value) for value in self.score))
        object.__setattr__(self, "possession", tuple(float(value) for value in self.possession))
        object.__setattr__(self, "shots", tuple(int(value) for value in self.shots))
        object.__setattr__(self, "shots_on_target", tuple(int(value) for value in self.shots_on_target))
        object.__setattr__(self, "xg", tuple(float(value) for value in self.xg))
        object.__setattr__(self, "passes_attempted", tuple(int(value) for value in self.passes_attempted))
        object.__setattr__(self, "passes_completed", tuple(int(value) for value in self.passes_completed))
        object.__setattr__(self, "events", tuple(freeze_event(event) for event in self.events))

    def to_dict(self) -> dict:
        return {
            "source_step": self.source_step,
            "score": list(self.score),
            "possession": list(self.possession),
            "shots": list(self.shots),
            "shots_on_target": list(self.shots_on_target),
            "xg": list(self.xg),
            "passes_attempted": list(self.passes_attempted),
            "passes_completed": list(self.passes_completed),
            "events": [_thaw(event) for event in self.events],
        }


@dataclass(frozen=True)
class CameraCue:
    source_step: int
    mode: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {"source_step": self.source_step, "mode": self.mode, "reason": self.reason}


@dataclass(frozen=True)
class GraphicsCue:
    source_step: int
    graphic: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze(dict(self.payload)))

    def to_dict(self) -> dict:
        return {"source_step": self.source_step, "graphic": self.graphic, "payload": _thaw(self.payload)}


@dataclass(frozen=True)
class ReplayCue:
    source_step: int
    start_step: int
    end_step: int
    speed: float = 1.0
    label: str = ""

    def __post_init__(self) -> None:
        if self.start_step > self.end_step:
            raise ValueError("replay start_step must not be after end_step")
        if self.speed <= 0:
            raise ValueError("replay speed must be positive")

    def to_dict(self) -> dict:
        return {
            "source_step": self.source_step,
            "start_step": self.start_step,
            "end_step": self.end_step,
            "speed": self.speed,
            "label": self.label,
        }


@dataclass(frozen=True)
class BroadcastPlan:
    match_id: str
    source_state_rate: float
    presentation_fps: int
    camera_cues: Tuple[CameraCue, ...] = field(default_factory=tuple)
    graphics_cues: Tuple[GraphicsCue, ...] = field(default_factory=tuple)
    replay_cues: Tuple[ReplayCue, ...] = field(default_factory=tuple)
    version: str = "2.0.0-phase1"

    def __post_init__(self) -> None:
        if self.source_state_rate <= 0 or self.presentation_fps <= 0:
            raise ValueError("source_state_rate and presentation_fps must be positive")
        object.__setattr__(self, "camera_cues", tuple(self.camera_cues))
        object.__setattr__(self, "graphics_cues", tuple(self.graphics_cues))
        object.__setattr__(self, "replay_cues", tuple(self.replay_cues))

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "match_id": self.match_id,
            "source_state_rate": self.source_state_rate,
            "presentation_fps": self.presentation_fps,
            "camera_cues": [cue.to_dict() for cue in self.camera_cues],
            "graphics_cues": [cue.to_dict() for cue in self.graphics_cues],
            "replay_cues": [cue.to_dict() for cue in self.replay_cues],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BroadcastArtifactMetadata:
    renderer_version: str
    timeline_version: str
    camera_profile: str
    presentation_fps: int
    resolution: Tuple[int, int]
    encoder: str
    source_archive_sha256: str
    broadcast_config_sha256: str

    def __post_init__(self) -> None:
        if self.presentation_fps <= 0:
            raise ValueError("presentation_fps must be positive")
        if len(self.resolution) != 2 or any(int(value) <= 0 for value in self.resolution):
            raise ValueError("resolution must be a positive (width, height) pair")
        object.__setattr__(self, "resolution", tuple(int(value) for value in self.resolution))

    def to_dict(self) -> dict:
        return {
            "renderer_version": self.renderer_version,
            "timeline_version": self.timeline_version,
            "camera_profile": self.camera_profile,
            "presentation_fps": self.presentation_fps,
            "resolution": list(self.resolution),
            "encoder": self.encoder,
            "source_archive_sha256": self.source_archive_sha256,
            "broadcast_config_sha256": self.broadcast_config_sha256,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
