import copy

import numpy as np
import pytest

from logic.broadcast.stats import StatsSnapshotReducer
from logic.grf_trajectory import MatchManifest, MatchTrajectory


def _trajectory() -> MatchTrajectory:
    total_steps = 8
    events = [
        {"type": "shot", "team": "home", "step": 1, "minute": 12, "xg": 0.2, "on_target": True, "outcome": "SAVED"},
        {"type": "save", "team": "away", "step": 2, "minute": 13},
        {"type": "shot", "team": "home", "step": 3, "minute": 45, "xg": 0.4, "on_target": True, "outcome": "GOAL"},
        {"type": "goal", "team": "home", "step": 3, "minute": 45, "scorer": "Arsenal Player 8"},
        {"type": "half_time", "step": 3, "minute": 45, "score": "1-0"},
        {"type": "shot", "team": "away", "step": 5, "minute": 67, "xg": 0.1, "on_target": False, "outcome": "OFF_TARGET"},
        {"type": "full_time", "step": 7, "minute": 90, "score": "1-0"},
    ]
    manifest = MatchManifest(
        match_id="broadcast_stats_fixture",
        home_team="Arsenal",
        away_team="Chelsea",
        home_score=1,
        away_score=0,
        score=(1, 0),
        total_steps=total_steps,
        possession=(50.0, 50.0),
        shots=(2, 1),
        shots_on_target=(2, 0),
        xg=(0.6, 0.1),
        passes_attempted=(1, 1),
        passes_completed=(1, 1),
        events=events,
    )
    actions = np.zeros((total_steps, 20), dtype=np.uint8)
    actions[1, 0] = 11  # home player 1 passes; player 2 receives at step 2
    actions[5, 10] = 10  # away player 1 passes; player 2 receives at step 6
    scores = np.zeros((total_steps, 2), dtype=np.uint8)
    scores[3:, 0] = 1
    owners = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int8)
    players = np.array([1, 1, 2, 2, 1, 1, 2, 2], dtype=np.int8)
    return MatchTrajectory(
        match_id=manifest.match_id,
        seed=123,
        total_steps=total_steps,
        player_coords=np.zeros((total_steps, 22, 2), dtype=np.float32),
        player_dirs=np.zeros((total_steps, 22, 2), dtype=np.float32),
        ball_coords=np.zeros((total_steps, 3), dtype=np.float32),
        ball_dirs=np.zeros((total_steps, 3), dtype=np.float32),
        actions=actions,
        scores=scores,
        manifest=manifest,
        game_mode=np.zeros(total_steps, dtype=np.int8),
        ball_owned_team=owners,
        ball_owned_player=players,
    )


def test_halftime_snapshot_uses_only_first_half_data():
    snapshot = StatsSnapshotReducer.at_step(_trajectory(), 3)

    assert snapshot.score == (1, 0)
    assert snapshot.possession == (100.0, 0.0)
    assert snapshot.shots == (2, 0)
    assert snapshot.shots_on_target == (2, 0)
    assert snapshot.xg == (0.6, 0.0)
    assert snapshot.passes_attempted == (1, 0)
    assert snapshot.passes_completed == (1, 0)
    assert {event["type"] for event in snapshot.events} == {"shot", "save", "goal", "half_time"}


def test_full_time_snapshot_equals_canonical_manifest():
    trajectory = _trajectory()
    snapshot = StatsSnapshotReducer.at_step(trajectory, trajectory.total_steps - 1)

    assert snapshot.score == trajectory.manifest.score
    assert snapshot.possession == trajectory.manifest.possession
    assert snapshot.shots == trajectory.manifest.shots
    assert snapshot.shots_on_target == trajectory.manifest.shots_on_target
    assert snapshot.xg == trajectory.manifest.xg
    assert snapshot.passes_attempted == trajectory.manifest.passes_attempted
    assert snapshot.passes_completed == trajectory.manifest.passes_completed


def test_pass_reconstruction_matches_executor_state_machine_semantics():
    trajectory = _trajectory()

    first_half = StatsSnapshotReducer.at_step(trajectory, 3)
    full_time = StatsSnapshotReducer.at_step(trajectory, 7)

    assert first_half.passes_attempted == (1, 0)
    assert first_half.passes_completed == (1, 0)
    assert full_time.passes_attempted == (1, 1)
    assert full_time.passes_completed == (1, 1)


def test_event_cutoff_and_inputs_are_immutable():
    trajectory = _trajectory()
    arrays_before = {
        "actions": trajectory.actions.copy(),
        "scores": trajectory.scores.copy(),
        "owners": trajectory.ball_owned_team.copy(),
        "players": trajectory.ball_owned_player.copy(),
    }
    events_before = copy.deepcopy(trajectory.manifest.events)

    early = StatsSnapshotReducer.at_step(trajectory, 2)
    late = StatsSnapshotReducer.at_step(trajectory, 5)

    assert all(event["step"] <= 2 for event in early.events)
    assert all(event["step"] <= 5 for event in late.events)
    with pytest.raises(TypeError):
        early.events[0]["type"] = "mutated"

    assert np.array_equal(trajectory.actions, arrays_before["actions"])
    assert np.array_equal(trajectory.scores, arrays_before["scores"])
    assert np.array_equal(trajectory.ball_owned_team, arrays_before["owners"])
    assert np.array_equal(trajectory.ball_owned_player, arrays_before["players"])
    assert trajectory.manifest.events == events_before
