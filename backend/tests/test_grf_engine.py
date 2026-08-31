"""
Comprehensive Test Suite for GRF & TiKick 3D Simulation Engine.
Tests canonical architecture, perspective symmetry, trajectory serialization,
attribute mapping, truthful statistics invariants, and FastAPI endpoints.
"""

import math
import numpy as np
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api_fastapi import app
from logic.grf_trajectory import MatchTrajectory, MatchManifest
from logic.footy_grf_adapter import FootyGRFAdapter, FORMATION_COORDINATES, GRFPlayerProfile
from logic.grf_core import extract_canonical_features, compute_shot_xg, ACTION_MIRROR_MAP

client = TestClient(app)


def test_engine_status_endpoint():
    """Test engine status reporting."""
    response = client.get("/api/v1/engine/status")
    assert response.status_code == 200
    data = response.json()
    assert "engine_mode" in data
    assert "grf_available" in data
    assert "checkpoint_found" in data
    assert "baller_dir" in data


def test_match_video_endpoint_missing():
    """Test nonexistent video query returns available=False."""
    response = client.get("/api/v1/match/nonexistent_match_99999/video")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "nonexistent_match_99999"
    assert data["available"] is False


def test_formation_coordinates_bounds():
    """Verify all formation coordinate presets have 11 positions within pitch bounds."""
    for form_name, coords in FORMATION_COORDINATES.items():
        assert len(coords) == 11, f"Formation {form_name} must have 11 player coordinates"
        for x, y in coords:
            assert -1.0 <= x <= 1.0, f"Coordinate x={x} out of range in {form_name}"
            assert -0.45 <= y <= 0.45, f"Coordinate y={y} out of range in {form_name}"


def test_footy_grf_adapter_attribute_mapping():
    """Test mapping of Footy player attributes to simulation multipliers."""
    fast_player = {
        "id": 1,
        "name": "Speedster",
        "position": "RW",
        "potential": 90,
        "attributes": {
            "physical": {"pace": 95, "acceleration": 95, "stamina": 90},
            "technical": {"shooting": 88, "passing": 82, "finishing": 89}
        }
    }
    profile_fast = FootyGRFAdapter.extract_player_profile(fast_player, assigned_pos="RW")
    assert profile_fast.name == "Speedster"
    assert profile_fast.speed_multiplier > 1.05
    assert profile_fast.stamina_decay_rate < 0.90
    assert profile_fast.shot_quality_modifier > 1.10

    slow_player = {
        "id": 2,
        "name": "TargetMan",
        "position": "ST",
        "potential": 60,
        "attributes": {
            "physical": {"pace": 45, "stamina": 50},
            "technical": {"shooting": 65, "passing": 50}
        }
    }
    profile_slow = FootyGRFAdapter.extract_player_profile(slow_player, assigned_pos="ST")
    assert profile_slow.speed_multiplier < 1.0
    assert profile_slow.stamina_decay_rate > 0.95
    assert profile_fast.speed_multiplier > profile_slow.speed_multiplier


def test_action_mirror_map_completeness():
    """Verify dual-team action mirroring map covers directional actions symmetrically."""
    # 180° spatial symmetry pairs
    assert ACTION_MIRROR_MAP[1] == 5  # left <-> right
    assert ACTION_MIRROR_MAP[5] == 1
    assert ACTION_MIRROR_MAP[2] == 6  # top_left <-> bottom_right
    assert ACTION_MIRROR_MAP[6] == 2
    assert ACTION_MIRROR_MAP[3] == 7  # top <-> bottom
    assert ACTION_MIRROR_MAP[7] == 3
    assert ACTION_MIRROR_MAP[4] == 8  # top_right <-> bottom_left
    assert ACTION_MIRROR_MAP[8] == 4

    # Non-directional actions are invariant
    for act in [0, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]:
        assert ACTION_MIRROR_MAP[act] == act


