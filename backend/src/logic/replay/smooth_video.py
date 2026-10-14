"""Experimental 30 fps optical-flow export; never changes simulation data.

Post-processes a presentation video, retaining its exact duration and event PTS.
Fast ball movement can still show interpolation artifacts; this is not a public
native animation/frame-rate profile.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path


def export_smooth_video(source, target):
    import cv2

    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError("Smooth export must have a separate output path")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for optical-flow export")
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if frames <= 0 or fps <= 0:
        raise ValueError("Source video has no decodable frames")
    expected = round(frames / fps * 30)
    duration = expected / 30
    padding = 1 / fps
    filters = (
        f"tpad=start_mode=clone:start_duration={padding}:stop_mode=clone:stop_duration={3 * padding},"
        f"minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
        f"trim=start={padding}:duration={duration},setpts=PTS-STARTPTS"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_suffix(".smoothing.mp4")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-vf",
                filters,
                "-frames:v",
                str(expected),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                str(pending),
            ],
            check=True,
            timeout=1800,
        )
        cap = cv2.VideoCapture(str(pending))
        actual = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if actual != expected or actual_fps != 30:
            raise RuntimeError(f"Interpolated timing mismatch: {actual}/{expected} frames at {actual_fps} fps")
        timeline_path = source.with_suffix(".timeline.json")
        timeline = json.loads(timeline_path.read_text()) if timeline_path.exists() else None
        if timeline:
            timeline.update(
                fps=30,
                total_frames=actual,
                total_duration_seconds=duration,
                motion_interpolation="experimental_optical_flow",
                native_source_redraw=timeline.get("native_redraw", False),
                native_redraw=False,
            )
            target.with_suffix(".timeline.json").write_text(json.dumps(timeline, indent=2))
        os.replace(pending, target)
    finally:
        pending.unlink(missing_ok=True)
    return {"frames": actual, "fps": 30, "duration_seconds": duration, "source_unchanged": True}
