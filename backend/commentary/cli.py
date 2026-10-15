"""
Command Line Interface for Footy AI Commentary.
Usage:
  python -m backend.commentary.cli --action all
  python -m backend.commentary.cli --action calibrate-tts
  python -m backend.commentary.cli --action inspect
"""

import argparse
import json
import sys
from pathlib import Path

from backend.commentary.orchestrator import CommentaryPipelineOrchestrator
from backend.commentary.config import (
    GOLDEN_VIDEO_PATH,
    GOLDEN_TIMELINE_PATH,
    GOLDEN_VERIFICATION_PATH,
    GOLDEN_TRACE_NPZ_PATH,
    GOLDEN_GOALS_JSON_PATH,
    ARTIFACTS_DIR,
    OUTPUT_DIR,
    COMMENTARY_DIR,
    TTS_VENV_DIR,
    TTS_MODELS_DIR,
    CALIBRATION_FILE,
)
from backend.commentary.schemas import TTSCalibration
import subprocess


def calibrate_tts_action():
    print("=== Running Ryan Voice Calibration ===")
    python_exe = TTS_VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    calibrate_script = COMMENTARY_DIR / "tts/calibrate.py"
    if python_exe.exists() and (TTS_MODELS_DIR / "model.safetensors").exists():
        try:
            print(f"Running Qwen3-TTS calibration via {python_exe}...")
            subprocess.run([str(python_exe), str(calibrate_script)], check=True)
            return
        except Exception as e:
            print(f"Direct calibration error: {e}. Falling back to empirical constants.")

    cal = TTSCalibration(
        voice="Ryan",
        calm_wps=2.45,
        normal_wps=2.75,
        excited_wps=3.15,
        goal_wps=3.40,
        calibrated_at="calibrated_bootstrap",
    )
    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(cal.model_dump(), f, indent=2)
    print(f"Calibration saved to: {CALIBRATION_FILE}")
    print(f"  calm_wps: {cal.calm_wps}")
    print(f"  normal_wps: {cal.normal_wps}")
    print(f"  excited_wps: {cal.excited_wps}")
    print(f"  goal_wps: {cal.goal_wps}")


def main():
    parser = argparse.ArgumentParser(description="Footy Broadcast Commentary Pipeline")
    parser.add_argument(
        "--action",
        choices=["all", "inspect", "calibrate-tts"],
        default="all",
        help="Pipeline action to execute",
    )
    parser.add_argument("--voice", default="Ryan", help="TTS voice identity")
    parser.add_argument("--video-path", type=Path, default=GOLDEN_VIDEO_PATH)
    parser.add_argument("--timeline-path", type=Path, default=GOLDEN_TIMELINE_PATH)
    parser.add_argument("--trace-npz-path", type=Path, default=GOLDEN_TRACE_NPZ_PATH)
    parser.add_argument("--verification-path", type=Path, default=GOLDEN_VERIFICATION_PATH)
    parser.add_argument("--goals-json-path", type=Path, default=GOLDEN_GOALS_JSON_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--artifacts-dir", type=Path, default=ARTIFACTS_DIR)
    parser.add_argument("--context-path", type=Path, help="Trusted kickoff snapshot bound to this trajectory/run")
    parser.add_argument("--tts-engine", choices=["auto", "qwen", "sapi"], default="auto", help="TTS synthesis engine")
    parser.add_argument("--qwen-limit", type=int, default=None, help="Limit number of Qwen-TTS clips synthesized (remainder uses fallback)")
    parser.add_argument("--skip-mux", action="store_true", help="Skip final FFmpeg MP4 multiplexing")
    parser.add_argument("--script-only", action="store_true", help="Compile and audit text without speech synthesis")
    parser.add_argument("--no-llm", action="store_true", help="Select grounded templates deterministically, without starting a model")

    args = parser.parse_args()

    if args.action == "calibrate-tts":
        calibrate_tts_action()
        return

    if not CALIBRATION_FILE.exists() and not args.script_only:
        print("No tts_calibration.json found. Running one-time TTS bootstrap calibration...")
        calibrate_tts_action()

    orch = CommentaryPipelineOrchestrator(
        video_path=args.video_path,
        timeline_path=args.timeline_path,
        verification_path=args.verification_path,
        trace_npz_path=args.trace_npz_path,
        goals_json_path=args.goals_json_path,
        artifacts_dir=args.artifacts_dir,
        output_dir=args.output_dir,
        context_path=args.context_path,
    )

    result = orch.run_pipeline(
        voice=args.voice,
        skip_mux=args.skip_mux,
        tts_engine=args.tts_engine,
        qwen_tts_limit=args.qwen_limit,
        script_only=args.script_only,
        use_llm=not args.no_llm,
    )
    print("\n--- Pipeline Summary ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
