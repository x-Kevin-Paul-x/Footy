from pathlib import Path
from types import SimpleNamespace

import numpy as np


def test_double_round_robin_has_one_fixture_per_team_per_round():
    from models.league import League

    league = League("Schedule Test")
    league.teams = [SimpleNamespace(name=f"T{i}", team_id=i) for i in range(1, 21)]
    league.generate_schedule()

    assert len(league.schedule_rounds) == 38
    assert len(league.schedule) == 380
    seen = set()
    for matchday in league.schedule_rounds:
        participants = [team.team_id for fixture in matchday for team in fixture]
        assert len(participants) == len(set(participants)) == 20
        for home, away in matchday:
            seen.add((home.team_id, away.team_id))
    assert len(seen) == 380


def test_trajectory_roundtrip_does_not_require_pickle(tmp_path: Path):
    from logic.grf_trajectory import MatchManifest, MatchTrajectory

    steps = 3
    manifest = MatchManifest(
        match_id="safe", home_team="H", away_team="A", home_score=0,
        away_score=0, score=(0, 0), total_steps=steps,
        possession=(50.0, 50.0), shots=(0, 0), shots_on_target=(0, 0), xg=(0.0, 0.0),
    )
    trajectory = MatchTrajectory(
        match_id="safe", seed=7, total_steps=steps,
        player_coords=np.zeros((steps, 22, 2), dtype=np.float32),
        player_dirs=np.zeros((steps, 22, 2), dtype=np.float32),
        ball_coords=np.zeros((steps, 3), dtype=np.float32),
        ball_dirs=np.zeros((steps, 3), dtype=np.float32),
        actions=np.zeros((steps, 20), dtype=np.uint8),
        scores=np.zeros((steps, 2), dtype=np.uint8),
        manifest=manifest,
    )
    path = trajectory.save_to_npz(tmp_path / "trajectory.npz")

    with np.load(path, allow_pickle=False) as raw:
        assert raw["manifest"].dtype.kind == "U"
    loaded = MatchTrajectory.load_from_npz(path)
    assert loaded.match_id == "safe"
    assert loaded.get_frame_state(steps - 1)["match_minute"] == 90


def test_sqlite_backup_contains_wal_commits(tmp_path: Path, monkeypatch):
    import sqlite3
    import database.session as session

    source = tmp_path / "source.db"
    destination = tmp_path / "snapshot.db"
    monkeypatch.setattr(session, "DB_FILE", str(source))
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE values_table(value TEXT NOT NULL)")
        connection.execute("INSERT INTO values_table VALUES ('committed')")
        connection.commit()

    session.backup_database(str(destination))
    with sqlite3.connect(destination) as snapshot:
        assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert snapshot.execute("SELECT value FROM values_table").fetchone()[0] == "committed"


def test_match_identity_is_scoped_by_run_and_season():
    from database.models import Match

    names = {constraint.name for constraint in Match.__table__.constraints}
    assert "uq_match_run_season_number" in names


def test_central_batch_capacity_is_bounded_statically():
    import inspect
    from logic.simulation.simulation_process_pool import SimulationProcessPool

    source = inspect.getsource(SimulationProcessPool._run_central_batched_pool)
    assert "len(fixtures) > self.num_workers" in source
    assert "fixtures[start:start + self.num_workers]" in source