def test_tikick_perspective_symmetry():
    """Verify right team observation extraction applies exact 180° pitch inversion for all 11 distinct player coords."""
    unique_left_coords = [
        [-0.95, 0.00], [-0.60, 0.30], [-0.70, 0.10], [-0.70, -0.10], [-0.60, -0.30],
        [-0.45, 0.00], [-0.30, 0.18], [-0.30, -0.18], [-0.15, 0.28], [-0.10, 0.00], [-0.15, -0.28]
    ]
    unique_right_coords = [
        [0.95, 0.00], [0.60, -0.30], [0.70, -0.10], [0.70, 0.10], [0.60, 0.30],
        [0.45, 0.00], [0.30, -0.18], [0.30, 0.18], [0.15, -0.28], [0.10, 0.00], [0.15, 0.28]
    ]

    raw_obs_left = [{
        'left_team': unique_left_coords,
        'left_team_direction': [[0.05, 0.01 * (i - 5)] for i in range(11)],
        'right_team': unique_right_coords,
        'right_team_direction': [[-0.05, -0.01 * (i - 5)] for i in range(11)],
        'ball': [0.2, 0.05, 0.0],
        'ball_direction': [0.05, 0.01, 0.0],
        'ball_owned_team': 0,
        'ball_owned_player': 8,
        'active': 8,
        'game_mode': 0,
        'steps_left': 2000,
        'score': [2, 1],
        'sticky_actions': [0] * 10,
        'left_team_tired_factor': [0.0] * 11,
        'left_team_yellow_card': [0.0] * 11,
        'left_team_active': [1.0] * 11,
        'right_team_tired_factor': [0.0] * 11,
        'right_team_yellow_card': [0.0] * 11,
        'right_team_active': [1.0] * 11,
    } for _ in range(10)]

    raw_obs_right = [{
        'left_team': unique_left_coords,
        'left_team_direction': [[0.05, 0.01 * (i - 5)] for i in range(11)],
        'right_team': unique_right_coords,
        'right_team_direction': [[-0.05, -0.01 * (i - 5)] for i in range(11)],
        'ball': [0.2, 0.05, 0.0],
        'ball_direction': [0.05, 0.01, 0.0],
        'ball_owned_team': 0,
        'ball_owned_player': 8,
        'active': 8,
        'game_mode': 0,
        'steps_left': 2000,
        'score': [2, 1],
        'sticky_actions': [0] * 10,
        'left_team_tired_factor': [0.0] * 11,
        'left_team_yellow_card': [0.0] * 11,
        'left_team_active': [1.0] * 11,
        'right_team_tired_factor': [0.0] * 11,
        'right_team_yellow_card': [0.0] * 11,
        'right_team_active': [1.0] * 11,
    } for _ in range(10)]

    feat_l, _, _ = extract_canonical_features(raw_obs_left, team_side="left", num_agents=10)
    feat_r, _, _ = extract_canonical_features(raw_obs_right, team_side="right", num_agents=10)

    assert feat_l.shape == (10, 268)
    assert feat_r.shape == (10, 268)
    # Right team ally coordinates are 180° mirrored right_team [0.95, 0.0] -> [-0.95, 0.0]
    for p_i in range(11):
        expected_mirrored = -np.array(unique_right_coords[p_i], dtype=np.float32)
        actual_ally = feat_r[0, (p_i*2):(p_i*2 + 2)]
        assert np.allclose(actual_ally, expected_mirrored), f"Player {p_i} coordinate mismatch in right perspective"


