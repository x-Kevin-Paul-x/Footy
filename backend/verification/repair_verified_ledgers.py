"""Recover omitted interval metadata only from independently verified states.

Keep original trajectories and a provenance log. Never change physics arrays,
scores, goals, seeds or native state archives. Used for early fixtures produced
while the halftime observer fix was being verified during this audit.
"""
import os
import sys
import json
import shutil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
latest = json.loads((ROOT / 'verification/latest.json').read_text())
output = Path(latest['output'])
os.environ['FOOTY_DATA_DIR'] = str(output / 'data')
os.environ['FOOTY_REPORTS_DIR'] = str(output / 'reports')
sys.path.insert(0, str(ROOT / 'src'))
from logic.grf_trajectory import MatchTrajectory
from logic.match_manifest import compute_file_sha256
from database.session import get_db_session
from database.models import Match, MatchEvent


if __name__ == '__main__':
    recordings = output / 'reports/recordings' / latest['run_id']
    provenance = []
    for path in sorted(recordings.glob('*.npz')):
        audit = json.loads(path.with_suffix('.audit.json').read_text())
        assert audit['passed'], f'Cannot repair unverified recording: {path.name}'
        traj = MatchTrajectory.load_from_npz(path)
        if not any(e['type'] == 'half_time' for e in traj.manifest.events):
            step = audit['native_half_restart_frame']
            assert np.linalg.norm(traj.ball_coords[step, :2]) < 1e-6
            np.testing.assert_array_equal(traj.scores[step], traj.scores[step - 1])
            original_sha = compute_file_sha256(str(path))
            backup = recordings / 'before_ledger_repair' / path.name
            backup.parent.mkdir(exist_ok=True)
            if not backup.exists():
                shutil.copy2(path, backup)
            score = traj.scores[step]
            traj.manifest.events.append({'minute': 45, 'step': step, 'type': 'half_time',
                                         'score': f'{score[0]}-{score[1]}',
                                         'source': 'verified_native_state_recovery'})
            traj.manifest.events.sort(key=lambda e: int(e['step']))
            traj.save_to_npz(path)
            original = MatchTrajectory.load_from_npz(backup)
            for field in ('player_coords', 'player_dirs', 'ball_coords', 'ball_dirs', 'actions', 'scores',
                          'game_mode', 'ball_owned_team', 'ball_owned_player'):
                np.testing.assert_array_equal(getattr(original, field), getattr(traj, field))
            provenance.append({'match_id': traj.match_id, 'original_sha256': original_sha,
                               'corrected_sha256': compute_file_sha256(str(path)), 'backup': str(backup),
                               'source_frame': step, 'physics_arrays_unchanged': True})
            audit['halftime_event_present'] = True
            audit['metadata_recovered_from_verified_native_state'] = True
            path.with_suffix('.audit.json').write_text(json.dumps(audit, indent=2))
        # Preserve exact canonical metadata in the existing text column without
        # touching lineup/bench metadata, standings or fixture identity.
        with get_db_session() as db:
            _, year, home, away = traj.match_id.split('_')
            match = db.query(Match).filter(Match.simulation_run_id == latest['run_id'],
                                          Match.season_year == int(year), Match.home_team_id == int(home),
                                          Match.away_team_id == int(away)).one()
            reserved = ('home_lineup', 'away_lineup', 'home_bench', 'away_bench', 'substitutions')
            db.query(MatchEvent).filter(MatchEvent.match_id == match.match_id,
                                       ~MatchEvent.type.in_(reserved)).delete(synchronize_session=False)
            for event in traj.manifest.events:
                db.add(MatchEvent(match_id=match.match_id, minute=event['minute'], type=event['type'],
                                  player=event.get('player', 'Unknown'), team=event.get('team', 'home'),
                                  details=json.dumps({'canonical_event': event})))
    (output / 'ledger_repair_provenance.json').write_text(json.dumps(provenance, indent=2))
    print(f'Recovered halftime metadata for {len(provenance)} verified recordings; physics unchanged.')
