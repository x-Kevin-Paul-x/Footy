"""Presentation timestamps recorded while frames are actually emitted."""
from pathlib import Path

from logic.presentation_timeline import PresentationTimeline, TimelineSegment


class TimelineWriter:
    def __init__(self, writer, path, match_id, fps):
        self.writer = writer
        self.path = Path(path).with_suffix('.timeline.json')
        self.timeline = PresentationTimeline(str(match_id), fps, 0, 0, timeline_version='2.0.0')
        self.closed = False

    def mark(self, kind, step, minute, events=()):
        pts = self.timeline.total_frames / self.timeline.fps
        if kind == 'match_play' and self.timeline.segments and self.timeline.segments[-1].segment_type == kind:
            segment = self.timeline.segments[-1]
            segment.source_step_end, segment.match_minute_end = step, minute
        else:
            self.timeline.segments.append(TimelineSegment(kind, step, step, pts, pts, minute, minute))
        if kind == 'match_play':
            self.timeline.minute_to_pts.setdefault(minute, pts)
            for identity in events:
                self.timeline.events_pts_map[str(identity)] = pts
                self.timeline.segments[-1].event_ids.append(str(identity))

    def append_data(self, frame):
        if self.closed:
            raise RuntimeError('Video writer is closed')
        self.writer.append_data(frame)
        self.timeline.total_frames += 1
        self.timeline.total_duration_seconds = self.timeline.total_frames / self.timeline.fps
        if self.timeline.segments:
            self.timeline.segments[-1].pts_end_seconds = self.timeline.total_duration_seconds

    def close(self):
        if not self.closed:
            self.closed = True
            self.writer.close()
            self.timeline.save_to_file(self.path)