def test_match_trajectory_serialization(tmp_path):
    """Test MatchTrajectory save to .npz and load roundtrip with checksum validation."""
    steps = 100
    player_coords = np.random.randn(steps, 22, 2).astype(np.float32)
    player_dirs = np.random.randn(steps, 22, 2).astype(np.float32)
    ball_coords = np.random.randn(steps, 3).astype(np.float32)
    ball_dirs = np.random.randn(steps, 3).astype(np.float32)
    actions = np.random.randint(0, 19, size=(steps, 20), dtype=np.uint8)
    scores = np.zeros((steps, 2), dtype=np.uint8)

    manifest = MatchManifest(
        match_id="test_traj_001",
        home_team="Arsenal",
        away_team="Chelsea",
        home_score=2,
        away_score=1,
        score=(2, 1),
        total_steps=steps,
        possession=(55.0, 45.0),
        shots=(8, 6),
        shots_on_target=(4, 3),
        xg=(1.85, 1.10),
        passes_attempted=(240, 190),
        passes_completed=(210, 160),
        events=[{"minute": 23, "type": "goal", "team": "home", "player": "Saka"}],
    )

    traj = MatchTrajectory(
        match_id="test_traj_001",
        seed=424242,
        total_steps=steps,
        player_coords=player_coords,
        player_dirs=player_dirs,
        ball_coords=ball_coords,
        ball_dirs=ball_dirs,
        actions=actions,
        scores=scores,
        manifest=manifest,
    )

    original_hash = traj.compute_trajectory_hash()
    npz_file = tmp_path / "test_traj_001.npz"
    traj.save_to_npz(npz_file)

    loaded_traj = MatchTrajectory.load_from_npz(npz_file)
    assert loaded_traj.match_id == "test_traj_001"
    assert loaded_traj.seed == 424242
    assert loaded_traj.manifest.home_score == 2
    assert loaded_traj.compute_trajectory_hash() == original_hash
    assert np.array_equal(loaded_traj.player_coords, player_coords)


def test_opta_xg_model():
    """Test physics & geometry based xG calculation monotonicity and bounds."""
    # Close-range shot directly in front of goal (dist ~ 0.10)
    defenders_empty = np.empty((0, 2))
    xg_close = compute_shot_xg(shooter_x=0.90, shooter_y=0.0, goal_x=1.0, defenders=defenders_empty, shooting_attr=85.0)
    assert 0.40 <= xg_close <= 0.92

    # Long-range shot from midfield (dist ~ 0.50)
    xg_far = compute_shot_xg(shooter_x=0.50, shooter_y=0.20, goal_x=1.0, defenders=defenders_empty, shooting_attr=85.0)
    assert xg_far < xg_close
    assert 0.02 <= xg_far <= 0.35


def test_simulate_grf_match_endpoint_fast_mode():
    """Test /api/v1/match/simulate-grf with generate_video=False executes fast Phase A simulation."""
    import time
    t0 = time.time()
    payload = {
        "home_team_name": "Arsenal",
        "away_team_name": "Chelsea",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "generate_video": False,
        "max_steps": 300
    }
    response = client.post("/api/v1/match/simulate-grf", json=payload)
    elapsed = time.time() - t0

    assert response.status_code == 200
    data = response.json()
    assert data["home_team"] == "Arsenal"
    assert data["away_team"] == "Chelsea"
    assert "home_score" in data
    assert "away_score" in data
    assert "possession" in data
    assert "shots" in data
    assert "xg" in data
    assert "timeline" in data

    # Verify statistical invariants
    h_s = data["shots"]["home"]
    a_s = data["shots"]["away"]
    assert h_s >= data["home_score"], "Shots must be >= goals"
    assert a_s >= data["away_score"], "Shots must be >= goals"
    assert 95.0 <= (data["possession"]["home"] + data["possession"]["away"]) <= 105.0

    # Video URL must be None since generate_video was False
    assert data.get("video_url") is None
    # Fast simulation should complete in seconds
    assert elapsed < 30.0, f"Fast mode simulation took too long: {elapsed:.2f}s"


