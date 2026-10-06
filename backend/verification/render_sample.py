import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
latest = json.loads((ROOT / 'verification/latest.json').read_text())
output = Path(latest['output'])
os.environ['FOOTY_DATA_DIR'] = str(output / 'data')
os.environ['FOOTY_REPORTS_DIR'] = str(output / 'reports')
sys.path.insert(0, str(ROOT / 'src'))

if __name__ == '__main__':
    from database.match_db import get_match_details
    from logic.grf_native_runner import GRFNativeRunner, to_win_path
    details = get_match_details(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    trace = to_win_path(details['trace_file'])
    from logic.grf_trajectory import MatchTrajectory
    trajectory = MatchTrajectory.load_from_npz(trace)
    result = GRFNativeRunner().render_replay(
        match_id=trajectory.match_id, home_team=trajectory.manifest.home_team,
        away_team=trajectory.manifest.away_team, trajectory_file=str(trace),
        states_file=str(trace.with_suffix('.grfstate')),
        output_mp4=str(trace.parent / f'match_{trajectory.match_id}_native_3d.mp4'), mode='3d', force='--force' in sys.argv)
    (output / f'render_{details["match_id"]}.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
