"""
Unit tests for TTSWorker, duration fitting, and calibration.
"""

import json
from pathlib import Path
from backend.commentary.schemas import (
    CommentarySlot,
    CommentaryUtterance,
    TTSCalibration,
)
from backend.commentary.tts.worker import TTSWorker, get_wav_duration_seconds


def test_tts_calibration_schema():
    cal = TTSCalibration(
        voice="Ryan",
        calm_wps=2.45,
        normal_wps=2.75,
        excited_wps=3.15,
        goal_wps=3.40,
    )
    d = cal.model_dump()
    assert d["voice"] == "Ryan"
    assert d["calm_wps"] == 2.45
    assert d["goal_wps"] == 3.40

    restored = TTSCalibration(**d)
    assert restored.voice == "Ryan"
    assert restored.normal_wps == 2.75


def test_tts_worker_cascading_fit(tmp_path):
    worker = TTSWorker(voice="Ryan")
    worker.clips_dir = tmp_path

    slot = CommentarySlot(
        commentary_id="com_test_01",
        start_ms=10000,
        max_end_ms=13500,
        window_seconds=3.5,
        slot_type="attack",
        speaker="Ryan",
        energy_target=0.75,
        target_words=8,
        allowed_fact_ids=["fact_0001"],
    )

    utt = CommentaryUtterance(
        commentary_id="com_test_01",
        speaker="Ryan",
        energy=0.75,
        emotion="excited",
        target_duration_ms=3500,
        primary="A tremendous burst of speed through the midfield opening up the space!",
        short="Tremendous burst of speed opening up the space!",
        emergency_short="Burst of speed!",
        used_fact_ids=["fact_0001"],
    )

    clip = worker.synthesize_clip(utt, slot)
    assert clip.clip_id == "com_test_01"
    assert clip.requested_start_ms == 10000
    assert clip.actual_duration_ms > 0
    assert Path(clip.file_path).exists()
    assert clip.variant_used in ("primary", "short", "emergency_short")
