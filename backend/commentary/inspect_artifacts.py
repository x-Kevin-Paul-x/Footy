"""
Phase -1: Artifact Inspector for Footy AI Commentary.
Inspects ground truth simulation artifacts and timeline metadata.
Produces artifact_report.json describing:
- SHA256 hashes for all input artifacts
- Detailed inventory of arrays, shapes, dtypes, and ranges
- Manifest inspection (goals, shots, cards, fouls, xG, possession)
- Authoritative timeline analysis (segments, PTS mappings)
- Explicit capability flags to govern downstream detectors
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
import numpy as np


def compute_sha256(filepath: Path) -> str:
    """Compute sha256 checksum of a file."""
    if not filepath.exists():
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def inspect_match_artifacts(
    video_path: Path,
    timeline_path: Path,
    verification_path: Path,
    trace_npz_path: Path,
    goals_json_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "artifact_report.json"

    files_info = {
        "video": {
            "path": str(video_path),
            "exists": video_path.exists(),
            "bytes": video_path.stat().st_size if video_path.exists() else 0,
            "sha256": compute_sha256(video_path) if video_path.exists() else "",
        },
        "timeline": {
            "path": str(timeline_path),
            "exists": timeline_path.exists(),
            "bytes": timeline_path.stat().st_size if timeline_path.exists() else 0,
            "sha256": compute_sha256(timeline_path) if timeline_path.exists() else "",
        },
        "verification": {
            "path": str(verification_path),
            "exists": verification_path.exists(),
            "bytes": verification_path.stat().st_size if verification_path.exists() else 0,
            "sha256": compute_sha256(verification_path) if verification_path.exists() else "",
        },
        "trace_npz": {
            "path": str(trace_npz_path),
            "exists": trace_npz_path.exists(),
            "bytes": trace_npz_path.stat().st_size if trace_npz_path.exists() else 0,
            "sha256": compute_sha256(trace_npz_path) if trace_npz_path.exists() else "",
        },
        "goals_json": {
            "path": str(goals_json_path),
            "exists": goals_json_path.exists(),
            "bytes": goals_json_path.stat().st_size if goals_json_path.exists() else 0,
            "sha256": compute_sha256(goals_json_path) if goals_json_path.exists() else "",
        },
    }

    # Inspect timeline
    timeline_data = {}
    timeline_segments = []
    events_pts_map = {}
    minute_to_pts = {}
    if timeline_path.exists():
        with open(timeline_path, "r", encoding="utf-8") as f:
            timeline_data = json.load(f)
        timeline_segments = timeline_data.get("segments", [])
        events_pts_map = timeline_data.get("events_pts_map", {})
        minute_to_pts = timeline_data.get("minute_to_pts", {})

    # Inspect NPZ
    npz_arrays = {}
    manifest_data = {}
    if trace_npz_path.exists():
        loaded = np.load(trace_npz_path, allow_pickle=True)
        for key in loaded.files:
            arr = loaded[key]
            if key == "manifest":
                if arr.size > 0:
                    try:
                        manifest_data = json.loads(str(arr[0]))
                    except Exception:
                        manifest_data = {"raw": str(arr[0])}
                npz_arrays[key] = {
                    "shape": list(arr.shape),
                    "dtype": str(arr.dtype),
                    "is_manifest": True,
                }
            else:
                info = {
                    "shape": list(arr.shape),
                    "dtype": str(arr.dtype),
                }
                if np.issubdtype(arr.dtype, np.number):
                    info["min"] = float(np.min(arr))
                    info["max"] = float(np.max(arr))
                npz_arrays[key] = info

    # Inspect goals
    goals_data = {}
    if goals_json_path.exists():
        with open(goals_json_path, "r", encoding="utf-8") as f:
            goals_data = json.load(f)

    # Derive capabilities
    has_ball_coords = "ball_coords" in npz_arrays
    has_player_coords = "player_coords" in npz_arrays
    has_ball_owned = "ball_owned_team" in npz_arrays and "ball_owned_player" in npz_arrays
    has_manifest_events = bool(manifest_data.get("events"))
    has_manifest_xg = "xg" in manifest_data
    has_player_names = bool(manifest_data.get("home_players")) and bool(manifest_data.get("away_players"))
    has_timeline_pts = bool(events_pts_map) and bool(minute_to_pts)

    capabilities = {
        "can_detect_possession": has_ball_owned,
        "can_detect_passes": has_ball_coords and has_ball_owned,
        "can_detect_carries": has_ball_coords and has_ball_owned,
        "can_detect_field_progression": has_ball_coords,
        "can_detect_box_entries": has_ball_coords,
        "has_canonical_events": has_manifest_events,
        "has_native_xg": has_manifest_xg,
        "can_compute_xg": False,  # No raw xG engine required; we use verified ground-truth xG
        "has_player_names": has_player_names,
        "has_exact_goal_pts": has_timeline_pts and len(goals_data.get("frames", [])) > 0,
        "has_timeline_segments": len(timeline_segments) > 0,
        "has_intro_and_halftime_cards": any(s.get("segment_type") == "intro" for s in timeline_segments),
        "has_goal_replays": any(s.get("segment_type") == "goal_replay" for s in timeline_segments),
    }

    report = {
        "match_id": timeline_data.get("match_id", manifest_data.get("match_id", "unknown")),
        "files": files_info,
        "timeline_summary": {
            "fps": timeline_data.get("fps", 10.0),
            "total_frames": timeline_data.get("total_frames", 3107),
            "total_duration_seconds": timeline_data.get("total_duration_seconds", 310.7),
            "segment_count": len(timeline_segments),
            "segment_types": sorted(list({s.get("segment_type") for s in timeline_segments})),
            "events_mapped_count": len(events_pts_map),
            "minute_mapped_count": len(minute_to_pts),
        },
        "npz_summary": {
            "total_steps": int(npz_arrays.get("player_coords", {}).get("shape", [0])[0]),
            "arrays": npz_arrays,
        },
        "manifest_summary": {
            "home_team": manifest_data.get("home_team"),
            "away_team": manifest_data.get("away_team"),
            "home_score": manifest_data.get("home_score"),
            "away_score": manifest_data.get("away_score"),
            "possession_split": manifest_data.get("possession"),
            "xg": manifest_data.get("xg"),
            "shots": manifest_data.get("shots"),
            "shots_on_target": manifest_data.get("shots_on_target"),
            "events_count": len(manifest_data.get("events", [])),
            "home_players_count": len(manifest_data.get("home_players", [])),
            "away_players_count": len(manifest_data.get("away_players", [])),
        },
        "goals_summary": {
            "goal_frames_count": len(goals_data.get("frames", [])),
            "goals": [
                {
                    "step": f.get("step"),
                    "score": f.get("score"),
                    "ball": f.get("ball"),
                }
                for f in goals_data.get("frames", [])
            ],
        },
        "capabilities": capabilities,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent.parent

    video = project_root / "assets/matches/full-match-recordings/burnley-2-4-bournemouth.mp4"
    timeline = project_root / "assets/matches/full-match-recordings/burnley-2-4-bournemouth.timeline.json"
    verification = project_root / "assets/matches/full-match-recordings/burnley-2-4-bournemouth.verification.json"
    trace_npz = project_root / "backend/verification/season_20261005_234339/reports/recordings/run_1791240220_7b08d5/trace_match_2026_20_3.npz"
    goals_json = project_root / "backend/verification/season_20261005_234339/reports/recordings/run_1791240220_7b08d5/trace_match_2026_20_3.goals.json"
    out = base_dir / "artifacts"

    rep = inspect_match_artifacts(video, timeline, verification, trace_npz, goals_json, out)
    print(f"Artifact report written to: {out / 'artifact_report.json'}")
    print("Capabilities:")
    for k, v in rep["capabilities"].items():
        print(f"  {k}: {v}")
