import sys
from pathlib import Path
import numpy as np
import cv2
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
if len(sys.argv) > 1 and sys.argv[1] == 'original':
    import gfootball.env as football_env
else:
    from logic.replay.replay_pipeline import football_env
from logic.replay.grf_render_runtime import render_restored_native_frame
from logic.replay.native_goal_frames import restore_native_goal_state
from logic.grf_state_archive import GRFStateArchiveReader
directory = root / 'verification/season_20261004_001100'
recordings = directory / 'reports/recordings/run_1791069061_b159ac'
env = football_env.create_environment(env_name='11_vs_11_kaggle', representation='raw', render=True,
    number_of_left_players_agent_controls=10, number_of_right_players_agent_controls=10,
    other_config_options={'action_set': 'full', 'render_resolution_x': 1280, 'render_resolution_y': 720})
env.reset()
for suffix, step, label in [('.grfstate', 500, 'draw_movement'), ('.goals.grfstate', 0, 'draw_goal')]:
    with GRFStateArchiveReader(str(recordings / ('trace_match_2026_10_11' + suffix))) as reader:
        before = restore_native_goal_state(env, reader.get_state(step))
        image = render_restored_native_frame(env)
        after = env.observation()[0]
        np.testing.assert_array_equal(before['ball'], after['ball'])
        np.testing.assert_array_equal(before['left_team'], after['left_team'])
        np.testing.assert_array_equal(before['score'], after['score'])
        cv2.imwrite(str(directory / (label + ('_original' if len(sys.argv) > 1 else '') + '.jpg')), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        print(label, before['ball'], before['score'], flush=True)
env.close()
