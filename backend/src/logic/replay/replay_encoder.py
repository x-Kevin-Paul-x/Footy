"""
Footy Replay Encoder Subsystem.
Direct rawvideo FFmpeg pipes for ultra-low latency video rendering:
- FFmpegSoftwareEncoder: libx264 CPU software encoding
- FFmpegNVENCEncoder: h264_nvenc hardware accelerated encoding on NVIDIA GPUs (RTX 5070)
- Configurable presets (p1..p7 / fast..veryfast) and direct RGB24 zero-conversion ingestion.
"""

import os
import sys
import subprocess
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class ReplayEncoder(ABC):
    """Abstract interface for video encoding pipelines."""

    def __init__(self, preset: str = "p4"):
        self.preset = preset
        self.proc: Optional[subprocess.Popen] = None
        self.width: int = 1280
        self.height: int = 720
        self.fps: int = 10
        self.output_mp4: str = ""
        self.frames_written: int = 0

    @abstractmethod
    def _build_ffmpeg_cmd(self) -> list:
        pass

    def start(self, width: int, height: int, fps: int, output_mp4: str):
        self.width = width
        self.height = height
        self.fps = fps
        self.output_mp4 = output_mp4
        self.frames_written = 0

        os.makedirs(os.path.dirname(output_mp4) or ".", exist_ok=True)
        cmd = self._build_ffmpeg_cmd()

        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

    def write_frame(self, frame_rgb: np.ndarray):
        """Writes an RGB24 numpy array (H, W, 3) directly to FFmpeg stdin."""
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("Encoder not started or process dead.")

        # Ensure contiguous bytes
        if not frame_rgb.flags['C_CONTIGUOUS']:
            frame_rgb = np.ascontiguousarray(frame_rgb)

        self.proc.stdin.write(frame_rgb.tobytes())
        self.frames_written += 1

    def close(self):
        """Flushes stdin, waits for ffmpeg to finalize container, and checks returncode."""
        if self.proc is not None:
            try:
                if self.proc.stdin and not self.proc.stdin.closed:
                    self.proc.stdin.close()
            except Exception:
                pass
            try:
                _, stderr = self.proc.communicate(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                    _, stderr = self.proc.communicate(timeout=2)
                except Exception:
                    stderr = b""
            if self.proc.returncode not in (0, None):
                err_text = stderr.decode('utf-8', errors='replace') if stderr else "Process terminated"
                raise RuntimeError(f"FFmpeg encoder exited with error code {self.proc.returncode}:\n{err_text}")
            self.proc = None


class FFmpegSoftwareEncoder(ReplayEncoder):
    """CPU Software Encoder using libx264."""

    def _build_ffmpeg_cmd(self) -> list:
        return [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", self.preset if self.preset in ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium") else "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            self.output_mp4
        ]


class FFmpegNVENCEncoder(ReplayEncoder):
    """NVIDIA Hardware Accelerated Encoder using h264_nvenc."""

    def _build_ffmpeg_cmd(self) -> list:
        return [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "h264_nvenc",
            "-preset", self.preset if self.preset.startswith("p") else "p4",
            "-rc", "vbr",
            "-cq", "24",
            "-pix_fmt", "yuv420p",
            self.output_mp4
        ]


def check_nvenc_available() -> bool:
    """Checks if h264_nvenc is supported and operational on the current system."""
    try:
        res = subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=0.1:size=64x64:rate=10",
             "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, timeout=3
        )
        return res.returncode == 0
    except Exception:
        return False


def create_encoder(encoder_type: str = "auto", preset: str = "p4") -> ReplayEncoder:
    """Factory creating the appropriate video encoder."""
    if encoder_type == "nvenc":
        return FFmpegNVENCEncoder(preset=preset)
    elif encoder_type == "software" or encoder_type == "libx264":
        return FFmpegSoftwareEncoder(preset=preset)
    else:  # auto
        if check_nvenc_available():
            return FFmpegNVENCEncoder(preset=preset)
        return FFmpegSoftwareEncoder(preset=preset)
