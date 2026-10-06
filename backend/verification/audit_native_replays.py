"""Validate recorded native states against every canonical trajectory frame."""
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def audit_one(path):
    import gfootball.env as football_env
    from logic.grf_trajectory import MatchTrajectory
    from logic.grf_state_archive import GRFStateArchiveReader
    trajectory = MatchTrajectory.load_from_npz(Path(path))
    state_path = Path(path).with_suffix('.grfstate')
    env = football_env.create_environment(env_name='11_vs_11_kaggle', representation='raw',
                                         number_of_left_players_agent_controls=10,
                                         number_of_right_players_agent_controls=10,
                                         other_config_options={'action_set': 'full'})
    env.reset()
    started = time.monotonic()
    final_remaining = None
    native_half_restart = None
    try:
        with GRFStateArchiveReader(str(state_path)) as archive:
            archive.validate(expected_match_id=trajectory.match_id, expected_steps=trajectory.total_steps,
                             check_global_sha=True)
            for step, state in enumerate(archive.iter_states()):
                env.set_state(state)
                o = env.observation()[0]
                np.testing.assert_array_equal(np.concatenate([o['left_team'], o['right_team']]).astype(np.float32),
                                              trajectory.player_coords[step])
                np.testing.assert_array_equal(np.asarray(o['ball'], dtype=np.float32), trajectory.ball_coords[step])
                np.testing.assert_array_equal(o['score'], trajectory.scores[step])
                assert int(o['game_mode']) == int(trajectory.game_mode[step])
                assert int(o['ball_owned_team']) == int(trajectory.ball_owned_team[step])
                assert int(o['ball_owned_player']) == int(trajectory.ball_owned_player[step])
                final_remaining = int(o['steps_left'])
                if step >= 1500 and np.linalg.norm(o['ball'][:2]) < 1e-6:
                    if native_half_restart is None:
                        native_half_restart = step
        assert final_remaining == 0, f'Native full time not reached: {final_remaining}'
        assert native_half_restart is not None, 'Native halftime ball reset missing'
        first_ball_motion = np.flatnonzero(np.linalg.norm(trajectory.ball_coords[:, :2], axis=1) > .01)
        assert len(first_ball_motion) and int(first_ball_motion[0]) < 100, 'Kickoff did not move the ball'
        policy = trajectory.manifest.engine_fingerprint.get('policy', {})
        if policy:
            assert policy['name'] == 'TiKick actor' and len(policy['checkpoint_sha256']) == 64
            allowed = 20 if policy.get('builtin_ai_allowed') else 19
            assert np.all(trajectory.actions < allowed), 'Action outside recorded policy profile'
        goals = [e for e in trajectory.manifest.events if e['type'] == 'goal']
        for side, team in enumerate(('home', 'away')):
            changes = np.diff(trajectory.scores[:, side].astype(int), prepend=0)
            actual = np.flatnonzero(changes > 0).tolist()
            recorded = [int(e['step']) for e in goals if e['team'] == team]
            assert actual == recorded, f'Goal frame mismatch: {actual} != {recorded}'
        from logic.replay.native_goal_frames import NativeGoalFrames, restore_native_goal_state
        native_goals = NativeGoalFrames(str(state_path), trajectory.match_id, trajectory)
        goal_frames_checked = 0
        try:
            for goal in goals:
                frames = native_goals.by_step.get(int(goal['step']), [])
                if policy:
                    assert frames, 'Native crossing frames missing for goal'
                for item in frames:
                    observation = restore_native_goal_state(env, native_goals.archive.get_state(item['index']))
                    np.testing.assert_allclose(observation['ball'], item['ball'], rtol=0, atol=1e-6)
                    np.testing.assert_array_equal(observation['score'], item['score'])
                    goal_frames_checked += 1
                if frames:
                    ball = frames[0]['ball']
                    # A public GRF observation follows ten physics substeps.
                    # The ball can already have hit/rolled along the net; its
                    # final Y is not its Y at the line-crossing instant.
                    assert abs(ball[0]) > 1, f'Native goal ball did not pass the goal line: {ball}'
        finally:
            native_goals.close()
        result = {'match_id': trajectory.match_id, 'passed': True, 'frames_compared': trajectory.total_steps,
                  'native_steps_left': final_remaining, 'native_half_restart_frame': native_half_restart,
                  'halftime_event_present': any(e['type'] == 'half_time' for e in trajectory.manifest.events),
                  'first_kickoff_motion_frame': int(first_ball_motion[0]), 'native_goal_frames_checked': goal_frames_checked,
                  'policy': policy, 'score': list(trajectory.manifest.score), 'seconds': round(time.monotonic() - started, 2)}
    except Exception as exc:
        result = {'match_id': trajectory.match_id, 'passed': False, 'error': str(exc)}
    finally:
        env.close()
    Path(path).with_suffix('.audit.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('expected', nargs='?', type=int, default=380)
    parser.add_argument('fixture', nargs='?')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    directory, expected = args.directory, args.expected
    if args.workers < 1:
        parser.error('--workers must be positive')
    if args.fixture:
        print(json.dumps(audit_one(args.fixture)), flush=True)
        sys.exit(0)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        while True:
            paths = sorted(p for p in directory.glob('*.npz')
                           if p.with_suffix('.grfstate').exists() and not p.with_suffix('.audit.json').exists())
            for result in pool.map(audit_one, [str(p) for p in paths]):
                print(json.dumps(result), flush=True)
            if len(list(directory.glob('*.audit.json'))) >= expected:
                break
            time.sleep(5)
