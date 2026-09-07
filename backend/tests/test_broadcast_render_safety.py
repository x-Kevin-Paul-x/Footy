import hashlib
import sys
import types

import numpy as np

from logic.wsl_workers import grf_render_worker as worker


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dump_renderer_preserves_all_source_artifacts(monkeypatch, tmp_path):
    dump_file = tmp_path / "trace_match-1.dump"
    trajectory_file = tmp_path / "trace_match-1.npz"
    state_file = tmp_path / "trace_match-1.grfstate"
    legacy_state_file = tmp_path / "trace_match-1_states.grfstate"
    output_mp4 = tmp_path / "match_match-1_3d.mp4"
    for path, contents in (
        (dump_file, b"dump-source"),
        (trajectory_file, b"trajectory-source"),
        (state_file, b"state-source"),
        (legacy_state_file, b"legacy-state-source"),
    ):
        path.write_bytes(contents)
    before = {path: _sha(path) for path in (dump_file, trajectory_file, state_file, legacy_state_file)}

    class FakeHelper:
        def load_dump(self, _path):
            return [{"debug": {"config": {"players": []}}}]

        def _ScriptHelpers__build_players(self, _path, players):
            return players

    class FakeEnvironment:
        def render(self, mode=None):
            return np.zeros((8, 8, 3), dtype=np.uint8) if mode == "rgb_array" else None

        def reset(self):
            return None

        def step(self, _actions):
            return ([{"score": [0, 0], "ball_owned_team": -1, "ball_owned_player": -1}], 0.0, True, {})

        def close(self):
            return None

    class FakeWriter:
        def append_data(self, _frame):
            return None

        def close(self):
            output_mp4.write_bytes(b"derived-video")

    fake_env_module = types.ModuleType("gfootball.env")
    fake_env_module.script_helpers = types.SimpleNamespace(ScriptHelpers=FakeHelper)
    fake_env_module.config = types.SimpleNamespace(Config=lambda raw: dict(raw))
    fake_env_module.football_env = types.SimpleNamespace(FootballEnv=lambda _cfg: FakeEnvironment())
    fake_gfootball = types.ModuleType("gfootball")
    fake_gfootball.env = fake_env_module
    monkeypatch.setitem(sys.modules, "gfootball", fake_gfootball)
    monkeypatch.setitem(sys.modules, "gfootball.env", fake_env_module)
    monkeypatch.setitem(sys.modules, "imageio", types.SimpleNamespace(get_writer=lambda *_args, **_kwargs: FakeWriter()))
    monkeypatch.setattr(worker, "draw_pre_match_card", lambda **_kwargs: np.zeros((8, 8, 3), dtype=np.uint8))
    monkeypatch.setattr(worker, "draw_hud", lambda **kwargs: kwargs["frame"])
    monkeypatch.setattr(worker.MatchTrajectory, "load_from_npz", lambda _path: None)

    worker.render_from_dump({
        "match_id": "match-1",
        "dump_file": str(dump_file),
        "trajectory_file": str(trajectory_file),
        "output_mp4": str(output_mp4),
    })

    assert output_mp4.read_bytes() == b"derived-video"
    assert {path: _sha(path) for path in before} == before
