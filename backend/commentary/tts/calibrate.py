"""
Phase 9 / One-Time Bootstrap: Voice Calibration for Ryan.
Measures empirical words-per-second (WPS) across energy tiers using Qwen3-TTS.
Saves results to tts_calibration.json.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# When executed via .venv-tts, add project root to sys.path
footy_root = Path(__file__).resolve().parents[3]
if str(footy_root) not in sys.path:
    sys.path.insert(0, str(footy_root))

from backend.commentary.config import (
    CALIBRATION_FILE,
    TTS_MODELS_DIR,
    DEFAULT_VOICE,
)
from backend.commentary.schemas import TTSCalibration


BENCHMARK_SAMPLES = [
    {
        "tier": "calm",
        "text": "Burnley and Bournemouth settling into the opening phase of the match.",
        "instruct": "Calm and composed commentator",
    },
    {
        "tier": "normal",
        "text": "A good spell of possession here as they work the ball into midfield.",
        "instruct": "Clear and attentive match commentator",
    },
    {
        "tier": "excited",
        "text": "Semenyo bursts through the defense and cuts it back toward the box!",
        "instruct": "Excited commentator with rising intensity",
    },
    {
        "tier": "goal",
        "text": "GOAL! Misty Noble smashes it home to give Bournemouth the lead!",
        "instruct": "Explosive joy, passionate goal celebration call",
    },
]


def run_calibration(voice: str = DEFAULT_VOICE, device: str = "cpu") -> TTSCalibration:
    print(f"=== Running Voice Calibration for '{voice}' on {device.upper()} ===")
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    model_dir = TTS_MODELS_DIR.resolve()
    print(f"Loading Qwen3TTSModel from {model_dir} ...")
    model = Qwen3TTSModel.from_pretrained(
        str(model_dir),
        device_map=device,
        dtype=torch.float32 if device == "cpu" else torch.bfloat16,
    )

    results = {}
    temp_dir = Path("backend/commentary/artifacts/calibration_clips")
    temp_dir.mkdir(parents=True, exist_ok=True)

    for sample in BENCHMARK_SAMPLES:
        tier = sample["tier"]
        text = sample["text"]
        instruct = sample["instruct"]
        word_count = len(text.split())

        print(f"Synthesizing [{tier}] ({word_count} words): \"{text}\" ...")
        t0 = time.time()
        wavs, sr = model.generate_custom_voice(
            text=text,
            speaker=voice,
            language="English",
            instruct=instruct,
        )
        elapsed = time.time() - t0
        dur_sec = len(wavs[0]) / float(sr)
        wps = round(word_count / dur_sec, 2)
        results[tier] = wps
        print(f"  -> Generated {dur_sec:.2f}s of audio in {elapsed:.2f}s (WPS: {wps})")

        # Save sample wav
        out_wav = temp_dir / f"calib_{voice}_{tier}.wav"
        sf.write(str(out_wav), wavs[0], sr)

    calib = TTSCalibration(
        voice=voice,
        calm_wps=results.get("calm", 2.45),
        normal_wps=results.get("normal", 2.75),
        excited_wps=results.get("excited", 3.15),
        goal_wps=results.get("goal", 3.40),
        calibrated_at=datetime.utcnow().isoformat(),
    )

    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(calib.model_dump(), f, indent=2)

    print(f"=== Calibration complete! Saved to {CALIBRATION_FILE} ===")
    print(json.dumps(calib.model_dump(), indent=2))
    return calib


if __name__ == "__main__":
    device = "cuda:0" if (len(sys.argv) > 1 and sys.argv[1] == "--gpu") else "cpu"
    run_calibration(device=device)
