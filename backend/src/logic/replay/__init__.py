"""
Footy High-Performance Asynchronous Video Replay Subsystem
"""

from .replay_encoder import ReplayEncoder, FFmpegSoftwareEncoder, FFmpegNVENCEncoder, create_encoder


def __getattr__(name):
    if name == 'ReplayPipeline':
        from .replay_pipeline import ReplayPipeline
        return ReplayPipeline
    raise AttributeError(name)

__all__ = [
    "ReplayEncoder",
    "FFmpegSoftwareEncoder",
    "FFmpegNVENCEncoder",
    "create_encoder",
    "ReplayPipeline",
]
