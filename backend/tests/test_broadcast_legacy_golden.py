import hashlib
import json
from pathlib import Path

import pytest

from logic.grf_trajectory import MatchTrajectory
from logic.broadcast.stats import StatsSnapshotReducer


BACKEND_DIR = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "broadcast" / "legacy_arsenal_chelsea.json"
TRAJECTORY = BACKEND_DIR / "reports" / "recordings" / "trace_readme_showcase_arsenal_chelsea_20260906.npz"


@pytest.mark.skipif(not TRAJECTORY.exists(), reason="legacy showcase trajectory is a local golden artifact")
def test_legacy_arsenal_chelsea_canonical_hashes_and_result_are_unchanged():
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    trajectory = MatchTrajectory.load_from_npz(TRAJECTORY)
    assert hashlib.sha256(TRAJECTORY.read_bytes()).hexdigest() == expected["trajectory_file_sha256"]
    assert trajectory.compute_trajectory_hash() == expected["trajectory_hash"]
    assert trajectory.compute_physics_hash() == expected["physics_hash"]
    assert list(trajectory.manifest.score) == expected["canonical_result"]["score"]
    assert trajectory.manifest.events[0]["step"] == expected["halftime_step"]
    goal = next(event for event in trajectory.manifest.events if event["type"] == "goal")
    assert goal["step"] == expected["goal_step"]
    assert goal["scorer"] == expected["scorer"]

    halftime = StatsSnapshotReducer.at_step(trajectory, expected["halftime_step"])
    full_time = StatsSnapshotReducer.at_step(trajectory, trajectory.total_steps - 1)
    assert halftime.score == (0, 0)
    assert halftime.shots == (0, 0)
    assert halftime.xg == (0.0, 0.0)
    assert full_time.possession == tuple(expected["final_statistics"]["possession"])
    assert full_time.shots == tuple(expected["final_statistics"]["shots"])
    assert full_time.shots_on_target == tuple(expected["final_statistics"]["shots_on_target"])
    assert full_time.xg == tuple(expected["final_statistics"]["xg"])
    assert full_time.passes_attempted == tuple(expected["final_statistics"]["passes_attempted"])
    assert full_time.passes_completed == tuple(expected["final_statistics"]["passes_completed"])
