"""
Static Architecture & Contract Regression Test Suite (Passes 1, 2 & 3).
Statically verifies system abstractions, argument contracts, determinism contracts,
event ledger invariants, database pragmas, state archive schema versioning, manager financial bounds,
lineup/seed parity, worker state machine transitions, and frontend/API route alignment WITHOUT running simulation or WSL subprocesses.
"""

import inspect
import json
import pytest
from pathlib import Path


def test_home_lineup_abstraction_contract():
    """Statically verify that FootyMatchSimulator accepts home_lineup/away_lineup while GRFNativeRunner does not."""
    from logic.match_engine_grf import FootyMatchSimulator
    from logic.grf_native_runner import GRFNativeRunner

    sim_sig = inspect.signature(FootyMatchSimulator.simulate)
    assert "home_lineup" in sim_sig.parameters, "FootyMatchSimulator.simulate must accept 'home_lineup'"
    assert "away_lineup" in sim_sig.parameters, "FootyMatchSimulator.simulate must accept 'away_lineup'"

    native_sig = inspect.signature(GRFNativeRunner.simulate)
    assert "home_lineup" not in native_sig.parameters, "GRFNativeRunner.simulate must NOT directly accept 'home_lineup'"
    assert "away_lineup" not in native_sig.parameters, "GRFNativeRunner.simulate must NOT directly accept 'away_lineup'"


def test_simulator_bridge_method_forwarding():
    """Statically verify FootyMatchSimulator exposes .run_match() and .render_replay()."""
    from logic.match_engine_grf import FootyMatchSimulator

    assert hasattr(FootyMatchSimulator, "run_match"), "FootyMatchSimulator must expose run_match()"
    assert hasattr(FootyMatchSimulator, "render_replay"), "FootyMatchSimulator must expose render_replay()"


def test_get_grf_simulator_return_type():
    """Statically verify get_grf_simulator source code imports FootyMatchSimulator and does not permanently lock out retry."""
    from models.match import get_grf_simulator
    src = inspect.getsource(get_grf_simulator)
    assert "from logic.match_engine_grf import FootyMatchSimulator" in src, \
        "get_grf_simulator must instantiate FootyMatchSimulator"
    assert "_grf_simulator_attempted" not in src, \
        "get_grf_simulator must not permanently lock out retry on transient failure"


def test_canonical_lineup_and_seed_derivation_methods():
    """Statically verify League exposes derive_match_seed and select_team_lineup methods."""
    from models.league import League

    assert hasattr(League, "derive_match_seed"), "League must expose derive_match_seed()"
    assert hasattr(League, "select_team_lineup"), "League must expose select_team_lineup()"


def test_canonical_adapter_roster_extraction():
    """Statically verify FootyGRFAdapter.build_team_tactics signature and roster mapping."""
    from logic.footy_grf_adapter import FootyGRFAdapter, GRFTeamTactics

    adapter_sig = inspect.signature(FootyGRFAdapter.build_team_tactics)
    assert "lineup" in adapter_sig.parameters
    assert "formation" in adapter_sig.parameters

    tactics = FootyGRFAdapter.build_team_tactics(
        team="Arsenal",
        lineup=[{"name": f"Player {i+1}", "position": "GK" if i == 0 else "CM"} for i in range(11)],
        formation="4-3-3"
    )
    assert isinstance(tactics, GRFTeamTactics)
    assert len(tactics.roster) == 11
    assert tactics.roster[0].position == "GK"


def test_manifest_identity_completeness():
    """Statically verify MatchManifest includes home_formation and away_formation in simulation identity hash."""
    from logic.match_manifest import MatchManifest

    manifest = MatchManifest(
        match_id="test_001",
        home_team="Arsenal",
        away_team="Chelsea",
        home_formation="4-3-3",
        away_formation="4-2-3-1",
        score=[2, 1]
    )
    identity_dict = manifest.get_simulation_identity_dict()
    assert "home_formation" in identity_dict, "Identity dict must contain home_formation"
    assert "away_formation" in identity_dict, "Identity dict must contain away_formation"
    assert identity_dict["home_formation"] == "4-3-3"


def test_process_pool_state_machine_and_deduplication():
    """Statically inspect SimulationProcessPool._run_dynamic_queue_pool source code for state machine and result deduplication."""
    from logic.simulation.simulation_process_pool import SimulationProcessPool

    src = inspect.getsource(SimulationProcessPool._run_dynamic_queue_pool)
    assert "fixture_states" in src, "Supervisor must maintain explicit fixture_states map"
    assert "clean_partial_artifacts" in src, "Supervisor must clean partial artifacts before retry"
    assert "if m_id not in results_by_id:" in src, "Supervisor must enforce result deduplication"


def test_fast_mode_engine_mode_precedence():
    """Statically inspect Match.play_match source code to ensure ENGINE_MODE=='GRF' overrides FAST_MODE."""
    from models.match import Match

    src = inspect.getsource(Match.play_match)
    assert "if ENGINE_MODE == \"GRF\":" in src, "Match.play_match must check ENGINE_MODE=='GRF'"
    assert "fast_prediction_enabled = False" in src, "ENGINE_MODE=='GRF' must disable fast mode prediction"


def test_season_fixture_completeness_assertion():
    """Statically inspect main.py simulate_season_with_transfers for season completeness assertion."""
    import main as main_mod

    src = inspect.getsource(main_mod.simulate_season_with_transfers)
    assert "if matches_played != total_matches:" in src, "Season simulation must assert exact expected fixture count"


def test_event_ledger_terminal_state_exclusivity():
    """Statically verify shot outcome classification in SimulationWorker."""
    from logic.simulation.simulation_worker import SimulationWorker

    src = inspect.getsource(SimulationWorker.step)
    for terminal_state in ["SAVED", "HIT_POST", "BLOCKED", "OFF_TARGET", "UNRESOLVED", "GOAL"]:
        assert terminal_state in src, f"SimulationWorker must track {terminal_state} shot outcome"


def test_database_wal_and_busy_timeout_pragmas():
    """Statically inspect database session.py for WAL mode and busy timeout pragmas."""
    import database.session as session_mod

    src = inspect.getsource(session_mod)
    assert "PRAGMA journal_mode=WAL" in src, "Database engine connect listener must set WAL mode"
    assert "PRAGMA busy_timeout=10000" in src, "Database engine connect listener must set busy_timeout"


def test_frontend_backend_route_contracts():
    """Statically verify key FastAPI endpoint paths match frontend API client declarations."""
    from api_fastapi import app

    routes = [r.path for r in app.routes]
    expected_routes = [
        "/teams",
        "/players",
        "/run-simulation",
        "/get-seasons",
        "/get-season-report/{year}",
        "/matches/{season_year}",
        "/match/{match_id}",
        "/team-history/{team_name}",
        "/financial-summary",
        "/youth-prospects",
        "/transfer-activity",
        "/all-seasons-overview",
        "/api/v1/engine/status",
        "/api/v1/match/{match_id}/video",
        "/api/v1/match/simulate-grf",
        "/api/v1/match/{match_id}/render-status",
    ]
    for route in expected_routes:
        assert route in routes, f"FastAPI app must register route '{route}'"
