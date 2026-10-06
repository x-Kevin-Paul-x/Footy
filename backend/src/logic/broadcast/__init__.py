"""Broadcast V2 presentation-only foundations.

Nothing in this package participates in canonical simulation identity.
"""

from .config import BroadcastRenderConfig, get_broadcast_render_config
from .schema import (
    BroadcastArtifactMetadata,
    BroadcastPlan,
    CameraCue,
    GraphicsCue,
    ReplayCue,
    StatsSnapshot,
)
from .stats import StatsSnapshotReducer

__all__ = [
    "BroadcastArtifactMetadata",
    "BroadcastPlan",
    "BroadcastRenderConfig",
    "CameraCue",
    "get_broadcast_render_config",
    "GraphicsCue",
    "ReplayCue",
    "StatsSnapshot",
    "StatsSnapshotReducer",
]
