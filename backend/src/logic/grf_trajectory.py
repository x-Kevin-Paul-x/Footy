"""
MatchTrajectory Module for Google Research Football (GRF) & TiKick.
Provides compact binary trajectory serialization (.npz), manifest metadata,
and deterministic trajectory fingerprinting for 100% replay fidelity.
"""

import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from logic.replay_schema import TRAJECTORY_SCHEMA_VERSION, TRAJECTORY_SCHEMA_VERSION_V1
from logic.grf_state_archive import ReplayIntegrityError


@dataclass
class MatchManifest:
    """Immutable match summary and event manifest."""
    match_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    score: Tuple[int, int]
    total_steps: int
    possession: Tuple[float, float]  # [home_pct, away_pct]
    shots: Tuple[int, int]  # [home_shots, away_shots]
    shots_on_target: Tuple[int, int]  # [home_sot, away_sot]
    xg: Tuple[float, float]  # [home_xg, away_xg]
    passes_attempted: Tuple[int, int] = (0, 0)
    passes_completed: Tuple[int, int] = (0, 0)
    events: List[Dict[str, Any]] = field(default_factory=list)
    home_players: List[str] = field(default_factory=list)
    away_players: List[str] = field(default_factory=list)
    home_formation: str = "4-3-3"
    away_formation: str = "4-2-3-1"
    home_color: str = "#e63946"
    away_color: str = "#2196f3"
    engine_fingerprint: Dict[str, Any] = field(default_factory=dict)
    video_url: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchManifest":
        score = tuple(data.get("score", [data.get("home_score", 0), data.get("away_score", 0)]))
        possession = tuple(data.get("possession", (50.0, 50.0)))
        shots = tuple(data.get("shots", (0, 0)))
        shots_on_target = tuple(data.get("shots_on_target", (0, 0)))
        xg = tuple(data.get("xg", (0.0, 0.0)))
        passes_attempted = tuple(data.get("passes_attempted", (0, 0)))
        passes_completed = tuple(data.get("passes_completed", (0, 0)))
        return cls(
            match_id=str(data.get("match_id", "")),
            home_team=data.get("home_team", "Home"),
            away_team=data.get("away_team", "Away"),
            home_score=int(data.get("home_score", score[0] if score else 0)),
            away_score=int(data.get("away_score", score[1] if len(score) > 1 else 0)),
            score=(int(score[0]), int(score[1])),
            total_steps=int(data.get("total_steps", 0)),
            possession=(float(possession[0]), float(possession[1])),
            shots=(int(shots[0]), int(shots[1])),
            shots_on_target=(int(shots_on_target[0]), int(shots_on_target[1])),
            xg=(float(xg[0]), float(xg[1])),
            passes_attempted=(int(passes_attempted[0]), int(passes_attempted[1])),
            passes_completed=(int(passes_completed[0]), int(passes_completed[1])),
            events=data.get("events", []),
            home_players=data.get("home_players", []),
            away_players=data.get("away_players", []),
            home_formation=data.get("home_formation", "4-3-3"),
            away_formation=data.get("away_formation", "4-2-3-1"),
            home_color=data.get("home_color", "#e63946"),
            away_color=data.get("away_color", "#2196f3"),
            engine_fingerprint=data.get("engine_fingerprint", {}),
            video_url=data.get("video_url"),
            created_at=data.get("created_at"),
        )


