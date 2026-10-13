"""
Phase 11: Audio Processor & Master Timeline Assembly.
Resamples 24 kHz mono clips to 48 kHz stereo.
Assembles the master commentary track at exact PTS timestamps across the match duration.
"""

import json
import wave
import struct
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

from backend.commentary.schemas import AudioClip, AudioManifest
from backend.commentary.config import (
    ARTIFACTS_DIR,
    MASTER_SAMPLE_RATE,
)


class AudioProcessor:
    """Stitches audio clips onto a continuous master broadcast timeline."""

    def __init__(self, master_duration_seconds: float = 310.7, sample_rate: int = MASTER_SAMPLE_RATE):
        self.duration_sec = master_duration_seconds
        self.sample_rate = sample_rate
        self.total_samples = int(self.duration_sec * self.sample_rate)

    def resample_clip_to_48k(self, input_wav: Path, output_wav: Path) -> bool:
        """Resample a single clip to 48 kHz stereo using FFmpeg."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_wav),
            "-af", "aresample=resampler=soxr",
            "-ar", str(self.sample_rate),
            "-ac", "2",
            str(output_wav),
        ]
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0 and output_wav.exists()

    def assemble_master_track(
        self,
        clips: List[AudioClip],
        output_path: Path,
    ) -> Tuple[Path, float]:
        """
        Mixes all clips onto a silent canvas at exact PTS offsets.
        Returns (output_path, total_speech_seconds).
        """
        # Master stereo buffer (channels=2, samples=total_samples)
        master = np.zeros((2, self.total_samples), dtype=np.float32)
        total_speech_samples = 0
        last_clip_end_sample = 0

        resampled_dir = output_path.parent / "resampled_clips"
        resampled_dir.mkdir(parents=True, exist_ok=True)

        sorted_clips = sorted(clips, key=lambda c: c.pts_offset_seconds)

        for clip in sorted_clips:
            raw_path = Path(clip.file_path)
            if not raw_path.exists():
                raise FileNotFoundError(raw_path)

            resampled_path = resampled_dir / f"{clip.clip_id}_48k.wav"
            if not self.resample_clip_to_48k(raw_path, resampled_path):
                raise RuntimeError(f'Cannot resample {raw_path}')

            # Read audio data
            with wave.open(str(resampled_path), "rb") as wf:
                n_channels = wf.getnchannels()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)

            data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            if n_channels == 2:
                data = data.reshape(-1, 2).T
            else:
                data = np.tile(data, (2, 1))

            requested_start = int(clip.pts_offset_seconds * self.sample_rate)
            # Preserve the event anchor. Deadline/overlap errors must be fixed
            # in speech planning, never by postponing an urgent call.
            start_sample = requested_start
            clip_samples = data.shape[1]
            deadline = round(clip.max_end_ms / 1000 * self.sample_rate)
            if start_sample < last_clip_end_sample:
                raise ValueError(f'Overlapping speech: {clip.clip_id}; timing must be fitted before mixing')
            if start_sample + clip_samples > deadline:
                raise ValueError(f'Speech exceeds its deadline: {clip.clip_id}')
            end_sample = min(self.total_samples, start_sample + clip_samples)
            actual_len = end_sample - start_sample

            if actual_len > 0 and start_sample < self.total_samples:
                master[:, start_sample:end_sample] += data[:, :actual_len]
                total_speech_samples += actual_len
                last_clip_end_sample = end_sample

        # Prevent digital clipping (normalize if peaks exceed 0.95)
        peak = np.max(np.abs(master))
        if peak > 0.95:
            master = (master / peak) * 0.95

        # Write master WAV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        int16_data = (master * 32767.0).astype(np.int16).T.flatten()
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(int16_data.tobytes())

        total_speech_sec = round(total_speech_samples / float(self.sample_rate), 2)
        return output_path, total_speech_sec
