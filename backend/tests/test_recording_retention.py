import os

from database.db_setup import clean_old_simulation_data


def make_run(root, name, timestamp):
    folder = root / name
    folder.mkdir(parents=True)
    (folder / 'match.grfstate').write_bytes(b'recorded states')
    (folder / 'match.mp4').write_bytes(b'video')
    os.utime(folder, (timestamp, timestamp))
    return folder


def test_new_run_removes_previous_recordings_but_preserves_current_and_curated_assets(tmp_path, monkeypatch):
    monkeypatch.delenv('FOOTY_RUN_RETENTION', raising=False)
    recordings = tmp_path / 'reports' / 'recordings'
    old = make_run(recordings, 'run_previous', 1)
    current = make_run(recordings, 'run_current', 2)
    curated = tmp_path / 'assets' / 'matches' / 'full-match-recordings' / 'match.mp4'
    curated.parent.mkdir(parents=True)
    curated.write_bytes(b'curated video')
    clean_old_simulation_data('run_current', recordings_dir=recordings)
    assert not old.exists()
    assert (current / 'match.grfstate').exists()
    assert curated.read_bytes() == b'curated video'


def test_optional_retention_keeps_only_requested_number_of_previous_runs(tmp_path, monkeypatch):
    monkeypatch.setenv('FOOTY_RUN_RETENTION', '1')
    old = make_run(tmp_path, 'run_old', 1)
    recent = make_run(tmp_path, 'run_recent', 2)
    current = make_run(tmp_path, 'run_current', 3)
    clean_old_simulation_data('run_current', recordings_dir=tmp_path)
    assert not old.exists()
    assert recent.exists() and current.exists()
