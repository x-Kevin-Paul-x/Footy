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
import threading
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
        self._stderr_chunks: list[bytes] = []
        self._stderr_thread: Optional[threading.Thread] = None

    @abstractmethod
    def _build_ffmpeg_cmd(self) -> list:
        pass

    def start(self, width: int, height: int, fps: int, output_mp4: str):
        self.width = width
        self.height = height
        self.fps = fps
        self.output_mp4 = output_mp4
        self.frames_written = 0
        self._stderr_chunks = []

        os.makedirs(os.path.dirname(output_mp4) or ".", exist_ok=True)
        cmd = self._build_ffmpeg_cmd()

        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        # FFmpeg can emit enough diagnostics to fill an OS pipe while raw frames
        # are still being written.  Drain it continuously so the encoder cannot
        # deadlock behind a full stderr buffer.
        proc = self.proc

        def _drain_stderr() -> None:
            if proc.stderr is None:
                return
            for chunk in iter(lambda: proc.stderr.read(8192), b""):
                self._stderr_chunks.append(chunk)

        self._stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        self._stderr_thread.start()

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
        proc = self.proc
        if proc is None:
            return

        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            # communicate() attempts to flush stdin when the handle remains set.
            proc.stdin = None
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired as exc:
                self.abort()
                raise RuntimeError("FFmpeg did not finalize within 30 seconds") from exc

            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=2)
            if proc.returncode != 0:
                stderr = b"".join(self._stderr_chunks)
                err_text = stderr[-16000:].decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"FFmpeg encoder exited with error code {proc.returncode}:\n{err_text}"
                )
        finally:
            self.proc = None
            self._stderr_thread = None

    def abort(self) -> None:
        """Stop an incomplete encode without waiting indefinitely for finalization."""
        proc = self.proc
        if proc is None:
            return
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except OSError:
            pass
        proc.stdin = None
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1)
        self.proc = None
        self._stderr_thread = None


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
