"""Render a saved native match and verify dimensions, timing and source immutability."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logic.grf_trajectory import MatchTrajectory
from logic.replay.replay_pipeline import ReplayPipeline
from logic.replay.presentation import RESOLUTIONS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--resolution", choices=["720p", "1080p", "4k"], default="1080p")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark")
    parser.add_argument("--camera", choices=["wide", "bird", "tele", "director"], default="wide")
    args = parser.parse_args()
    if args.resolution == "4k":
        # Benchmark-only profile; deliberately absent from public API validation.
        RESOLUTIONS["4k"] = (3840, 2160)
    trajectory = args.recording.with_suffix(".npz")
    sources = [args.recording, trajectory]
    for suffix in (".goals.json", ".goals.grfstate"):
        extra = args.recording.with_suffix(suffix)
        if extra.exists():
            sources.append(extra)
    digests = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    match = MatchTrajectory.load_from_npz(trajectory)
    result = ReplayPipeline(encoder_type="software").render_match_video(
        {
            "match_id": match.match_id,
            "states_file": str(args.recording),
            "trajectory_file": str(trajectory),
            "output_mp4": str(args.output),
            "resolution": args.resolution,
            "theme": args.theme,
            "camera": args.camera,
        }
    )
    import cv2

    cap = cv2.VideoCapture(str(args.output))
    width, height = RESOLUTIONS[args.resolution]
    assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == width
    assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == height
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == result["total_frames"]
    assert cap.get(cv2.CAP_PROP_FPS) == 10
    cap.release()
    for path, digest in digests.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    result.update(source_unchanged=True, source_hashes=digests, physics_hash=match.compute_physics_hash())
    args.output.with_suffix(".benchmark.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
