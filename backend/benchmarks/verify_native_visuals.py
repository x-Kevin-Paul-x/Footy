"""Native integration proof for materials, cameras, cache changes and immutable physics."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logic.replay.native_visuals import enable_visual_runtime, bind_visual_identity

enable_visual_runtime()
import gfootball.env as football_env
from logic.replay.presentation import create_native_environment
from logic.replay.grf_render_runtime import render_restored_native_frame
from logic.grf_state_archive import GRFStateArchiveReader
from logic.grf_trajectory import MatchTrajectory
from logic.visual_identity import freeze_visual_identity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--clip", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    archive = GRFStateArchiveReader(str(args.recording))
    traj = MatchTrajectory.load_from_npz(args.recording.with_suffix(".npz"))
    source_hash = hashlib.sha256(args.recording.read_bytes()).hexdigest()
    summary = copy.deepcopy(traj.manifest.to_dict())
    fields = (
        "ball",
        "ball_direction",
        "left_team",
        "right_team",
        "left_team_direction",
        "right_team_direction",
        "score",
        "steps_left",
        "game_mode",
        "ball_owned_team",
        "ball_owned_player",
    )
    results = []
    for resolution in ((1280, 720), (1920, 1080), (1280, 720)):
        env = create_native_environment(football_env, *resolution)
        step = min(60, archive.total_steps - 1)
        env.set_state(archive.get_state(step))
        before = {k: np.array(env.observation()[0][k], copy=True) for k in fields}
        # Deliberately synthetic identity fixture; no historic identity invented or saved.
        fixture = copy.deepcopy(traj.manifest)
        fixture.home_roster = [
            {
                "player_id": i + 1,
                "jersey_number": 47 if i == 9 else i + 1,
                "appearance": {"skin": 1 + i % 4, "hair": "short01", "hair_colour": "brown"},
            }
            for i in range(11)
        ]
        fixture.away_roster = [
            {
                "player_id": i + 20,
                "jersey_number": i + 20,
                "appearance": {"skin": 1 + i % 4, "hair": "short02", "hair_colour": "black"},
            }
            for i in range(11)
        ]
        fixture.visual_identity = freeze_visual_identity(
            fixture.home_team, fixture.away_team, fixture.home_roster, fixture.away_roster
        )
        assert bind_visual_identity(env, fixture, args.output / "kits")
        for preset in (1, 2, 3, 4):
            for blend in (0.5, 1.0) if preset == 4 else (1.0,):
                env.set_state(archive.get_state(step))
                env._footy_camera = (preset, 0, 9, blend)
                frame = render_restored_native_frame(env)
                assert frame.shape == (resolution[1], resolution[0], 3)
                after = env.observation()[0]
                for key in fields:
                    np.testing.assert_array_equal(before[key], after[key], err_msg=key)
                from PIL import Image

                Image.fromarray(frame).save(args.output / f"{resolution[0]}-camera-{preset}-{blend}.png")
                results.append({"dimensions": resolution, "camera": preset, "blend": blend, "physics_unchanged": True})
        if args.clip and resolution == (1280, 720):
            native = env.unwrapped._env._env
            count = native.validate_presentation_animation(str(args.clip.resolve()))
            assert count == 168
            import imageio

            with imageio.get_writer(str(args.output / "celebration-prototype.mp4"), fps=30, codec="libx264") as writer:
                for frame_index in range(0, count, 3):
                    env.set_state(archive.get_state(step))
                    env._footy_camera = (4, 0, 9, 1.0)
                    render_restored_native_frame(env)
                    buffer = native.render_presentation_clip(0, 9, str(args.clip.resolve()), frame_index)
                    frame = np.frombuffer(buffer, dtype=np.uint8).reshape(720, 1280, 3)[::-1].copy()
                    writer.append_data(frame)
                    env.unwrapped._env._retrieve_observation()
                    after = env.observation()[0]
                    for key in fields:
                        np.testing.assert_array_equal(before[key], after[key], err_msg=key)
            results.append({"clip": "CC0 KayKit Cheer", "native_frames": count, "physics_unchanged": True})
        env.close()
    assert hashlib.sha256(args.recording.read_bytes()).hexdigest() == source_hash
    assert traj.manifest.to_dict() == summary
    (args.output / "proof.json").write_text(
        json.dumps({"checks": results, "source_unchanged": True, "source_sha256": source_hash}, indent=2)
    )
    archive.close()
    print("Native identity/camera/cache proof passed:", len(results), "checks")


if __name__ == "__main__":
    main()
