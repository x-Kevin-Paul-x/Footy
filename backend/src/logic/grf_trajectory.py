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
    agent action records, step scores, and the verified match manifest.
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

    def compute_trajectory_hash(self) -> str:
        """Compute deterministic SHA256 checksum of trajectory physics arrays and manifest."""
        h = hashlib.sha256()
        h.update(str(self.seed).encode('utf-8'))
        h.update(self.player_coords.tobytes())
        h.update(self.player_dirs.tobytes())
        h.update(self.ball_coords.tobytes())
        h.update(self.ball_dirs.tobytes())
        h.update(self.actions.tobytes())
        h.update(self.scores.tobytes())
        if self.manifest:
            manifest_summary = f"{self.manifest.home_score}:{self.manifest.away_score}:{len(self.manifest.events)}"
            h.update(manifest_summary.encode('utf-8'))
        return h.hexdigest()

    def get_frame_state(self, step: int) -> Dict[str, Any]:
        """Retrieve complete O(1) state snapshot for a specific simulation step."""
        idx = max(0, min(step, self.total_steps - 1))
        match_min = max(1, min(90, int((idx / max(self.total_steps, 1)) * 90)))
        return {
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

    def save_to_npz(self, filepath: Path) -> Path:
        """Save trajectory and manifest to compressed .npz archive."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest_json = json.dumps(self.manifest.to_dict())
        np.savez_compressed(
            str(path),
            player_coords=self.player_coords.astype(np.float32),
            player_dirs=self.player_dirs.astype(np.float32),
            ball_coords=self.ball_coords.astype(np.float32),
            ball_dirs=self.ball_dirs.astype(np.float32),
            actions=self.actions.astype(np.uint8),
            scores=self.scores.astype(np.uint8),
            seed=np.array([self.seed], dtype=np.int64),
            manifest=np.array([manifest_json], dtype=object),
        )
        return path

    @classmethod
    def load_from_npz(cls, filepath: Path) -> "MatchTrajectory":
        """Load trajectory and manifest from compressed .npz archive."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Trajectory file not found: {path}")

        data = np.load(str(path), allow_pickle=True)
        manifest_dict = json.loads(str(data["manifest"][0]))
        manifest = MatchManifest.from_dict(manifest_dict)
        seed = int(data["seed"][0]) if "seed" in data else 0
        player_coords = data["player_coords"]
        total_steps = player_coords.shape[0]

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
        )
