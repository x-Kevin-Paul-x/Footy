"""Render the corrected actor's original match for the local season viewer."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / 'verification/season_20261004_001100'
os.environ['FOOTY_REPORTS_DIR'] = str(output / 'reports')
sys.path.insert(0, str(root / 'src'))
from logic.grf_native_runner import GRFNativeRunner
from logic.grf_trajectory import MatchTrajectory

trace = output / 'actor_comparison/trace_tikick_kaggle.npz'
trajectory = MatchTrajectory.load_from_npz(trace)
video = output / 'reports/recordings/tikick_policy_comparison/match_tikick_kaggle_3d.mp4'
video.parent.mkdir(exist_ok=True)
result = GRFNativeRunner().render_replay(match_id=trajectory.match_id,
    home_team=trajectory.manifest.home_team, away_team=trajectory.manifest.away_team,
    trajectory_file=str(trace), states_file=str(trace.with_suffix('.grfstate')),
    output_mp4=str(video), mode='3d', force=True)
(output / 'actor_comparison/render.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
