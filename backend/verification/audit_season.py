"""Recompute season completeness, statistics and recording identity from disk."""
import json
import sys
import sqlite3
import hashlib
from pathlib import Path
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from logic.grf_trajectory import MatchTrajectory


def main(output, run_id):
    conn = sqlite3.connect(output / 'data/football_sim.db')
    conn.row_factory = sqlite3.Row
    matches = conn.execute('SELECT * FROM Match WHERE simulation_run_id=? ORDER BY match_number', (run_id,)).fetchall()
    teams = dict(conn.execute('SELECT team_id,name FROM Team'))
    run = dict(conn.execute('SELECT * FROM SimulationRun WHERE run_id=?', (run_id,)).fetchone())
    recordings = output / 'reports/recordings' / run_id
    failures = []
    table = {t: {'team': n, 'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'points': 0}
             for t, n in teams.items()}
    pairings = Counter((m['home_team_id'], m['away_team_id']) for m in matches)
    if len(matches) != 380 or len(pairings) != 380 or any(v != 1 for v in pairings.values()):
        failures.append(f'Fixture completeness: {len(matches)} matches, {len(pairings)} unique pairings')
    frames = 0
    native_goal_frames = 0
    expected_actor_hash = hashlib.sha256((ROOT / 'checkpoints/tikick/actor.pt').read_bytes()).hexdigest()
    for match in matches:
        identity = f"match_{match['season_year']}_{match['home_team_id']}_{match['away_team_id']}"
        try:
            traj = MatchTrajectory.load_from_npz(recordings / f'trace_{identity}.npz')
            assert traj.match_id == traj.manifest.match_id == identity
            assert traj.manifest.home_team == teams[match['home_team_id']]
            assert traj.manifest.away_team == teams[match['away_team_id']]
            assert list(traj.manifest.score) == [match['home_goals'], match['away_goals']]
            np.testing.assert_array_equal(traj.scores[-1], traj.manifest.score)
            assert traj.manifest.engine_fingerprint['match_complete'] is True
            assert traj.manifest.engine_fingerprint['native_steps_left'] == 0
            assert traj.total_steps == 3001
            policy = traj.manifest.engine_fingerprint['policy']
            assert policy['checkpoint_sha256'] == expected_actor_hash
            assert policy['builtin_ai_allowed'] is True
            assert policy['available_actions'] == 20 and policy['inference_profile'] == 'tikick_kaggle'
            assert np.all(traj.actions < 20)
            assert traj.manifest.engine_fingerprint['tactical_action_overrides'] is False
            audit = json.loads((recordings / f'trace_{identity}.audit.json').read_text())
            assert audit['passed'], audit.get('error')
            frames += audit['frames_compared']
            native_goal_frames += audit.get('native_goal_frames_checked', 0)
            assert audit['halftime_event_present']
            assert [e['type'] for e in traj.manifest.events].count('half_time') == 1
            assert [e['type'] for e in traj.manifest.events].count('full_time') == 1
            goals = [e for e in traj.manifest.events if e['type'] == 'goal']
            stored = conn.execute("SELECT COUNT(*) FROM MatchEvent WHERE match_id=? AND type='goal'", (match['match_id'],)).fetchone()[0]
            assert stored == len(goals)
            assert len(goals) == sum(traj.manifest.score)
            assert sum(e['type']=='shot' and e.get('team')=='home' for e in traj.manifest.events) == traj.manifest.shots[0]
            assert sum(e['type']=='shot' and e.get('team')=='away' for e in traj.manifest.events) == traj.manifest.shots[1]
        except Exception as exc:
            failures.append(f'{identity}: {exc}')
        h, a = table[match['home_team_id']], table[match['away_team_id']]
        hg, ag = match['home_goals'], match['away_goals']
        for t, gf, ga in ((h, hg, ag), (a, ag, hg)):
            t['played'] += 1
            t['gf'] += gf
            t['ga'] += ga
            if gf > ga:
                t['won'] += 1
                t['points'] += 3
            elif gf == ga:
                t['drawn'] += 1
                t['points'] += 1
            else:
                t['lost'] += 1
    report_path = output / 'reports/season_reports/season_report_2026.json'
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding='utf-8'))
        published = {name: stats for name, stats in report['table']}
        for t in table.values():
            if t['played'] != 38:
                failures.append(f"{t['team']} played {t['played']} fixtures")
            row = published.get(t['team'], {})
            for key in ('played', 'won', 'drawn', 'lost', 'gf', 'ga', 'points'):
                if row.get(key) != t[key]:
                    failures.append(f"Standings mismatch: {t['team']} {key}: {row.get(key)} != {t[key]}")
    else:
        failures.append('Final season report missing')
    if run['status'] != 'completed':
        failures.append('Run did not complete: ' + run['status'])
    if run['matches_played'] != len(matches):
        failures.append(f"Run counter {run['matches_played']} differs from {len(matches)} saved fixtures")
    standings = sorted(table.values(), key=lambda t: (t['points'], t['gf'] - t['ga'], t['gf']), reverse=True)
    result = {'passed': not failures, 'run_id': run_id, 'matches': len(matches), 'native_replay_frames_compared': frames,
              'actor_checkpoint_sha256': expected_actor_hash, 'native_goal_frames_compared': native_goal_frames,
              'failures': failures, 'standings': standings}
    (output / 'season_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    latest = json.loads((ROOT / 'verification/latest.json').read_text())
    main(Path(latest['output']), latest['run_id'])
