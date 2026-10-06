"""Shared render progress and finalized-video checks; no GRF dependency."""
import json
import os
import struct
import time
from pathlib import Path


def write_render_status(path, data):
    if not path:
        return
    target = Path(path)
    previous = {}
    try:
        previous = json.loads(target.read_text())
    except (OSError, ValueError):
        pass
    data = dict(data)
    data.setdefault('started_at', previous.get('started_at') if not previous.get('completed') else None)
    data['started_at'] = data['started_at'] or time.time()
    data['elapsed_seconds'] = int(time.time() - data['started_at'])
    temporary = target.with_name(target.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(data))
    os.replace(temporary, target)


def replay_video_is_ready(path, expected_match_id=None, require_native=False):
    """An unfinished ffmpeg output lacks a complete top-level moov atom."""
    path = Path(path)
    try:
        length = path.stat().st_size
        found_format = False
        found_index = False
        with path.open('rb') as video:
            offset = 0
            while offset + 8 <= length:
                video.seek(offset)
                size, kind = struct.unpack('>I4s', video.read(8))
                header = 8
                if size == 1:
                    size = struct.unpack('>Q', video.read(8))[0]
                    header = 16
                if size == 0:
                    size = length - offset
                if size < header or offset + size > length:
                    return False
                found_format |= kind == b'ftyp'
                found_index |= kind == b'moov'
                offset += size
        if not (found_format and found_index):
            return False
        if require_native:
            timeline = json.loads(path.with_suffix('.timeline.json').read_text())
            return bool(timeline.get('native_redraw')) and (expected_match_id is None or timeline.get('match_id') == expected_match_id)
        return True
    except (OSError, ValueError, struct.error):
        return False
