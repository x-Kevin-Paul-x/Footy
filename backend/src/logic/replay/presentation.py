"""Validated replay presentation settings, separate from authoritative match data."""

import json
import os
from pathlib import Path

RESOLUTIONS = {"720p": (1280, 720), "1080p": (1920, 1080)}


def dimensions(resolution):
    try:
        return RESOLUTIONS[resolution]
    except KeyError:
        raise ValueError("Supported replay resolutions are 720p and 1080p") from None


def profile_matches(video, resolution="720p", theme="dark", camera="wide"):
    path = Path(video).with_suffix(".presentation.json")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
        return (
            profile.get("resolution") == resolution
            and profile.get("theme") == theme
            and profile.get("camera", "wide") == camera
        )
    except (OSError, ValueError):
        return resolution == "720p" and theme == "dark" and camera == "wide"


def write_profile(video, resolution, theme, camera="wide"):
    path = Path(video).with_suffix(".presentation.json")
    pending = path.with_suffix(".json.tmp")
    pending.write_text(json.dumps({"resolution": resolution, "theme": theme, "camera": camera}), encoding="utf-8")
    os.replace(pending, path)


def create_native_environment(football_env, width, height):
    """Discard GRF's unkeyed idle engine cache before creating a graphics context.

    GRF otherwise reuses a framebuffer allocated at the previous resolution.
    This is called only by dedicated, sequential replay workers.
    """
    from gfootball.env import football_env_core

    if football_env_core._active_rendering:
        raise RuntimeError("A native renderer is already active in this replay process")
    football_env_core._unused_engines.clear()
    football_env_core._unused_rendering_engine = None
    env = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        representation="raw",
        render=True,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10,
        other_config_options={"render_resolution_x": width, "render_resolution_y": height},
    )
    env.reset()
    return env
