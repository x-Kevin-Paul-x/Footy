"""Run and time an isolated season, pruning previous verification recordings."""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

root = Path(__file__).resolve().parents[1]
output = root / 'verification' / ('season_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
output.mkdir(parents=True)
os.environ['FOOTY_DATA_DIR'] = str(output / 'data')
os.environ['FOOTY_REPORTS_DIR'] = str(output / 'reports')
os.environ['FOOTY_ENGINE_MODE'] = 'GRF'
os.environ['FOOTY_NUM_SEASONS'] = '1'
os.environ['FOOTY_GRF_MAX_STEPS'] = '3200'
os.environ['FOOTY_MAX_MATCHES'] = '0'
os.environ['FOOTY_SYNC_VIDEO_RENDER'] = '0'
sys.path.insert(0, str(root / 'src'))

if __name__ == '__main__':
    started = time.perf_counter()
    timing = {'started_at': datetime.now().astimezone().isoformat(), 'batches': []}
    from database.db_setup import init_simulation_run, clean_old_simulation_data
    from main import main
    from logic.grf_batch_runner import GRFBatchRunner
    original_batch = GRFBatchRunner.run_matchday

    def timed_batch(self, fixtures, *args, **kwargs):
        batch_started = time.perf_counter()
        result = original_batch(self, fixtures, *args, **kwargs)
        timing['batches'].append({'matches': len(fixtures),
                                 'seconds': round(time.perf_counter() - batch_started, 3)})
        (output / 'timing.json').write_text(json.dumps(timing, indent=2))
        return result

    GRFBatchRunner.run_matchday = timed_batch
    run_id = init_simulation_run(render_mode='3d')
    # Isolated timed runs have separate report roots; apply the same retention
    # policy to their predecessors without deleting audit evidence or databases.
    for previous in (root / 'verification').glob('season_*'):
        if previous.resolve() == output.resolve() or not previous.is_dir():
            continue
        recordings = previous / 'reports' / 'recordings'
        if previous.is_symlink() or previous.resolve().parent != (root / 'verification').resolve():
            raise ValueError(f'Unsafe previous verification directory: {previous}')
        if recordings.is_symlink() or not recordings.resolve().is_relative_to(previous.resolve()):
            raise ValueError(f'Unsafe previous recordings directory: {recordings}')
        clean_old_simulation_data(recordings_dir=recordings)
    (root / 'verification' / 'latest.json').write_text(json.dumps({'output': str(output), 'run_id': run_id}, indent=2))
    print('VERIFICATION_OUTPUT=' + str(output), flush=True)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    with (output / 'season.log').open('w', encoding='utf-8', buffering=1) as log:
        import logging
        handler = logging.StreamHandler(log)
        logging.getLogger().addHandler(handler)
        sys.stdout = log
        sys.stderr = log
        try:
            main(run_id=run_id, render_mode='3d')
        except Exception:
            import traceback
            traceback.print_exc(file=log)
            raise
        finally:
            timing['finished_at'] = datetime.now().astimezone().isoformat()
            timing['season_wall_seconds'] = round(time.perf_counter() - started, 3)
            timing['match_batch_wall_seconds'] = round(sum(b['seconds'] for b in timing['batches']), 3)
            timing['matches_simulated'] = sum(b['matches'] for b in timing['batches'])
            (output / 'timing.json').write_text(json.dumps(timing, indent=2))
            sys.stdout, sys.stderr = original_stdout, original_stderr
            logging.getLogger().removeHandler(handler)
    print('FULL_SEASON_FINISHED', flush=True)
