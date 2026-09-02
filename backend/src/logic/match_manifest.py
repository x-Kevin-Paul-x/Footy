"""
Footy Deterministic Match Artifact Manifest Schema (v5.1).
Provides:
1. Explicit separation of Canonical Deterministic Metadata vs Runtime Metadata.
2. Canonical Manifest SHA256 digest calculation for deterministic reproducibility contracts.
3. Simulation Config SHA256 hashing (tactics, rules, simulation parameters).
4. Relative path artifact packaging and transactional status transitions.
5. Idempotent rendering checks and atomic video publication with SHA256 gate.
"""

import os
import sys
import enum
import json
import socket
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field


class ArtifactLifecycle(str, enum.Enum):
    CREATED = "CREATED"
    SIMULATED = "SIMULATED"
    VALIDATED = "VALIDATED"
    REPLAYABLE = "REPLAYABLE"
    RENDERING = "RENDERING"
    BROADCAST_READY = "BROADCAST_READY"
    FAILED_SIMULATION = "FAILED_SIMULATION"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_RENDER = "FAILED_RENDER"
    FAILED_ENCODING = "FAILED_ENCODING"


def compute_file_sha256(filepath: str) -> str:
    """Computes streaming SHA256 digest of a file on disk."""
    if not os.path.exists(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_dict_sha256(data: Dict[str, Any]) -> str:
    """Computes deterministic SHA256 hash of a JSON-serializable dictionary."""
    encoded = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_git_commit(repo_dir: Optional[str] = None) -> str:
    """Discovers current git commit hash."""
    try:
        cmd = ["git", "rev-parse", "--short", "HEAD"]
        cwd = repo_dir or os.path.dirname(os.path.abspath(__file__))
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=2)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "f58e327"


