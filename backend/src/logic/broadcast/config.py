"""Presentation-only Broadcast V2 configuration.

This module intentionally has no dependency on SimulationSpec or MatchManifest.
"""

from dataclasses import asdict, dataclass
import hashlib
import json

from config import (
    ALTERNATE_REPLAYS_ENABLED,
    BROADCAST_V2_ENABLED,
    CAMERA_DIRECTOR_ENABLED,
    CELEBRATIONS_ENABLED,
    PRESENTATION_FPS,
)


@dataclass(frozen=True)
class BroadcastRenderConfig:
    """Configuration for derived presentation artifacts only."""

    broadcast_v2_enabled: bool = BROADCAST_V2_ENABLED
    camera_director_enabled: bool = CAMERA_DIRECTOR_ENABLED
    presentation_fps: int = PRESENTATION_FPS
    alternate_replays_enabled: bool = ALTERNATE_REPLAYS_ENABLED
    celebrations_enabled: bool = CELEBRATIONS_ENABLED

    def __post_init__(self) -> None:
        if self.presentation_fps <= 0:
            raise ValueError("presentation_fps must be positive")

    def to_dict(self) -> dict:
        return asdict(self)

    def sha256(self) -> str:
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def get_broadcast_render_config() -> BroadcastRenderConfig:
    """Return the immutable process configuration for derived broadcasts."""
    return BroadcastRenderConfig()
