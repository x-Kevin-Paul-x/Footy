"""
Audio Mixer: Combines commentary track and ambient stadium bed into a master audio bus.
"""

import wave
import subprocess
from pathlib import Path
import numpy as np

from backend.commentary.config import MASTER_SAMPLE_RATE


def mix_commentary_and_ambience(
    commentary_wav: Path,
    ambient_wav: Path,
    output_wav: Path,
    sample_rate: int = MASTER_SAMPLE_RATE,
) -> Path:
    """Combines speech bus and stadium ambience into final broadcast master."""
    def read_wav(path: Path) -> np.ndarray:
        with wave.open(str(path), "rb") as wf:
            n_ch = wf.getnchannels()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if n_ch == 2:
            return data.reshape(-1, 2).T
        return np.tile(data, (2, 1))

    c_audio = read_wav(commentary_wav)
    a_audio = read_wav(ambient_wav)

    # Pad or trim to matching length
    max_len = max(c_audio.shape[1], a_audio.shape[1])
    c_pad = np.zeros((2, max_len), dtype=np.float32)
    a_pad = np.zeros((2, max_len), dtype=np.float32)

    c_pad[:, :c_audio.shape[1]] = c_audio
    a_pad[:, :a_audio.shape[1]] = a_audio

    # Blend: commentary prominent (1.0), ambience balanced (0.6)
    mixed = c_pad * 1.0 + a_pad * 0.6

    # Peak normalization to prevent clipping (-1.0 dB ceiling ~ 0.89)
    peak = np.max(np.abs(mixed))
    if peak > 0.89:
        mixed = (mixed / peak) * 0.89

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    int16_data = (np.clip(mixed, -1.0, 1.0) * 32767.0).astype(np.int16).T.flatten()
    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_data.tobytes())

    normalized = output_wav.with_name(output_wav.stem + '_normalized.wav')
    # Standard loudness control, not just peak scaling. True peak leaves AAC headroom.
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(output_wav),
        '-af', 'loudnorm=I=-18:TP=-1.5:LRA=9', '-ar', str(sample_rate),
        '-ac', '2', '-c:a', 'pcm_s16le', str(normalized)], check=True)
    normalized.replace(output_wav)
    return output_wav
