import asyncio
import json
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from database import jobs
from database.migrations import upgrade_database
from database.models import Base, SimulationRun, WorkJob
from logic.grf_state_archive import GRFStateArchiveReader, GRFStateArchiveWriter, ReplayIntegrityError
from logic.safe_paths import contained_path


@pytest.fixture
def job_database(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "jobs.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)

    @contextmanager
    def session():
        with factory() as db:
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    monkeypatch.setattr(jobs, 'get_db_session', session)
    yield session
    engine.dispose()


def simulation_payload():
    return {'season_year': 2026, 'render_mode': '2d', 'total_matches': 380}


def test_empty_and_unversioned_schema_upgrade_preserves_data(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "migration.db"}')
    upgrade_database(engine)
    with engine.begin() as db:
        assert db.exec_driver_sql('PRAGMA integrity_check').scalar() == 'ok'
        assert db.exec_driver_sql('PRAGMA foreign_key_check').fetchall() == []
        assert db.exec_driver_sql('SELECT version_num FROM alembic_version').scalar() == 'b20261013'
        db.exec_driver_sql("INSERT INTO League(name,season_year) VALUES ('Saved league',2026)")
        db.exec_driver_sql('DROP TABLE alembic_version')
    upgrade_database(engine)
    with engine.connect() as db:
        assert db.exec_driver_sql('SELECT name FROM League').scalar() == 'Saved league'
    engine.dispose()


def test_legacy_revision_upgrade_preserves_reports(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "legacy.db"}')
    # A representative metadata-created, old stamped installation.
    Base.metadata.create_all(engine)
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)')
        db.exec_driver_sql("INSERT INTO alembic_version VALUES ('879f4c01467a')")
        db.exec_driver_sql("INSERT INTO SeasonReport(season_year,champion_team,report_data,created_at) VALUES (2025,'Arsenal','{}','2025-01-01')")
    upgrade_database(engine)
    with engine.connect() as db:
        assert db.exec_driver_sql('SELECT champion_team FROM SeasonReport').scalar() == 'Arsenal'
        assert db.exec_driver_sql('PRAGMA foreign_key_check').fetchall() == []
    engine.dispose()


def test_durable_acceptance_idempotency_and_exclusion(job_database):
    accepted = jobs.submit_job('simulation', simulation_payload(), 'same-request')
    assert accepted['status'] == 'queued'
    with job_database() as db:
        assert db.get(SimulationRun, accepted['run_id']).status == 'queued'
    assert jobs.submit_job('simulation', simulation_payload(), 'same-request')['job_id'] == accepted['job_id']
    with pytest.raises(jobs.JobBusyError):
        jobs.submit_job('simulation', simulation_payload())
    with pytest.raises(ValueError):
        jobs.submit_job('simulation', {**simulation_payload(), 'season_year': 2027}, 'same-request')


def test_two_process_owners_cannot_claim_same_job(job_database):
    job = jobs.submit_job('simulation', simulation_payload())
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda owner: jobs.claim_job(job['job_id'], owner), ['owner-a', 'owner-b']))
    assert sum(claim is not None for claim in claims) == 1
    owner = 'owner-a' if claims[0] else 'owner-b'
    assert not jobs.finish_job(job['job_id'], 'not-the-owner', 'completed')
    assert jobs.heartbeat(job['job_id'], owner)
    assert jobs.finish_job(job['job_id'], owner, 'completed', {'verified': True})
    assert jobs.get_job(job['job_id'])['result'] == {'verified': True}


def test_cancel_and_expired_lease_survive_restart(job_database):
    job = jobs.submit_job('simulation', simulation_payload())
    assert jobs.cancel_job(job['job_id'])['status'] == 'cancelled'
    assert jobs.claim_job(job['job_id'], 'owner') is None
    next_job = jobs.submit_job('simulation', simulation_payload())
    jobs.claim_job(next_job['job_id'], 'gone-worker')
    with job_database() as db:
        db.get(WorkJob, next_job['job_id']).lease_until = time.time() - 10
    assert jobs.reconcile_expired() == 1
    assert jobs.get_job(next_job['job_id'])['status'] == 'interrupted'
    assert not jobs.finish_job(next_job['job_id'], 'gone-worker', 'completed')