def test_simulation_determinism_level_2():
    """Verify trajectory replay fidelity: trajectory save/load reproduces 100% identical hash and manifest."""
    from logic.grf_native_runner import GRFNativeRunner
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("GRF WSL environment not available")

    fixed_seed = 338822
    sim1 = runner.simulate(
        home_team="Arsenal",
        away_team="Chelsea",
        max_steps=150,
        match_id="test_det_fidelity",
        seed_val=fixed_seed,
    )

    npz_path = Path(f"backend/reports/recordings/trace_test_det_fidelity.npz")
    assert npz_path.exists(), "Trajectory .npz file must be persisted"

    traj = MatchTrajectory.load_from_npz(npz_path)
    assert traj.manifest.score == tuple(sim1["score"]), "Loaded trajectory score must match simulation"
    assert traj.compute_trajectory_hash() == sim1.get("trajectory_hash"), "Trajectory hash must be 100% bit-for-bit identical"
    assert len(traj.manifest.events) == len(sim1.get("events", [])), "Events list must be identical"


def test_simulation_seed_variation():
    """Verify different seeds produce different match outcomes / trajectories."""
    from logic.grf_native_runner import GRFNativeRunner
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("GRF WSL environment not available")

    sim_a = runner.simulate(
        home_team="Liverpool",
        away_team="ManCity",
        max_steps=150,
        match_id="test_var_a",
        seed_val=11111,
    )
    sim_b = runner.simulate(
        home_team="Liverpool",
        away_team="ManCity",
        max_steps=150,
        match_id="test_var_b",
        seed_val=99999,
    )

    assert sim_a.get("trajectory_hash") != sim_b.get("trajectory_hash"), "Different seeds must produce different trajectories"


def test_simulate_grf_match_endpoint_with_video_async():
    """Test /api/v1/match/simulate-grf with generate_video=True returns video_url."""
    import time
    t0 = time.time()
    payload = {
        "home_team_name": "Liverpool",
        "away_team_name": "ManCity",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "generate_video": True,
        "max_steps": 150
    }
    response = client.post("/api/v1/match/simulate-grf", json=payload)
    elapsed = time.time() - t0

    assert response.status_code == 200
    data = response.json()
    assert data["home_team"] == "Liverpool"
    assert data["away_team"] == "ManCity"
    assert data.get("video_url") is not None
    assert "/recordings/" in data["video_url"]
    assert elapsed < 90.0, f"Render request took too long: {elapsed:.2f}s"


def test_pure_trajectory_renderer_integrity(tmp_path):
    """Verify that grf_renderer renders valid broadcast MP4 without importing or calling football_env."""
    import sys
    from logic.grf_renderer import render_video_from_trajectory

    # Ensure gfootball is NOT imported on host
    assert "gfootball.env" not in sys.modules, "Pure trajectory renderer must not import gfootball.env"

    steps = 30
    player_coords = np.zeros((steps, 22, 2), dtype=np.float32)
    # Set default positions
    for i in range(11):
        player_coords[:, i, 0] = -0.8 + i * 0.07
        player_coords[:, i, 1] = -0.3 + (i % 4) * 0.2
        player_coords[:, i + 11, 0] = 0.8 - i * 0.07
        player_coords[:, i + 11, 1] = -0.3 + (i % 4) * 0.2

    player_dirs = np.zeros((steps, 22, 2), dtype=np.float32)
    ball_coords = np.zeros((steps, 3), dtype=np.float32)
    ball_dirs = np.zeros((steps, 3), dtype=np.float32)
    actions = np.zeros((steps, 20), dtype=np.uint8)
    scores = np.zeros((steps, 2), dtype=np.uint8)

    manifest = MatchManifest(
        match_id="test_pure_render_01",
        home_team="Arsenal",
        away_team="Chelsea",
        home_score=1,
        away_score=0,
        score=(1, 0),
        total_steps=steps,
        possession=(60.0, 40.0),
        shots=(5, 3),
        shots_on_target=(3, 1),
        xg=(1.2, 0.4),
        passes_attempted=(40, 30),
        passes_completed=(35, 22),
        events=[{"minute": 44, "type": "goal", "team": "home", "player": "Saka"}],
    )

    traj = MatchTrajectory(
        match_id="test_pure_render_01",
        seed=12345,
        total_steps=steps,
        player_coords=player_coords,
        player_dirs=player_dirs,
        ball_coords=ball_coords,
        ball_dirs=ball_dirs,
        actions=actions,
        scores=scores,
        manifest=manifest,
    )

    out_mp4 = tmp_path / "pure_render_test.mp4"
    video_url = render_video_from_trajectory(traj, str(out_mp4))

    assert out_mp4.exists(), "MP4 video file must be generated"
    assert out_mp4.stat().st_size > 1000, "MP4 video file must contain valid encoded frames"
    assert "pure_render_test.mp4" in video_url


