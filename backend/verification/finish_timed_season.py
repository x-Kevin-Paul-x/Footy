"""Wait for the isolated season, then time its audits and a native 3D replay."""
import datetime
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent
latest = json.loads((root / 'latest.json').read_text())
output = Path(latest['output'])
results = {'run_id': latest['run_id'], 'phase': 'waiting_for_season', 'audit_workers': 10}

def save():
    (output / 'completion_timing.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results), flush=True)

def wsl_path(path):
    value = str(path.resolve()).replace('\\', '/')
    return '/mnt/' + value[0].lower() + value[2:]

save()
while True:
    with sqlite3.connect(f'file:{output / "data/football_sim.db"}?mode=ro', uri=True) as db:
        status = db.execute('SELECT status FROM SimulationRun WHERE run_id=?', (latest['run_id'],)).fetchone()[0]
    if status == 'completed':
        break
    if status not in ('running', 'cancelling'):
        raise RuntimeError('Season stopped: ' + status)
    time.sleep(5)

results['phase'] = 'checking_native_states'
results['verification_started_at'] = datetime.datetime.now().astimezone().isoformat()
save()
started = time.perf_counter()
with (output / 'native_audit.log').open('w', encoding='utf-8') as log:
    subprocess.run(['wsl', '-u', 'root', '/root/venv_baller/bin/python3',
                    wsl_path(root / 'audit_native_replays.py'),
                    wsl_path(output / 'reports/recordings' / latest['run_id']),
                    '380', '--workers', '10'], stdout=log, stderr=subprocess.STDOUT, check=True)
results['native_state_audit_seconds'] = round(time.perf_counter() - started, 3)
results['phase'] = 'checking_season_and_squads'
save()
for name, report in [('audit_season.py', 'season_audit.json'), ('audit_squad_data.py', 'squad_audit.json')]:
    with (output / (name + '.log')).open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, str(root / name)], stdout=log, stderr=subprocess.STDOUT, check=True)
    data = json.loads((output / report).read_text())
    if not data['passed']:
        results['phase'] = 'verification_failed'
        results['failed_report'] = report
        save()
        raise RuntimeError(report + ': ' + str(data['failures']))
results['verification_wall_seconds'] = round(time.perf_counter() - started, 3)
results['phase'] = 'rendering_saved_native_replay'
save()
render_started = time.perf_counter()
with (output / 'render_sample.log').open('w', encoding='utf-8') as log:
    subprocess.run([sys.executable, str(root / 'render_sample.py'), '1'], stdout=log, stderr=subprocess.STDOUT, check=True)
results['sample_3d_render_seconds'] = round(time.perf_counter() - render_started, 3)
results['sample_match_id'] = 1
results['finished_at'] = datetime.datetime.now().astimezone().isoformat()
results['phase'] = 'complete'
save()
