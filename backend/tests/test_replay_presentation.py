import sys
import types
import pytest
from logic.replay.presentation import dimensions, profile_matches, write_profile, create_native_environment
from schemas import MatchRenderRequest


def test_public_profiles_are_strict():
    assert dimensions("1080p") == (1920, 1080)
    with pytest.raises(ValueError):
        MatchRenderRequest(resolution="4k")
    with pytest.raises(ValueError):
        dimensions("4k")


def test_cached_video_respects_requested_presentation(tmp_path):
    video = tmp_path / "match.mp4"
    assert profile_matches(video)
    assert not profile_matches(video, "1080p", "light")
    write_profile(video, "1080p", "light")
    assert profile_matches(video, "1080p", "light")
    assert not profile_matches(video)


def test_native_environment_drops_unkeyed_idle_buffers(monkeypatch):
    core = types.SimpleNamespace(_active_rendering=False, _unused_engines=[object()], _unused_rendering_engine=object())
    monkeypatch.setitem(sys.modules, "gfootball", types.ModuleType("gfootball"))
    module = types.ModuleType("gfootball.env")
    module.football_env_core = core
    monkeypatch.setitem(sys.modules, "gfootball.env", module)
    calls = []
    env = types.SimpleNamespace(reset=lambda: calls.append("reset"))
    backend = types.SimpleNamespace(create_environment=lambda **kwargs: calls.append(kwargs) or env)
    assert create_native_environment(backend, 1920, 1080) is env
    assert core._unused_engines == [] and core._unused_rendering_engine is None
    assert calls[0]["other_config_options"] == {"render_resolution_x": 1920, "render_resolution_y": 1080}
    assert calls[1] == "reset"
    core._active_rendering = True
    with pytest.raises(RuntimeError):
        create_native_environment(backend, 1280, 720)


def test_native_frame_keeps_rgb_and_corrects_opengl_origin():
    import numpy as np
    from logic.replay.grf_render_runtime import render_restored_native_frame

    bottom = np.array([[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [255, 255, 255]]], dtype=np.uint8)
    calls = []
    native = types.SimpleNamespace(
        game_config=types.SimpleNamespace(render=False, render_resolution_x=2, render_resolution_y=2),
        get_frame=lambda: bottom.tobytes(),
        render=lambda swap: calls.append("redraw"),
    )
    core = types.SimpleNamespace(_env=native, _retrieve_observation=lambda: calls.append("observe"))
    env = types.SimpleNamespace(unwrapped=types.SimpleNamespace(_env=core))
    frame = render_restored_native_frame(env)
    np.testing.assert_array_equal(frame, bottom[::-1])
    assert calls == ["redraw", "observe"]