def test_attribute_sensitivity():
    """Verify that teams with different attributes produce measurably distinct velocities and trajectories under the exact same seed."""
    from logic.grf_native_runner import GRFNativeRunner
    from logic.footy_grf_adapter import GRFPlayerProfile, GRFTeamTactics
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("GRF WSL environment not available")

    fixed_seed = 777888
    # High-pace team
    high_pace_profiles = [
        GRFPlayerProfile(name=f"Speed_{i+1}", pace=95.0, shooting=90.0, stamina=95.0, defending=85.0).to_dict()
        for i in range(11)
    ]
    # Low-pace team
    low_pace_profiles = [
        GRFPlayerProfile(name=f"Slow_{i+1}", pace=40.0, shooting=45.0, stamina=40.0, defending=45.0).to_dict()
        for i in range(11)
    ]

    sim_high = runner.simulate(
        home_team="HighPaceFC",
        away_team="OpponentFC",
        max_steps=120,
        match_id="test_attr_high",
        seed_val=fixed_seed,
        home_tactics=GRFTeamTactics(team_name="HighPaceFC", offensive_bias=80.0, pressing_intensity=85.0, roster=[GRFPlayerProfile(**p) for p in high_pace_profiles]),
    )

    sim_low = runner.simulate(
        home_team="LowPaceFC",
        away_team="OpponentFC",
        max_steps=120,
        match_id="test_attr_low",
        seed_val=fixed_seed,
        home_tactics=GRFTeamTactics(team_name="LowPaceFC", offensive_bias=20.0, pressing_intensity=25.0, roster=[GRFPlayerProfile(**p) for p in low_pace_profiles]),
    )

    assert sim_high.get("trajectory_hash") != sim_low.get("trajectory_hash"), "Attribute differences must produce distinct trajectories under identical seed"


def test_state_machine_invariants():
    """Assert passes_attempted >= passes_completed >= 0 and shots >= shots_on_target >= goals across simulated matches."""
    from logic.grf_native_runner import GRFNativeRunner
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("GRF WSL environment not available")

    sim = runner.simulate(
        home_team="Arsenal",
        away_team="Chelsea",
        max_steps=150,
        match_id="test_invariants",
        seed_val=424242,
    )

    # State Machine Pass Invariants
    p_att_h, p_att_a = sim["passes_attempted"]
    p_cmp_h, p_cmp_a = sim["passes_completed"]
    assert p_att_h >= p_cmp_h >= 0, f"Home passes invalid: attempted={p_att_h}, completed={p_cmp_h}"
    assert p_att_a >= p_cmp_a >= 0, f"Away passes invalid: attempted={p_att_a}, completed={p_cmp_a}"

    # State Machine Shot & Goal Invariants
    shots_h, shots_a = sim["shots"]
    sot_h, sot_a = sim["shots_on_target"]
    g_h, g_a = sim["score"]
    assert shots_h >= sot_h >= g_h >= 0, f"Home shots invariant violated: {shots_h} >= {sot_h} >= {g_h}"
    assert shots_a >= sot_a >= g_a >= 0, f"Away shots invariant violated: {shots_a} >= {sot_a} >= {g_a}"


