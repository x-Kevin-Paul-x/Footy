"""
Unit tests for AudioProcessor and AmbientBedManager.
"""

from pathlib import Path
from backend.commentary.schemas import AudioClip
from backend.commentary.audio.processor import AudioProcessor
from backend.commentary.audio.ambient_bed import AmbientBedManager
from backend.commentary.audio.mixer import mix_commentary_and_ambience


def test_audio_processor_assembly(tmp_path):
    proc = AudioProcessor(master_duration_seconds=5.0)
    master_path = tmp_path / "commentary_track.wav"

    # Assemble empty clips
    path, speech_sec = proc.assemble_master_track([], master_path)
    assert path.exists()
    assert speech_sec == 0.0


def test_ambient_bed_generation(tmp_path):
    mgr = AmbientBedManager(duration_seconds=3.0)
    out_path = tmp_path / "ambient.wav"
    res_path = mgr.generate_ducked_ambient_track([], out_path)
    assert res_path.exists()
    assert res_path.stat().st_size > 1000
