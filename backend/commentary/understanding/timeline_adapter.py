"""
Phase 0: Presentation Timeline Adapter.
Maps simulation steps and match minutes to authoritative video Presentation Timestamps (PTS).
Handles intro, halftime, fulltime cards, and goal replays without clock drift.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class TimelineAdapter:
    """Provides exact PTS conversions and segment boundaries based on presentation_plan.json / timeline.json."""

    def __init__(self, timeline_path: Path):
        self.timeline_path = timeline_path
        with open(timeline_path, "r", encoding="utf-8") as f:
            self.data: Dict[str, Any] = json.load(f)

        self.match_id: str = self.data.get("match_id", "")
        self.fps: float = float(self.data.get("fps", 10.0))
        self.total_frames: int = int(self.data.get("total_frames", 0))
        self.total_duration_seconds: float = float(self.data.get("total_duration_seconds", 0.0))
        self.total_duration_ms: int = int(self.total_duration_seconds * 1000)

        # Parse segments
        self.segments: List[Dict[str, Any]] = self.data.get("segments", [])
        self.events_pts_map: Dict[str, float] = self.data.get("events_pts_map", {})

        # minute_to_pts mapping
        raw_min = self.data.get("minute_to_pts", {})
        self.minute_to_pts_map: Dict[int, float] = {int(k): float(v) for k, v in raw_min.items()}

        # Identify key broadcast milestones
        self.intro_segment = next((s for s in self.segments if s.get("segment_type") == "intro"), None)
        self.halftime_segment = next((s for s in self.segments if s.get("segment_type") == "halftime"), None)
        self.fulltime_segment = next((s for s in self.segments if s.get("segment_type") == "fulltime"), None)
        self.goal_replays = [s for s in self.segments if s.get("segment_type") == "goal_replay"]

    def event_to_pts(self, event_id: str) -> Optional[float]:
        """Look up exact video PTS seconds for an event ID or step key."""
        k = str(event_id)
        if k in self.events_pts_map:
            return self.events_pts_map[k]
        if f"event_{k}" in self.events_pts_map:
            return self.events_pts_map[f"event_{k}"]
        if f"step_{k}" in self.events_pts_map:
            return self.events_pts_map[f"step_{k}"]
        return None

    def event_to_ms(self, event_id: str) -> Optional[int]:
        """Look up exact video PTS milliseconds for an event ID or step key."""
        pts = self.event_to_pts(event_id)
        return int(pts * 1000) if pts is not None else None

    def minute_to_pts(self, minute: int) -> float:
        """Return video PTS seconds corresponding to a match minute (1 to 90)."""
        m = max(1, min(90, int(minute)))
        if m in self.minute_to_pts_map:
            return self.minute_to_pts_map[m]
        # Nearest neighbor interpolation
        for d in range(1, 90):
            if (m - d) in self.minute_to_pts_map:
                return self.minute_to_pts_map[m - d]
            if (m + d) in self.minute_to_pts_map:
                return self.minute_to_pts_map[m + d]
        return 0.0

    def minute_to_ms(self, minute: int) -> int:
        return int(self.minute_to_pts(minute) * 1000)

    def pts_to_match_minute(self, pts_seconds: float) -> int:
        """Return closest match minute for a given PTS timestamp."""
        if not self.minute_to_pts_map:
            # Fallback estimation based on total duration
            ratio = max(0.0, min(1.0, pts_seconds / max(1.0, self.total_duration_seconds)))
            return max(1, min(90, int(ratio * 90.0) + 1))
        closest_min = 1
        min_diff = float("inf")
        for m, pts in self.minute_to_pts_map.items():
            diff = abs(pts - pts_seconds)
            if diff < min_diff:
                min_diff = diff
                closest_min = m
        return closest_min

    def step_to_pts(self, step: int, total_steps: int = 3000) -> float:
        """
        Converts simulation step (0 to 3000) to presentation PTS seconds.
        First checks exact event PTS map; falls back to minute mapping.
        """
        # Goal event PTS is the crossing frame; the replay segment begins
        # AFTER crossing and the standard frame. Never react to that card.
        exact = self.event_to_pts(f"step_{step}")
        if exact is not None:
            return exact
        for segment in (self.halftime_segment, self.fulltime_segment):
            if segment and int(segment['source_step_start']) == step:
                return float(segment['pts_start_seconds'])
        if self.data.get('native_redraw'):
            intro = float((self.intro_segment or {}).get('pts_end_seconds', 0))
            pts = intro + step / self.fps
            pts += sum(1 / self.fps for s in self.goal_replays if int(s['source_step_start']) < step)
            if self.halftime_segment and step > int(self.halftime_segment['source_step_start']):
                pts += self.halftime_segment['pts_end_seconds'] - self.halftime_segment['pts_start_seconds']
            return round(pts, 3)
        exact = self.event_to_pts(f"step_{step}")
        if exact is not None:
            return exact

        # In Footy 3000-step simulation, ~33.33 steps per minute
        # Step 0-1500 is 1st half (min 1-45), step 1500-3000 is 2nd half (min 46-90)
        match_min = int(step / (total_steps / 90.0)) + 1
        match_min = max(1, min(90, match_min))

        pts_base = self.minute_to_pts(match_min)
        pts_next = self.minute_to_pts(min(90, match_min + 1)) if match_min < 90 else self.total_duration_seconds

        # Intra-minute interpolation
        steps_per_min = total_steps / 90.0
        step_in_min = (step % steps_per_min) / steps_per_min
        interpolated = pts_base + (pts_next - pts_base) * step_in_min
        return round(interpolated, 3)

    def step_to_ms(self, step: int, total_steps: int = 3000) -> int:
        return int(self.step_to_pts(step, total_steps) * 1000)

    def is_in_stoppage_card(self, pts_seconds: float) -> Optional[str]:
        """Returns the segment type if timestamp falls inside an intro/halftime/fulltime card."""
        for seg in [self.intro_segment, self.halftime_segment, self.fulltime_segment]:
            if seg:
                start = seg.get("pts_start_seconds", 0.0)
                end = seg.get("pts_end_seconds", 0.0)
                if start <= pts_seconds <= end:
                    return seg.get("segment_type")
        return None

    def get_play_windows(self) -> List[Tuple[float, float]]:
        """
        Returns list of (start_seconds, end_seconds) corresponding to active match play.
        Excludes intro card, halftime card, and fulltime card.
        """
        intro_end = self.intro_segment.get("pts_end_seconds", 0.0) if self.intro_segment else 0.0
        ht_start = self.halftime_segment.get("pts_start_seconds", 153.6) if self.halftime_segment else 153.6
        ht_end = self.halftime_segment.get("pts_end_seconds", 156.6) if self.halftime_segment else 156.6
        ft_start = self.fulltime_segment.get("pts_start_seconds", 306.7) if self.fulltime_segment else self.total_duration_seconds

        return [
            (intro_end, ht_start),
            (ht_end, ft_start)
        ]