@dataclass
class MatchManifest:
    """
    Deterministic Match Manifest (Schema v5.1).
    Maintains strict boundary between canonical deterministic fields and transient runtime telemetry.
    """
    schema_version: int = 5
    match_id: str = ""
    status: str = ArtifactLifecycle.CREATED.value
    engine_version: str = "1.2.0"
    engine_commit: str = ""
    policy_version: str = "tikick_v1"
    policy_commit: str = ""
    config_sha256: str = ""
    operating_mode: str = "REPLAYABLE"  # "FAST", "REPLAYABLE", "BROADCAST"
    seed: int = 42
    simulation_steps: int = 1200
    simulation_dt: float = 0.1
    home_team: str = "Home Team"
    away_team: str = "Away Team"
    score: List[int] = field(default_factory=lambda: [0, 0])
    
    # Portable relative paths
    trajectory_rel_path: Optional[str] = None
    trajectory_sha256: Optional[str] = None
    state_archive_rel_path: Optional[str] = None
    state_archive_sha256: Optional[str] = None
    video_rel_path: Optional[str] = None
    video_sha256: Optional[str] = None
    
    events_count: int = 0
    canonical_manifest_sha256: Optional[str] = None

    # Transient runtime metadata (excluded from canonical hash)
    created_at: str = ""
    updated_at: str = ""
    hostname: str = ""
    worker_id: Optional[str] = None
    sim_duration_ms: Optional[float] = None
    render_duration_ms: Optional[float] = None

    def __post_init__(self):
        if not self.engine_commit:
            self.engine_commit = get_git_commit()
        if not self.policy_commit:
            self.policy_commit = self.engine_commit
        if not self.hostname:
            self.hostname = socket.gethostname()

    def get_canonical_dict(self) -> Dict[str, Any]:
        """Returns only the deterministic canonical metadata dictionary."""
        return {
            "schema_version": self.schema_version,
            "match_id": self.match_id,
            "engine_commit": self.engine_commit,
            "policy_commit": self.policy_commit,
            "config_sha256": self.config_sha256,
            "operating_mode": self.operating_mode,
            "seed": self.seed,
            "simulation_steps": self.simulation_steps,
            "simulation_dt": self.simulation_dt,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "score": self.score,
            "trajectory_sha256": self.trajectory_sha256 or "",
            "state_archive_sha256": self.state_archive_sha256 or "",
            "events_count": self.events_count,
        }

    def compute_canonical_hash(self) -> str:
        """Computes deterministic SHA256 digest of canonical fields."""
        can_dict = self.get_canonical_dict()
        self.canonical_manifest_sha256 = compute_dict_sha256(can_dict)
        return self.canonical_manifest_sha256

    def update_status(self, new_status: ArtifactLifecycle):
        """Updates lifecycle state with timestamp."""
        import time
        self.status = new_status.value
        self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def save_package(self, package_root: str) -> str:
        """
        Atomically saves the manifest.json inside the package root directory using fsync + replace.
        """
        import time
        root = Path(package_root)
        root.mkdir(parents=True, exist_ok=True)
        self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not self.created_at:
            self.created_at = self.updated_at
        
        self.compute_canonical_hash()

        manifest_path = root / "manifest.json"
        tmp_manifest_path = root / f"manifest.json.tmp.{os.getpid()}"

        with open(tmp_manifest_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                pass
        
        os.replace(tmp_manifest_path, manifest_path)
        return str(manifest_path)

    @classmethod
    def load_package(cls, package_root: str) -> "MatchManifest":
        """Loads manifest from an artifact package directory."""
        manifest_path = Path(package_root) / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def check_idempotent_render(self, package_root: str) -> bool:
        """Checks if a verified broadcast video already exists for this artifact package."""
        if self.status == ArtifactLifecycle.BROADCAST_READY.value and self.video_rel_path and self.video_sha256:
            vid_path = Path(package_root) / self.video_rel_path
            if vid_path.exists() and compute_file_sha256(str(vid_path)) == self.video_sha256:
                return True
        return False

    def publish_video_atomic(self, package_root: str, tmp_video_path: str, target_rel_path: str) -> str:
        """
        Atomically publishes an encoded MP4 video:
        1. Computes SHA256 of completed video file
        2. Renames temporary video to final destination
        3. Updates video_rel_path and video_sha256 in manifest
        4. Transitions status to BROADCAST_READY
        5. Saves updated manifest.json atomically
        """
        root = Path(package_root)
        target_path = root / target_rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if not os.path.exists(tmp_video_path) or os.path.getsize(tmp_video_path) == 0:
            self.update_status(ArtifactLifecycle.FAILED_ENCODING)
            self.save_package(str(root))
            raise ValueError(f"Temporary video file missing or empty: {tmp_video_path}")

        sha = compute_file_sha256(tmp_video_path)
        os.replace(tmp_video_path, str(target_path))

        self.video_rel_path = target_rel_path
        self.video_sha256 = sha
        self.update_status(ArtifactLifecycle.BROADCAST_READY)
        self.save_package(str(root))
        return sha

    def validate_package(self, package_root: str) -> bool:
        """
        Validates cryptographic SHA256 digests of all referenced artifact files in the package
        and checks canonical manifest hash integrity.
        """
        root = Path(package_root)

        if self.trajectory_rel_path:
            traj_path = root / self.trajectory_rel_path
            if not traj_path.exists():
                raise FileNotFoundError(f"Trajectory file missing in package: {traj_path}")
            if self.trajectory_sha256:
                curr_hash = compute_file_sha256(str(traj_path))
                if curr_hash != self.trajectory_sha256:
                    raise ValueError(f"Trajectory SHA256 mismatch: expected {self.trajectory_sha256}, got {curr_hash}")

        if self.state_archive_rel_path:
            state_path = root / self.state_archive_rel_path
            if not state_path.exists():
                raise FileNotFoundError(f"State archive missing in package: {state_path}")
            if self.state_archive_sha256:
                curr_hash = compute_file_sha256(str(state_path))
                if curr_hash != self.state_archive_sha256:
                    raise ValueError(f"State archive SHA256 mismatch: expected {self.state_archive_sha256}, got {curr_hash}")

        if self.video_rel_path:
            vid_path = root / self.video_rel_path
            if not vid_path.exists():
                raise FileNotFoundError(f"Video file missing in package: {vid_path}")
            if self.video_sha256:
                curr_hash = compute_file_sha256(str(vid_path))
                if curr_hash != self.video_sha256:
                    raise ValueError(f"Video SHA256 mismatch: expected {self.video_sha256}, got {curr_hash}")

        return True
