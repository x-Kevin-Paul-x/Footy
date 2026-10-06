"""Exercise actual saved fixtures through the replay APIs in the isolated run."""
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
from fastapi.testclient import TestClient
from api_fastapi import app
from database.match_db import get_match_details
from logic.grf_trajectory import MatchTrajectory
from logic.grf_native_runner import to_win_path

with TestClient(app) as client:
    for row_id in (1, 10):
        details = get_match_details(row_id)
        trajectory = MatchTrajectory.load_from_npz(to_win_path(details['trace_file']))
        fixture = trajectory.match_id
        for identity in (str(row_id), fixture):
            response = client.get(f'/api/v1/match/{identity}/timeline')
            assert response.status_code == 200, response.text
            timeline = response.json()
            assert timeline['match_id'] == fixture
            assert timeline['total_frames'] >= 3101
            metadata = client.get(f'/api/v1/match/{identity}/video').json()
            if metadata['available']:
                assert latest['run_id'] in metadata['video_url']
                status = client.get(f'/api/v1/match/{identity}/render-status').json()
                assert status['video_url'] == metadata['video_url'] and status['completed']
    print('API_RECORDING_IDENTITY_AND_TIMELINE_PASSED', flush=True)
