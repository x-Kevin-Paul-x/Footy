"""
Certification Test Suite for P1 (Consolidation & Render Decoupling),
P2 (API Standardization), P3 (Canonical Presentation Timeline), and P4 (Benchmark Harness).
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api_fastapi import app, RECORDINGS_DIR
from logic.simulation.match_executor import (
    GRFMatchExecutor,
    SimulationSpec,
    SimulationTransition,
    CanonicalMatchResult,
    ReplayMode,
)
from logic.simulation.simulation_worker import SimulationWorker
from logic.presentation_timeline import (
    PresentationTimeline,
    TimelineSegment,
    build_canonical_timeline,
)
from benchmarks.benchmark_harness import BenchmarkConfig, BenchmarkRunner

client = TestClient(app)


# ---------------------------------------------------------------------------
# P1.2: Simulation Consolidation via GRFMatchExecutor
# ---------------------------------------------------------------------------

def test_p1_2_match_executor_initialization_and_inheritance():
    """Verify that GRFMatchExecutor initializes properly and SimulationWorker subclasses it."""
    spec = SimulationSpec(
        fixture_id="test_cert_fix_01",
        season_year=2026,
        home_team_name="Arsenal",
        away_team_name="Chelsea",
        home_team_id=1,
        away_team_id=2,
        max_steps=200,
        seed_val=42,
        replay_mode=ReplayMode.NONE,
    )
    executor = GRFMatchExecutor(spec)
    assert executor.spec.fixture_id == "test_cert_fix_01"
    assert executor.spec.max_steps == 200

    # Verify SimulationWorker inherits from GRFMatchExecutor
    worker = SimulationWorker(spec)
    assert isinstance(worker, GRFMatchExecutor)


def test_p1_2_match_executor_deterministic_execution():
    """Verify GRFMatchExecutor executes deterministically for a given seed."""
    spec1 = SimulationSpec(
        fixture_id="fix_det_01",
        season_year=2026,
        home_team_name="Liverpool",
        away_team_name="Man City",
        home_team_id=3,
        away_team_id=4,
        max_steps=300,
        seed_val=1337,
        replay_mode=ReplayMode.NONE,
    )
    executor1 = GRFMatchExecutor(spec1)
    res1 = executor1.execute()

    spec2 = SimulationSpec(
        fixture_id="fix_det_02",
        season_year=2026,
        home_team_name="Liverpool",
        away_team_name="Man City",
        home_team_id=3,
        away_team_id=4,
        max_steps=300,
        seed_val=1337,
        replay_mode=ReplayMode.NONE,
    )
    executor2 = GRFMatchExecutor(spec2)
    res2 = executor2.execute()

    # Scores, shots, and possession must match identically
    assert res1.home_goals == res2.home_goals
    assert res1.away_goals == res2.away_goals
    assert res1.home_shots == res2.home_shots
    assert res1.away_shots == res2.away_shots
    assert res1.home_possession == res2.home_possession


# ---------------------------------------------------------------------------
# P1.4: On-Demand Render Endpoint
# ---------------------------------------------------------------------------

def test_p1_4_on_demand_render_endpoint(monkeypatch, tmp_path):
    """Verify POST /api/v1/match/{match_id}/render recognizes ready video or renders without resimulation."""
    test_recordings = tmp_path / "recordings"
    test_recordings.mkdir(parents=True)
    monkeypatch.setattr("api_fastapi.RECORDINGS_DIR", test_recordings)

    # 1. Existing video returns ready immediately
    dummy_video = test_recordings / "match_5555.mp4"
    dummy_video.write_bytes(b"dummy_mp4_bytes")

    resp = client.post("/api/v1/match/5555/render", json={"force": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_id"] == "5555"
    assert data["status"] == "ready"
    assert data["video_url"] == "/recordings/match_5555.mp4"

    # 2. Missing match returns 404
    monkeypatch.setattr("database.match_db.get_match_details", lambda mid: None)
    resp_404 = client.post("/api/v1/match/nonexistent_match/render", json={"force": True})
    assert resp_404.status_code == 404


# ---------------------------------------------------------------------------
# P3.1: Canonical Presentation Timeline & Seeking
# ---------------------------------------------------------------------------

def test_p3_1_canonical_presentation_timeline_construction(tmp_path):
    """Verify build_canonical_timeline constructs 3-clock mapping and seeking handles intro/halftime."""
    events = [
        {"minute": 23, "step": 300, "type": "GOAL", "player": "Saka", "team": "home"},
        {"minute": 78, "step": 1040, "type": "GOAL", "player": "Havertz", "team": "home"},
    ]

    timeline = build_canonical_timeline(
        match_id="cert_match_100",
        total_steps=1200,
        events=events,
        fps=15.0,
        intro_frames=45,       # 3.0s
        halftime_frames=60,    # 4.0s
        fulltime_frames=75,    # 5.0s
    )

    assert timeline.match_id == "cert_match_100"
    assert timeline.fps == 15.0
    assert len(timeline.segments) >= 5  # intro, first_half, halftime, second_half, fulltime + goal replays
    assert timeline.total_duration_seconds > 0

    # Presentation timestamp for minute 1 must be strictly after the 3.0s intro card
    pts_m1 = timeline.seek_minute(1)
    assert pts_m1 >= 3.0

    # Presentation timestamp for minute 50 must be strictly after the 4.0s halftime card
    pts_m50 = timeline.seek_minute(50)
    pts_m45 = timeline.seek_minute(45)
    assert pts_m50 > pts_m45 + 4.0

    # JSON Roundtrip
    json_path = tmp_path / "test_timeline.json"
    timeline.save_to_file(json_path)
    loaded = PresentationTimeline.load_from_file(json_path)
    assert loaded.match_id == timeline.match_id
    assert loaded.total_frames == timeline.total_frames
    assert loaded.seek_minute(23) == timeline.seek_minute(23)


def test_p3_1_timeline_api_endpoint(monkeypatch, tmp_path):
    """Verify GET /api/v1/match/{match_id}/timeline returns canonical presentation mapping."""
    test_recordings = tmp_path / "recordings"
    test_recordings.mkdir(parents=True)
    monkeypatch.setattr("api_fastapi.RECORDINGS_DIR", test_recordings)

    # Place companion timeline JSON
    tl_file = test_recordings / "match_7777.timeline.json"
    dummy_tl = {
        "match_id": "7777",
        "fps": 15.0,
        "total_frames": 1500,
        "total_duration_seconds": 100.0,
        "segments": [],
        "events_pts_map": {"step_300": 25.4},
        "minute_to_pts": {"1": 3.2, "23": 25.4, "90": 95.0},
        "timeline_version": "1.0.0"
    }
    tl_file.write_text(json.dumps(dummy_tl), encoding="utf-8")

    resp = client.get("/api/v1/match/7777/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_id"] == "7777"
    assert data["minute_to_pts"]["23"] == 25.4


# ---------------------------------------------------------------------------
# P2.2: API Route Standardization & Backward Compatibility
# ---------------------------------------------------------------------------

def test_p2_2_canonical_and_deprecated_route_equivalence():
    """Verify that canonical /api/v1 routes and deprecated root routes return identical responses."""
    # 1. Health
    r_v1 = client.get("/api/v1/health")
    r_root = client.get("/health")
    assert r_v1.status_code == 200
    assert r_root.status_code == 200
    assert r_v1.json() == r_root.json()

    # 2. Teams
    r_v1_teams = client.get("/api/v1/teams")
    r_root_teams = client.get("/teams")
    assert r_v1_teams.status_code == 200
    assert r_root_teams.status_code == 200
    assert r_v1_teams.json() == r_root_teams.json()

    # 3. Players
    r_v1_players = client.get("/api/v1/players")
    r_root_players = client.get("/players")
    assert r_v1_players.status_code == 200
    assert r_root_players.status_code == 200
    assert r_v1_players.json() == r_root_players.json()

    # 4. Seasons
    r_v1_seasons = client.get("/api/v1/seasons")
    r_root_seasons = client.get("/get-seasons")
    assert r_v1_seasons.status_code == 200
    assert r_root_seasons.status_code == 200
    assert r_v1_seasons.json() == r_root_seasons.json()

    # 5. Financial Summary
    r_v1_fin = client.get("/api/v1/financial-summary")
    r_root_fin = client.get("/financial-summary")
    assert r_v1_fin.status_code == 200
    assert r_root_fin.status_code == 200
    assert r_v1_fin.json() == r_root_fin.json()

    # 6. Youth Prospects
    r_v1_youth = client.get("/api/v1/youth-prospects")
    r_root_youth = client.get("/youth-prospects")
    assert r_v1_youth.status_code == 200
    assert r_root_youth.status_code == 200
    assert r_v1_youth.json() == r_root_youth.json()


# ---------------------------------------------------------------------------
# P4.1: Benchmark Harness Gate
# ---------------------------------------------------------------------------

def test_p4_1_benchmark_harness_smoke_execution(tmp_path):
    """Verify BenchmarkRunner executes in smoke mode, records percentiles and passes determinism gate."""
    bench_dir = tmp_path / "bench_results"
    config = BenchmarkConfig(
        worker_counts=[1],
        fixture_counts=[1, 2],
        step_counts=[100],
        replay_modes=["none"],
        repetitions=2,
        smoke=True,
        output_dir=bench_dir,
    )
    runner = BenchmarkRunner(config)
    report = runner.run_suite()

    assert report["all_passed"] is True
    assert "machine_metadata" in report
    assert "python_version" in report["machine_metadata"]
    assert len(report["results"]) == 2

    # Check metrics computed
    for res in report["results"]:
        assert res["throughput_fixtures_per_sec"] > 0
        assert res["p50_latency_sec"] > 0
        assert res["p95_latency_sec"] > 0
        assert res["correctness_pass"] is True
        assert len(res["result_hashes"]) == 2

    # Verify report written to disk
    assert Path(report["saved_path"]).is_file()
