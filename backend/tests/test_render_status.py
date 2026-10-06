import json
import struct
from logic.replay.render_status import replay_video_is_ready, write_render_status


def atom(kind, data=b''):
    return struct.pack('>I4s', len(data) + 8, kind) + data


def test_partial_mp4_is_not_ready_until_index_and_native_timeline_are_published(tmp_path):
    video = tmp_path / 'match_fixture_3d.mp4'
    partial = atom(b'ftyp', b'isom') + atom(b'mdat', b'frames')
    video.write_bytes(partial)
    assert not replay_video_is_ready(video)
    video.write_bytes(partial + atom(b'moov', b'index'))
    assert replay_video_is_ready(video)
    assert not replay_video_is_ready(video, 'fixture', require_native=True)
    video.with_suffix('.timeline.json').write_text(json.dumps({'native_redraw': True, 'match_id': 'other'}))
    assert not replay_video_is_ready(video, 'fixture', require_native=True)
    video.with_suffix('.timeline.json').write_text(json.dumps({'native_redraw': True, 'match_id': 'fixture'}))
    assert replay_video_is_ready(video, 'fixture', require_native=True)


def test_progress_preserves_job_start_across_updates(tmp_path, monkeypatch):
    monkeypatch.setattr('logic.replay.render_status.time.time', lambda: 100)
    path = tmp_path / 'progress.json'
    write_render_status(path, {'status': 'initializing', 'progress': 0, 'completed': False})
    monkeypatch.setattr('logic.replay.render_status.time.time', lambda: 137)
    write_render_status(path, {'status': 'rendering', 'progress': 45, 'completed': False})
    status = json.loads(path.read_text())
    assert status['started_at'] == 100
    assert status['elapsed_seconds'] == 37
    assert status['progress'] == 45
