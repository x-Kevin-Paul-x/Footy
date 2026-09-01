"""
Centralized Replay Schema Definitions & Standards for Google Research Football (GRF).
Provides single-source-of-truth constants for observation fields, archive schema versions,
and format identifiers across simulation, archive storage, and replay workers.
"""

from typing import Tuple, FrozenSet

import os

SIM_STEP_SECONDS = 0.1
SIM_FPS = 10.0
GRF_STATE_SCHEMA_VERSION = "grf_chunked_zlib_v2"


class PerformanceConfig:
    """
    Centralized toggle and settings for zero-cost production profiling vs granular benchmarks.
    When PROFILE_ENABLED is False (or env PROFILE_ENABLED=0), timing measurements incur zero/near-zero overhead.
    """
    enabled: bool = os.getenv("PROFILE_ENABLED", "1").lower() in ("1", "true", "yes")
    deep_profiling: bool = os.getenv("DEEP_PROFILING", "0").lower() in ("1", "true", "yes")
REPLAY_FORMAT_VERSION = "FOOTY_GRF_STATE_V2"
TRAJECTORY_SCHEMA_VERSION = "FOOTY_TRAJECTORY_V2"
TRAJECTORY_SCHEMA_VERSION_V1 = "FOOTY_TRAJECTORY_V1"

# Canonical ordered tuple of 16 observation fields required in every GRF observation for replay integrity.
GRF_REQUIRED_OBS_FIELDS: Tuple[str, ...] = (
    "left_team",
    "right_team",
    "left_team_direction",
    "right_team_direction",
    "left_team_tired_factor",
    "right_team_tired_factor",
    "left_team_yellow_card",
    "right_team_yellow_card",
    "left_team_active",
    "right_team_active",
    "ball",
    "ball_direction",
    "score",
    "ball_owned_team",
    "ball_owned_player",
    "game_mode",
)

# Immutable set for fast schema validation lookups
GRF_REQUIRED_OBS_FIELD_SET: FrozenSet[str] = frozenset(GRF_REQUIRED_OBS_FIELDS)