@dataclass
class MatchTrajectory:
    """
    Compact binary representation of a complete match simulation.
    Contains time-series coordinates for all 22 players and the ball,
    agent action records, step scores, categorical game state, and verified match manifest.
    """
    match_id: str
    seed: int
    total_steps: int
    player_coords: np.ndarray  # shape: (T, 22, 2), float32
    player_dirs: np.ndarray  # shape: (T, 22, 2), float32
    ball_coords: np.ndarray  # shape: (T, 3), float32
    ball_dirs: np.ndarray  # shape: (T, 3), float32
    actions: np.ndarray  # shape: (T, 20), uint8
    scores: np.ndarray  # shape: (T, 2), uint8
    manifest: MatchManifest
    game_mode: Optional[np.ndarray] = None  # shape: (T,), int8
    ball_owned_team: Optional[np.ndarray] = None  # shape: (T,), int8
    ball_owned_player: Optional[np.ndarray] = None  # shape: (T,), int8

    def __post_init__(self):
        """Validate trajectory array dimensions, step counts, dtypes, domains, and finite values."""
        T = self.total_steps
        if T <= 0:
            raise ValueError(f"MatchTrajectory total_steps must be positive, got {T}")

        v2_fields = (self.game_mode, self.ball_owned_team, self.ball_owned_player)
        has_any_v2 = any(x is not None for x in v2_fields)
        has_all_v2 = all(x is not None for x in v2_fields)
        if has_any_v2 and not has_all_v2:
            raise ValueError(
                "Trajectory V2 fields must be provided atomically together: "
                "game_mode, ball_owned_team, ball_owned_player"
            )

        expected_specs = [
            ("player_coords", self.player_coords, (T, 22, 2), np.float32),
            ("player_dirs", self.player_dirs, (T, 22, 2), np.float32),
            ("ball_coords", self.ball_coords, (T, 3), np.float32),
            ("ball_dirs", self.ball_dirs, (T, 3), np.float32),
            ("actions", self.actions, (T, 20), np.uint8),
            ("scores", self.scores, (T, 2), np.uint8),
        ]
        if has_all_v2:
            expected_specs.extend([
                ("game_mode", self.game_mode, (T,), np.int8),
                ("ball_owned_team", self.ball_owned_team, (T,), np.int8),
                ("ball_owned_player", self.ball_owned_player, (T,), np.int8),
            ])

        for name, arr, expected_shape, expected_dtype in expected_specs:
            if arr is None or not isinstance(arr, np.ndarray):
                raise ValueError(f"MatchTrajectory field '{name}' must be a numpy ndarray")
            if arr.shape != expected_shape:
                raise ValueError(f"MatchTrajectory field '{name}' shape mismatch: expected {expected_shape}, got {arr.shape}")
            if arr.dtype != expected_dtype:
                raise ValueError(f"MatchTrajectory field '{name}' dtype mismatch: expected {expected_dtype}, got {arr.dtype}")
            if np.issubdtype(arr.dtype, np.floating) and not np.all(np.isfinite(arr)):
                raise ValueError(f"MatchTrajectory field '{name}' contains non-finite values (NaN or Inf)")

        # Categorical domain validations
        if has_all_v2:
            if self.game_mode is not None:
                invalid_modes = set(np.unique(self.game_mode)) - set(range(7))
                if invalid_modes:
                    raise ValueError(f"MatchTrajectory field 'game_mode' contains invalid game_mode values: {invalid_modes}")

            if self.ball_owned_team is not None:
                invalid_teams = set(np.unique(self.ball_owned_team)) - {-1, 0, 1}
                if invalid_teams:
                    raise ValueError(f"MatchTrajectory field 'ball_owned_team' contains invalid team values: {invalid_teams}")

            if self.ball_owned_player is not None:
                min_player = int(np.min(self.ball_owned_player))
                max_player = int(np.max(self.ball_owned_player))
                if min_player < -1 or max_player > 10:
                    raise ValueError(f"MatchTrajectory field 'ball_owned_player' values out of range [-1, 10]: min={min_player}, max={max_player}")

    def compute_physics_hash(self) -> str:
        """Compute schema-aware deterministic SHA256 checksum of raw physics arrays."""
        h = hashlib.sha256()
        h.update(str(TRAJECTORY_SCHEMA_VERSION if (self.game_mode is not None) else TRAJECTORY_SCHEMA_VERSION_V1).encode('utf-8'))
        h.update(str(self.seed).encode('utf-8'))
        fields = [
            ("player_coords", self.player_coords),
            ("player_dirs", self.player_dirs),
            ("ball_coords", self.ball_coords),
            ("ball_dirs", self.ball_dirs),
            ("actions", self.actions),
            ("scores", self.scores),
        ]
        if self.game_mode is not None:
            fields.append(("game_mode", self.game_mode))
        if self.ball_owned_team is not None:
            fields.append(("ball_owned_team", self.ball_owned_team))
        if self.ball_owned_player is not None:
            fields.append(("ball_owned_player", self.ball_owned_player))

        for name, arr in fields:
            h.update(f"{name}:{arr.dtype}:{arr.shape}".encode('utf-8'))
            h.update(arr.tobytes())

        return h.hexdigest()

    def compute_trajectory_hash(self) -> str:
        """Compute complete artifact SHA256 checksum combining physics arrays, metadata, and manifest summary."""
        h = hashlib.sha256()
        h.update(self.compute_physics_hash().encode('utf-8'))
        h.update(str(self.match_id).encode('utf-8'))
        if self.manifest:
            manifest_json = json.dumps(self.manifest.to_dict(), sort_keys=True)
            h.update(manifest_json.encode('utf-8'))
        return h.hexdigest()

    def get_frame_state(self, step: int) -> Dict[str, Any]:
        """Retrieve complete O(1) state snapshot for a specific simulation step."""
        idx = max(0, min(step, self.total_steps - 1))
        match_min = max(1, min(90, int((idx / max(self.total_steps, 1)) * 90)))
        state = {
            "step": idx,
            "match_minute": match_min,
            "player_coords": self.player_coords[idx],
            "player_dirs": self.player_dirs[idx],
            "ball_coords": self.ball_coords[idx],
            "ball_dirs": self.ball_dirs[idx],
            "actions": self.actions[idx] if idx < len(self.actions) else np.zeros(20, dtype=np.uint8),
            "score": [int(self.scores[idx, 0]), int(self.scores[idx, 1])],
            "is_second_half": idx > (self.total_steps // 2),
        }
        if self.game_mode is not None:
            state["game_mode"] = int(self.game_mode[idx])
        if self.ball_owned_team is not None:
            state["ball_owned_team"] = int(self.ball_owned_team[idx])
        if self.ball_owned_player is not None:
            state["ball_owned_player"] = int(self.ball_owned_player[idx])
        return state

    def save_to_npz(self, filepath: Path) -> Path:
        """Save trajectory and manifest to compressed .npz archive."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest_dict = self.manifest.to_dict()
        manifest_dict["trajectory_schema"] = (
            TRAJECTORY_SCHEMA_VERSION if (self.game_mode is not None) else TRAJECTORY_SCHEMA_VERSION_V1
        )
        manifest_json = json.dumps(manifest_dict)
        payload = {
            "player_coords": self.player_coords.astype(np.float32),
            "player_dirs": self.player_dirs.astype(np.float32),
            "ball_coords": self.ball_coords.astype(np.float32),
            "ball_dirs": self.ball_dirs.astype(np.float32),
            "actions": self.actions.astype(np.uint8),
            "scores": self.scores.astype(np.uint8),
            "seed": np.array([self.seed], dtype=np.int64),
            "manifest": np.array([manifest_json], dtype=object),
        }
        if self.game_mode is not None:
            payload["game_mode"] = self.game_mode.astype(np.int8)
        if self.ball_owned_team is not None:
            payload["ball_owned_team"] = self.ball_owned_team.astype(np.int8)
        if self.ball_owned_player is not None:
            payload["ball_owned_player"] = self.ball_owned_player.astype(np.int8)

        np.savez_compressed(str(path), **payload)
        return path

    @classmethod
    def load_from_npz(cls, filepath: Path) -> "MatchTrajectory":
        """Load trajectory and manifest from compressed .npz archive with backward compatibility."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Trajectory file not found: {path}")

        data = np.load(str(path), allow_pickle=True)
        manifest_dict = json.loads(str(data["manifest"][0]))
        manifest = MatchManifest.from_dict(manifest_dict)
        seed = int(data["seed"][0]) if "seed" in data else 0
        player_coords = data["player_coords"]
        total_steps = player_coords.shape[0]

        declared_schema = manifest_dict.get("trajectory_schema", TRAJECTORY_SCHEMA_VERSION_V1)
        game_mode = data["game_mode"] if "game_mode" in data else None
        ball_owned_team = data["ball_owned_team"] if "ball_owned_team" in data else None
        ball_owned_player = data["ball_owned_player"] if "ball_owned_player" in data else None

        has_v2_data = (game_mode is not None or ball_owned_team is not None or ball_owned_player is not None)

        if declared_schema == TRAJECTORY_SCHEMA_VERSION:
            if game_mode is None or ball_owned_team is None or ball_owned_player is None:
                raise ReplayIntegrityError(
                    f"Trajectory manifest declared schema '{TRAJECTORY_SCHEMA_VERSION}' "
                    "but required V2 state arrays (game_mode, ball_owned_team, ball_owned_player) are missing."
                )
        elif declared_schema == TRAJECTORY_SCHEMA_VERSION_V1:
            if has_v2_data:
                raise ReplayIntegrityError(
                    f"Trajectory manifest declared legacy schema '{TRAJECTORY_SCHEMA_VERSION_V1}' "
                    "but V2 state arrays are present in file."
                )
        else:
            raise ReplayIntegrityError(f"Unsupported trajectory schema version: '{declared_schema}'")

        return cls(
            match_id=manifest.match_id,
            seed=seed,
            total_steps=total_steps,
            player_coords=player_coords,
            player_dirs=data["player_dirs"],
            ball_coords=data["ball_coords"],
            ball_dirs=data["ball_dirs"],
            actions=data["actions"],
            scores=data["scores"],
            manifest=manifest,
            game_mode=game_mode,
            ball_owned_team=ball_owned_team,
            ball_owned_player=ball_owned_player,
        )
