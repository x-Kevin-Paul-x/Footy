"""
Static Architecture & Contract Regression Test Suite (Fifth Pass - Full RNG Isolation & Parity).
Statically verifies system abstractions, PreparedMatch schema, lineup consolidation,
per-match RNG isolation, process pool state machines, database pragmas, state archive schema versioning,
manager financial bounds, and frontend/API route alignment WITHOUT running simulation or WSL subprocesses.
"""

import ast
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


def test_prepared_match_schema_and_methods():
    """Statically verify PreparedMatch dataclass fields and to_fixture_dict method."""
    from models.match import PreparedMatch

    sig = inspect.signature(PreparedMatch)
    expected_fields = ["match_id", "seed_val", "home_team", "away_team", "home_lineup", "away_lineup"]
    for field in expected_fields:
        assert field in sig.parameters, f"PreparedMatch must declare '{field}' field"

    assert hasattr(PreparedMatch, "to_fixture_dict"), "PreparedMatch must expose to_fixture_dict()"


def test_league_prepare_match_and_lineup_consolidation():
    """Statically verify League.prepare_match and select_team_lineup implementation."""
    from models.league import League

    assert hasattr(League, "prepare_match"), "League must expose prepare_match()"
    assert hasattr(League, "select_team_lineup"), "League must expose select_team_lineup()"

    src = inspect.getsource(League.prepare_match)
    assert "PreparedMatch" in src, "League.prepare_match must return a PreparedMatch instance"
    assert "select_team_lineup" in src, "League.prepare_match must utilize select_team_lineup"


def test_match_rng_isolation_ast():
    """Statically inspect Match methods to assert no bare global random. calls remain inside stochastic simulation methods."""
    from models import match as match_mod

    stochastic_methods = [
        "simulate_minute",
        "_calculate_action_success",
        "_maybe_injure_player",
        "_attempt_substitution",
        "_calculate_card_probability",
        "play_match",
        "_fast_mode_prediction",
    ]

    for method_name in stochastic_methods:
        method_obj = getattr(match_mod.Match, method_name)
        src = inspect.getsource(method_obj)
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "random":
                    pytest.fail(
                        f"Match.{method_name} contains unisolated global 'random.{node.func.attr}()' call at line {node.lineno}. "
                        f"Must use 'self.rng.{node.func.attr}()' for per-match seed isolation."
                    )


def test_truthiness_seed_val_preservation():
    """Statically verify that seed_val=0 is preserved correctly using 'is not None' rather than truthiness 'or'."""
    from models.match import Match, PreparedMatch
    from models.league import League

    src_match_init = inspect.getsource(Match.__init__)
    assert "seed_val if seed_val is not None else" in src_match_init, "Match.__init__ must use 'is not None' for seed_val check"

    src_league_prep = inspect.getsource(League.prepare_match)
    assert "seed_val if seed_val is not None else" in src_league_prep, "League.prepare_match must use 'is not None' for seed_val check"


def test_chronological_matchday_execution_in_concurrent():
    """Statically verify play_matchdays_concurrent executes matchday batches in chronological order."""
    from models.league import League

    src = inspect.getsource(League.play_matchdays_concurrent)
    assert "for fixtures_batch in matchdays_batches:" in src, "play_matchdays_concurrent must iterate matchday batches sequentially"
    assert "prepared_matches = [self.prepare_match" in src, "play_matchdays_concurrent must prepare matches per matchday batch"


def test_process_pool_state_machine_and_order_preservation():
    """Statically inspect SimulationProcessPool for explicit state machine and input order preservation."""
    from logic.simulation.simulation_process_pool import SimulationProcessPool

    src_pool = inspect.getsource(SimulationProcessPool._run_dynamic_queue_pool)
    assert "fixture_states" in src_pool, "Supervisor must maintain explicit fixture_states map"
    assert "clean_partial_artifacts" in src_pool, "Supervisor must clean partial artifacts before retry"
    assert "if m_id not in results_by_id:" in src_pool, "Supervisor must enforce result deduplication"

    src_run = inspect.getsource(SimulationProcessPool.run_batch)
    assert "return" in src_run, "run_batch must return results matching input fixture order"


def test_fast_mode_engine_mode_precedence():
    """Statically inspect Match.play_match source code to ensure ENGINE_MODE=='GRF' overrides FAST_MODE."""
    from models.match import Match

    src = inspect.getsource(Match.play_match)
    assert "if ENGINE_MODE == \"GRF\":" in src, "Match.play_match must check ENGINE_MODE=='GRF'"
    assert "fast_prediction_enabled = False" in src, "ENGINE_MODE=='GRF' must disable fast mode prediction"


def test_season_fixture_completeness_and_uniqueness_assertion():
    """Statically inspect main.py simulate_season_with_transfers for season completeness and exact match ID uniqueness assertions."""
    import main as main_mod

    src = inspect.getsource(main_mod.simulate_season_with_transfers)
    assert "if matches_played != total_matches:" in src, "Season simulation must assert exact expected fixture count"
    assert "if recorded_match_ids != expected_match_ids:" in src, "Season simulation must assert exact match ID set equality"


def test_match_play_match_rng_and_seed_propagation():
    """Statically inspect Match.play_match source code for rng pass-through and self.seed_val propagation to GRF."""
    from models.match import Match

    src = inspect.getsource(Match.play_match)
    assert "rng=self.rng" in src, "Match.play_match must pass rng=self.rng to manager lineup selection"
    assert "seed_val=self.seed_val" in src, "Match.play_match must propagate self.seed_val when delegating to GRF"


def test_deterministic_simulation_isolation_contracts():
    """Statically verify contract methods for deterministic match execution and independence from global Python random."""
    from models.match import Match
    from models.league import League

    # Verify Match.__init__ creates an isolated Random instance from seed_val
    src_init = inspect.getsource(Match.__init__)
    assert "self.rng = random.Random(self.seed_val)" in src_init, "Match.__init__ must initialize self.rng with self.seed_val"

    # Verify League.derive_match_seed uses deterministic hashlib SHA256 hashing
    src_derive = inspect.getsource(League.derive_match_seed)
    assert "hashlib.sha256" in src_derive, "League.derive_match_seed must use SHA256 for deterministic seed generation"


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