def test_simulation_api_returns_committed_id_and_cancel_contract(job_database, monkeypatch):
    import api_fastapi
    from database import db_setup
    monkeypatch.setattr(db_setup, 'create_tables', lambda: None)

    async def keep_queued(job_id):
        pass

    monkeypatch.setattr(api_fastapi, 'run_simulation_task', keep_queued)
    client = TestClient(api_fastapi.app)
    response = client.post('/api/v1/run-simulation', json={'render_mode': '2d'}, headers={'Idempotency-Key': 'api-request'})
    assert response.status_code == 202
    accepted = response.json()
    status = client.get(accepted['status_url']).json()
    assert status['status'] == 'queued' and status['run_id'] == accepted['run_id']
    assert client.post('/api/v1/run-simulation').status_code == 409
    assert client.post(accepted['status_url'] + '/cancel').json()['status'] == 'cancelled'
    assert client.get('/api/v1/jobs/missing').status_code == 404


@pytest.mark.parametrize('path', ['../secret', '%2e%2e/secret', '%252e%252e/secret', 'C:\\secret', '//server/share', '/etc/passwd', 'nested/../../secret'])
def test_artifact_containment_rejects_escapes(tmp_path, path):
    with pytest.raises(ValueError):
        contained_path(tmp_path, path)


def test_artifact_containment_accepts_nested_recording(tmp_path):
    assert contained_path(tmp_path, 'run_abc/match.mp4') == tmp_path / 'run_abc' / 'match.mp4'


def test_new_archive_roundtrip_and_unknown_pickle_rejection(tmp_path):
    target = tmp_path / 'states.grfstate'
    states = [b'state-0', b'state-1', b'state-2']
    with GRFStateArchiveWriter(str(target), 'test', chunk_size=2) as writer:
        for state in states:
            writer.append(state)
    with GRFStateArchiveReader(str(target)) as reader:
        assert reader.version == 3
        reader.validate(expected_steps=3, check_global_sha=True)
        assert reader.extract_all() == states
        assert reader.get_state(2) == states[2]
    target.write_bytes(pickle.dumps(states))
    with pytest.raises(ReplayIntegrityError):
        GRFStateArchiveReader(str(target))
    with GRFStateArchiveReader(str(target), trusted_legacy=True) as reader:
        assert reader.extract_all() == states


def test_pickle_payload_cannot_execute_even_in_legacy_converter(tmp_path):
    class Executable:
        def __reduce__(self):
            return eval, ('1 + 1',)
    target = tmp_path / 'malicious.pkl'
    target.write_bytes(pickle.dumps([Executable()]))
    with pytest.raises(ReplayIntegrityError, match='Executable pickle'):
        GRFStateArchiveReader(str(target), trusted_legacy=True)


def test_v1_byte_only_chunks_can_be_converted_without_executable_loading(tmp_path):
    import zlib
    from logic.grf_state_archive import MAGIC_HEADER_V1
    states = [b'old-state-one', b'old-state-two']
    compressed = zlib.compress(pickle.dumps(states))
    offset = len(MAGIC_HEADER_V1) + 8192
    header = {'version': 1, 'match_id': 'old', 'total_steps': 2, 'chunk_size': 2,
              'chunk_offsets': [[offset, len(compressed), 2]]}
    old = tmp_path / 'old.grfstate'
    old.write_bytes(MAGIC_HEADER_V1 + json.dumps(header).encode().ljust(8192, b' ') + compressed)
    converted = tmp_path / 'converted.grfstate'
    with GRFStateArchiveReader(str(old), trusted_legacy=True) as reader:
        with GRFStateArchiveWriter(str(converted), 'old') as writer:
            for state in reader.iter_states():
                writer.append(state)
    with GRFStateArchiveReader(str(converted)) as reader:
        reader.validate(expected_steps=2, check_global_sha=True)
        assert reader.extract_all() == states


def test_masks_for_exploration_and_greedy_selection():
    from ml.dqn_agent import DQNAgent
    from ml.footy_env import FootyEnv
    env = FootyEnv(num_teams=6, season_length=2, fast_mode=True)
    observation, _ = env.reset(seed=42)
    env.budget = 0
    mask = env.get_action_mask()
    assert mask[2] == mask[3] == mask[4] == 0
    agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim)
    for epsilon in (0.0, 1.0):
        for _ in range(100):
            action = agent.select_action(observation, action_mask=mask, training=True, epsilon=epsilon)
            assert mask[action] > 0.5
    env.close()


def test_seeded_rule_based_episode_reproducibility():
    from ml.footy_env import FootyEnv
    from ml.train_rl import run_episode
    a = run_episode(FootyEnv(num_teams=6, season_length=4, fast_mode=True), policy='rule_based', seed=123)
    b = run_episode(FootyEnv(num_teams=6, season_length=4, fast_mode=True), policy='rule_based', seed=123)
    assert a == b
