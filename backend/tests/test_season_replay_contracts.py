from types import SimpleNamespace

import pytest


def test_completion_counts_saved_fixtures_instead_of_halftime_progress(monkeypatch):
    from contextlib import contextmanager
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from database.models import Base, SimulationRun, Match
    from database.db_setup import complete_simulation_run
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for run_id in ('current', 'other'):
            db.add(SimulationRun(run_id=run_id, season_year=2026, created_at='now',
                                 status='running', matches_played=190, total_matches=380, render_mode='3d'))
        for run_id, number in [('current', 1), ('current', 2), ('other', 1)]:
            db.add(Match(simulation_run_id=run_id, match_number=number, date='now',
                         season_year=2026, home_team_id=1, away_team_id=2,
                         home_possession=50, away_possession=50, weather='clear', intensity='normal'))
        db.commit()

    @contextmanager
    def session_scope():
        with Session(engine) as db:
            yield db
            db.commit()

    monkeypatch.setattr('database.session.get_db_session', session_scope)
    complete_simulation_run('current')
    with Session(engine) as db:
        current = db.get(SimulationRun, 'current')
        assert current.matches_played == 2
        assert current.status == 'completed'
        assert db.get(SimulationRun, 'other').matches_played == 190


def test_cutoff_cannot_claim_full_time(monkeypatch):
    from logic.simulation import match_executor as module
    monkeypatch.setattr(module, 'football_env', None)
    worker = module.GRFMatchExecutor({'match_id': 'short'}, max_steps=1200, replay_mode=module.ReplayMode.NONE)
    worker.step_idx = 1200
    worker.raw_obs = [{'steps_left': 1801}]
    result = worker.finalize()
    assert result.match_complete is False
    assert result.events[-1]['type'] == 'simulation_stopped'
    assert result.events[-1]['minute'] < 45
    assert not any(e['type'] in ('half_time', 'full_time') for e in result.events)


def test_full_time_requires_native_terminal_state(monkeypatch):
    from logic.simulation import match_executor as module
    monkeypatch.setattr(module, 'football_env', None)
    worker = module.GRFMatchExecutor({'match_id': 'complete'}, replay_mode=module.ReplayMode.NONE)
    worker.step_idx = 3001
    worker.done = True
    worker.raw_obs = [{'steps_left': 0}]
    result = worker.finalize()
    assert result.match_complete is True
    assert result.events[-1]['type'] == 'full_time'
    assert result.total_steps == 3001


def test_shuffled_results_follow_fixture_identity():
    from models.league import League
    prepared = [SimpleNamespace(match_id=str(i), home_team=SimpleNamespace(name=f'H{i}'),
                                away_team=SimpleNamespace(name=f'A{i}')) for i in (1, 2)]
    results = [{'match_id': str(i), 'home_team': f'H{i}', 'away_team': f'A{i}',
                'match_complete': True} for i in (2, 1)]
    ordered = League._validated_batch_results(prepared, results)
    assert [r['match_id'] for r in ordered] == ['1', '2']
    with pytest.raises(RuntimeError, match='duplicate'):
        League._validated_batch_results(prepared, [results[0], results[0]])
    with pytest.raises(RuntimeError, match='Missing'):
        League._validated_batch_results(prepared, results[:1])
    results[0]['match_complete'] = False
    with pytest.raises(RuntimeError, match='full time'):
        League._validated_batch_results(prepared, results)


def test_persistence_rejects_incomplete_match():
    from database.match_db import save_match_to_db
    with pytest.raises(ValueError, match='incomplete'):
        save_match_to_db({'match_complete': False}, 2026, 1)


def test_spec_step_budget_is_not_overridden_by_worker_default():
    from logic.simulation.simulation_worker import SimulationWorker, SimulationSpec, ReplayMode
    spec = SimulationSpec(match_id='explicit_budget', max_steps=75, replay_mode=ReplayMode.NONE)
    import inspect
    assert inspect.signature(SimulationWorker).parameters['max_steps'].default is None
    assert spec.max_steps == 75


