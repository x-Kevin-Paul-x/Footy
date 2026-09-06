"""
Canonical Presentation Timeline Module for Footy Broadcast Replays.
Maps the three explicit clocks:
1. Simulation step / physics time
2. Football match time (minute 1-90)
3. Encoded video presentation timestamp (PTS in seconds)
Enables sample-accurate replay seeking across intro cards, halftime cards, goal holds, and slow-mo replays.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple, Union


@dataclass
class TimelineSegment:
    """A contiguous presentation segment in an encoded broadcast replay."""
    segment_type: str  # "intro", "match_play", "goal_replay", "halftime", "fulltime"
    source_step_start: int
    source_step_end: int
    pts_start_seconds: float
    pts_end_seconds: float
    match_minute_start: int
    match_minute_end: int
    event_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineSegment":
        return cls(
            segment_type=str(data.get("segment_type", "match_play")),
            source_step_start=int(data.get("source_step_start", 0)),
            source_step_end=int(data.get("source_step_end", 0)),
            pts_start_seconds=float(data.get("pts_start_seconds", 0.0)),
            pts_end_seconds=float(data.get("pts_end_seconds", 0.0)),
            match_minute_start=int(data.get("match_minute_start", 0)),
            match_minute_end=int(data.get("match_minute_end", 0)),
            event_ids=list(data.get("event_ids", [])),
        )


@dataclass
class PresentationTimeline:
    """Canonical timeline representation for a match video recording."""
    match_id: str
    fps: float
    total_frames: int
    total_duration_seconds: float
    segments: List[TimelineSegment] = field(default_factory=list)
    events_pts_map: Dict[str, float] = field(default_factory=dict)
    minute_to_pts: Dict[int, float] = field(default_factory=dict)
    timeline_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "fps": self.fps,
            "total_frames": self.total_frames,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "segments": [s.to_dict() for s in self.segments],
            "events_pts_map": self.events_pts_map,
            "minute_to_pts": {str(k): round(v, 3) for k, v in self.minute_to_pts.items()},
            "timeline_version": self.timeline_version,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp_p = p.with_suffix(f"{p.suffix}.tmp")
        tmp_p.write_text(self.to_json(), encoding="utf-8")
        tmp_p.replace(p)

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> "PresentationTimeline":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PresentationTimeline":
        raw_min_map = data.get("minute_to_pts", {})
        minute_to_pts = {int(k): float(v) for k, v in raw_min_map.items()}
        raw_evt_map = data.get("events_pts_map", {})
        events_pts_map = {str(k): float(v) for k, v in raw_evt_map.items()}
        segments = [TimelineSegment.from_dict(s) for s in data.get("segments", [])]
        return cls(
            match_id=str(data.get("match_id", "")),
            fps=float(data.get("fps", 15.0)),
            total_frames=int(data.get("total_frames", 0)),
            total_duration_seconds=float(data.get("total_duration_seconds", 0.0)),
            segments=segments,
            events_pts_map=events_pts_map,
            minute_to_pts=minute_to_pts,
            timeline_version=str(data.get("timeline_version", "1.0.0")),
        )

    def seek_minute(self, minute: int) -> float:
        """Return accurate presentation time in seconds for a match minute (1 to 90)."""
        m = max(1, min(90, int(minute)))
        if m in self.minute_to_pts:
            return self.minute_to_pts[m]
        # Fallback to nearest minute
        for diff in range(1, 90):
            if (m - diff) in self.minute_to_pts:
                return self.minute_to_pts[m - diff]
            if (m + diff) in self.minute_to_pts:
                return self.minute_to_pts[m + diff]
        return 0.0

    def seek_event(self, event_key_or_idx: Union[str, int]) -> Optional[float]:
        """Return accurate presentation time in seconds for a specific event."""
        k = str(event_key_or_idx)
        return self.events_pts_map.get(k)


def build_canonical_timeline(
    match_id: str,
    total_steps: int,
    events: List[Dict[str, Any]],
    fps: float = 15.0,
    intro_frames: int = 45,
    halftime_frames: int = 60,
    fulltime_frames: int = 75,
    goal_hold_frames: int = 30,
    goal_replay_frames: int = 40,
) -> PresentationTimeline:
    """
    Constructs 100% deterministic presentation timeline mapping from simulation steps and events.
    Replicates the frame-for-frame sequence output by the Footy video encoders:
    1. Intro card (intro_frames, e.g. 45 frames = 3.0s at 15 fps)
    2. First-half simulation frames up to step total_steps // 2
       - Goal triggers add hold frames and slow-mo replays
    3. Halftime studio recap card (halftime_frames, e.g. 60 frames = 4.0s)
    4. Second-half simulation frames up to step total_steps - 1
       - Goal triggers add hold frames and slow-mo replays
    5. Fulltime studio card (fulltime_frames, e.g. 75 frames = 5.0s)
    """
    frame_count = 0
    segments: List[TimelineSegment] = []
    events_pts_map: Dict[str, float] = {}
    minute_to_pts: Dict[int, float] = {}

    def pts_for_frame(f: int) -> float:
        return round(f / fps, 3)

    # 1. Intro card segment
    intro_start_pts = pts_for_frame(frame_count)
    frame_count += intro_frames
    intro_end_pts = pts_for_frame(frame_count)
    segments.append(TimelineSegment(
        segment_type="intro",
        source_step_start=0,
        source_step_end=0,
        pts_start_seconds=intro_start_pts,
        pts_end_seconds=intro_end_pts,
        match_minute_start=0,
        match_minute_end=0,
        event_ids=[],
    ))

    # Map events by step
    goal_events_by_step: Dict[int, List[Tuple[int, Dict[str, Any]]]] = {}
    for ev_idx, ev in enumerate(events):
        ev_type = str(ev.get("type", "")).lower()
        if ev_type == "goal":
            ev_step = ev.get("step")
            if ev_step is None:
                ev_min = float(ev.get("minute", 0))
                ev_step = int((ev_min / 90.0) * max(1, total_steps - 1))
            ev_step = max(0, min(total_steps - 1, int(ev_step)))
            goal_events_by_step.setdefault(ev_step, []).append((ev_idx, ev))

    current_play_start_step = 0
    current_play_start_frame = frame_count
    current_play_start_minute = 1

    halftime_step = total_steps // 2

    for step in range(total_steps):
        match_min = max(1, min(90, int((step / max(1, total_steps)) * 90) + 1))
        if match_min not in minute_to_pts:
            minute_to_pts[match_min] = pts_for_frame(frame_count)

        # Append standard pitch frame
        frame_count += 1

        # Check for goal event trigger at this step
        if step in goal_events_by_step:
            step_goals = goal_events_by_step[step]
            for ev_idx, gev in step_goals:
                ev_key = str(gev.get("id", ev_idx))
                event_pts = pts_for_frame(frame_count - 1)
                events_pts_map[ev_key] = event_pts
                events_pts_map[f"event_{ev_idx}"] = event_pts
                events_pts_map[f"step_{step}"] = event_pts

            # Goal replay insert
            replay_extra_frames = goal_hold_frames + goal_replay_frames
            replay_start_pts = pts_for_frame(frame_count)
            frame_count += replay_extra_frames
            replay_end_pts = pts_for_frame(frame_count)

            segments.append(TimelineSegment(
                segment_type="goal_replay",
                source_step_start=step,
                source_step_end=step,
                pts_start_seconds=replay_start_pts,
                pts_end_seconds=replay_end_pts,
                match_minute_start=match_min,
                match_minute_end=match_min,
                event_ids=[str(gev.get("id", idx)) for idx, gev in step_goals],
            ))

        # Halftime card trigger
        if step == halftime_step:
            ht_start_pts = pts_for_frame(frame_count)
            frame_count += halftime_frames
            ht_end_pts = pts_for_frame(frame_count)
            segments.append(TimelineSegment(
                segment_type="halftime",
                source_step_start=step,
                source_step_end=step,
                pts_start_seconds=ht_start_pts,
                pts_end_seconds=ht_end_pts,
                match_minute_start=45,
                match_minute_end=45,
                event_ids=[],
            ))

    # Fulltime card
    ft_start_pts = pts_for_frame(frame_count)
    frame_count += fulltime_frames
    ft_end_pts = pts_for_frame(frame_count)
    segments.append(TimelineSegment(
        segment_type="fulltime",
        source_step_start=max(0, total_steps - 1),
        source_step_end=max(0, total_steps - 1),
        pts_start_seconds=ft_start_pts,
        pts_end_seconds=ft_end_pts,
        match_minute_start=90,
        match_minute_end=90,
        event_ids=[],
    ))

    # Ensure all minutes 1-90 are present in minute_to_pts
    for m in range(1, 91):
        if m not in minute_to_pts:
            # Interpolate from previous
            prev = minute_to_pts.get(m - 1, intro_end_pts)
            minute_to_pts[m] = prev

    total_duration = pts_for_frame(frame_count)

    return PresentationTimeline(
        match_id=str(match_id),
        fps=fps,
        total_frames=frame_count,
        total_duration_seconds=total_duration,
        segments=segments,
        events_pts_map=events_pts_map,
        minute_to_pts=minute_to_pts,
        timeline_version="1.0.0",
    )
