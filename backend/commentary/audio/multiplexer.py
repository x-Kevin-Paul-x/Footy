"""
Phase 13: FFmpeg Multiplexer.
Multiplexes clean match video and broadcast commentary master audio into the final broadcast MP4.
Validates output streams and duration using ffprobe.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple


class VideoMultiplexer:
    """Muxes match video with final audio track using FFmpeg."""

    @staticmethod
    def mux(
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg muxing failed: {res.stderr}")
        return output_path

    @staticmethod
    def validate_mp4(mp4_path: Path) -> Dict[str, Any]:
        """Validate streams, sample rate, and duration of multiplexed video."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(mp4_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"ffprobe validation failed: {res.stderr}")

        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        duration = float(data.get("format", {}).get("duration", 0.0))
        size_bytes = int(data.get("format", {}).get("size", 0))

        return {
            "has_video": v_stream is not None,
            "has_audio": a_stream is not None,
            "duration_seconds": round(duration, 2),
            "size_bytes": size_bytes,
            "video_codec": v_stream.get("codec_name") if v_stream else None,
            "audio_codec": a_stream.get("codec_name") if a_stream else None,
            "audio_sample_rate": int(a_stream.get("sample_rate", 0)) if a_stream else None,
            "audio_channels": int(a_stream.get("channels", 0)) if a_stream else None,
        }