def test_away_observations_use_grf_canonical_perspective(monkeypatch):
    import numpy as np
    from logic.simulation import match_executor as module
    monkeypatch.setattr(module, 'football_env', None)
    worker = module.GRFMatchExecutor({'match_id': 'perspective'}, replay_mode=module.ReplayMode.NONE)
    worker.raw_obs = [{'side': 'home'}] * 10 + [{'side': 'away'}] * 10
    calls = []
    def extract(observations, team_side, **kwargs):
        calls.append((observations[0]['side'], team_side))
        return np.zeros((10, 268)), np.zeros(11), np.zeros(11)
    monkeypatch.setattr(module, 'extract_canonical_features', extract)
    worker.get_initial_observations()
    assert calls == [('home', 'left'), ('away', 'left')]


def test_native_goal_frames_shift_video_seeking():
    from logic.presentation_timeline import build_canonical_timeline
    events = [{'type': 'half_time', 'step': 1523}, {'type': 'goal', 'step': 2000}]
    timeline = build_canonical_timeline('native', 3001, events, fps=10,
        intro_frames=30, halftime_frames=30, fulltime_frames=40,
        goal_hold_frames=0, goal_replay_frames=0, native_duration=3000,
        native_goal_frames={2000: 2})
    assert timeline.total_frames == 3103
    assert timeline.seek_event('step_2000') == 206.0
    halftime = next(s for s in timeline.segments if s.segment_type == 'halftime')
    assert halftime.source_step_start == 1523


def test_restored_native_frame_redraws_without_stepping():
    from logic.replay.grf_render_runtime import render_restored_native_frame
    class Native:
        game_config = SimpleNamespace(render=True)
        framebuffer = 'stale kickoff picture'
        def render(self, swap):
            self.framebuffer = 'restored ball crossing the goal line'
        def step(self):
            raise AssertionError('Rendering must not step physics')
    native = Native()
    core = SimpleNamespace(_env=native, cached='stale kickoff picture')
    core._retrieve_observation = lambda: setattr(core, 'cached', native.framebuffer)
    env = SimpleNamespace(unwrapped=SimpleNamespace(_env=core), render=lambda mode: core.cached)
    assert render_restored_native_frame(env) == 'restored ball crossing the goal line'


def test_actor_actions_are_preserved_unless_tactical_overrides_are_requested():
    from logic.simulation.match_executor import SimulationSpec
    assert SimulationSpec.from_dict({'match_id': 'native_actor'}).apply_tactical_bias is False
    assert SimulationSpec.from_dict({
        'match_id': 'manager_overrides', 'apply_tactical_bias': True,
    }).apply_tactical_bias is True


def test_stale_or_wrong_match_video_is_not_reused(monkeypatch, tmp_path):
    import json
    import api_fastapi
    monkeypatch.setattr(api_fastapi, 'RECORDINGS_DIR', tmp_path)
    video = tmp_path / 'run/fixture_3d.mp4'
    video.parent.mkdir()
    video.write_bytes(b'\x00\x00\x00\x0cftypisom\x00\x00\x00\x08moov')
    monkeypatch.setattr(api_fastapi, 'get_match_details', lambda _: {
        'video_url': '/recordings/run/fixture_3d.mp4', 'trace_file': 'run/trace_fixture.npz'})
    assert api_fastapi.find_match_video_and_url('fixture') == (None, None)
    sidecar = video.with_suffix('.timeline.json')
    sidecar.write_text(json.dumps({'native_redraw': True, 'match_id': 'another_fixture'}))
    assert api_fastapi.find_match_video_and_url('fixture') == (None, None)
    sidecar.write_text(json.dumps({'native_redraw': True, 'match_id': 'fixture'}))
    assert api_fastapi.find_match_video_and_url('fixture')[0] == video.resolve()
