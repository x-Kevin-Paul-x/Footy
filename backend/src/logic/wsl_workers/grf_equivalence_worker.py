"""
WSL Worker: GRF State-to-Observation & Render Equivalence Tester.
Runs pure C++ GFootball simulation in WSL, captures raw states, full 16-field observations, and rendered RGB frames
at multiple checkpoints, then resets a completely new environment instance, restores states via set_state(),
and measures mathematical parity:
- Complete observation dictionary equality across all 16 replay fields
- Rendered RGB frame MAE, MSE, and PSNR.
- End-to-end pipeline validation: archive -> set_state() -> observation == trajectory.npz.
"""

import sys
import os
import json
import numpy as np
from pathlib import Path


def run_equivalence_test(num_steps: int = 50) -> dict:
    import gfootball.env as football_env

    # 1. First Environment: Original Simulation
    env1 = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        representation='raw',
        render=True,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10,
        other_config_options={
            'render_resolution_x': 640,
            'render_resolution_y': 360,
        }
    )
    env1.reset()
    env1.observation()

    checkpoints = [0, 10, 25, min(num_steps - 1, 49)]
    saved_states = {}
    saved_obs = {}
    saved_frames = {}

    np.random.seed(42)
    step = 0

    while step <= max(checkpoints):
        if step in checkpoints:
            saved_states[step] = env1.get_state()
            saved_obs[step] = env1.observation()[0]
            f = env1.render(mode='rgb_array')
            if f is not None:
                saved_frames[step] = f.copy()

        actions = [0] * 20
        _, _, done, _ = env1.step(actions)
        step += 1
        if done:
            break

    env1.close()

    # 2. Second Fresh Environment: State Restoration & Replay
    env2 = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        representation='raw',
        render=True,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10,
        other_config_options={
            'render_resolution_x': 640,
            'render_resolution_y': 360,
        }
    )
    env2.reset()

    results = {}
    all_obs_identical = True

    for chk_step in checkpoints:
        if chk_step not in saved_states:
            continue

        state_bytes = saved_states[chk_step]
        orig_o = saved_obs[chk_step]
        orig_f = saved_frames.get(chk_step)

        # Restore state in fresh environment
        env2.set_state(state_bytes)
        restored_o = env2.observation()[0]
        restored_f = env2.render(mode='rgb_array')

        # Compare Complete 16-Field Observation Vector
        l_diff = float(np.max(np.abs(np.array(orig_o['left_team']) - np.array(restored_o['left_team']))))
        r_diff = float(np.max(np.abs(np.array(orig_o['right_team']) - np.array(restored_o['right_team']))))
        ld_diff = float(np.max(np.abs(np.array(orig_o['left_team_direction']) - np.array(restored_o['left_team_direction']))))
        rd_diff = float(np.max(np.abs(np.array(orig_o['right_team_direction']) - np.array(restored_o['right_team_direction']))))
        b_diff = float(np.max(np.abs(np.array(orig_o['ball']) - np.array(restored_o['ball']))))
        bd_diff = float(np.max(np.abs(np.array(orig_o['ball_direction']) - np.array(restored_o['ball_direction']))))

        score_match = (list(orig_o['score']) == list(restored_o['score']))
        owned_team_match = (orig_o.get('ball_owned_team') == restored_o.get('ball_owned_team'))
        owned_player_match = (orig_o.get('ball_owned_player') == restored_o.get('ball_owned_player'))
        game_mode_match = (orig_o.get('game_mode') == restored_o.get('game_mode'))

        # Check tired factor, card, and active state parity
        tired_l_diff = float(np.max(np.abs(np.array(orig_o.get('left_team_tired_factor', [0])) - np.array(restored_o.get('left_team_tired_factor', [0])))))
        tired_r_diff = float(np.max(np.abs(np.array(orig_o.get('right_team_tired_factor', [0])) - np.array(restored_o.get('right_team_tired_factor', [0])))))
        cards_l_match = bool(np.array_equal(orig_o.get('left_team_yellow_card'), restored_o.get('left_team_yellow_card')))
        cards_r_match = bool(np.array_equal(orig_o.get('right_team_yellow_card'), restored_o.get('right_team_yellow_card')))
        active_l_match = bool(np.array_equal(orig_o.get('left_team_active'), restored_o.get('left_team_active')))
        active_r_match = bool(np.array_equal(orig_o.get('right_team_active'), restored_o.get('right_team_active')))

        obs_passed = bool(
            l_diff < 1e-4 and r_diff < 1e-4 and
            ld_diff < 1e-4 and rd_diff < 1e-4 and
            b_diff < 1e-4 and bd_diff < 1e-4 and
            tired_l_diff < 1e-4 and tired_r_diff < 1e-4 and
            score_match and owned_team_match and owned_player_match and
            game_mode_match and cards_l_match and cards_r_match and
            active_l_match and active_r_match
        )
        if not obs_passed:
            all_obs_identical = False

        # Compare RGB frames
        frame_metrics = {}
        if orig_f is not None and restored_f is not None:
            diff = np.abs(orig_f.astype(np.float32) - restored_f.astype(np.float32))
            mae = float(np.mean(diff))
            mse = float(np.mean(diff ** 2))
            psnr = float(10 * np.log10((255.0 ** 2) / mse)) if mse > 0 else 999.0
            exact_pixels = int(np.sum(orig_f == restored_f))
            total_pixels = int(orig_f.size)
            pixel_match_pct = round((exact_pixels / total_pixels) * 100, 2)

            frame_metrics = {
                "mae": mae,
                "mse": mse,
                "psnr": psnr,
                "exact_pixel_pct": pixel_match_pct,
                "frame_shape": list(orig_f.shape)
            }

        results[f"step_{chk_step}"] = {
            "obs_passed": obs_passed,
            "left_team_max_diff": l_diff,
            "right_team_max_diff": r_diff,
            "left_dir_max_diff": ld_diff,
            "right_dir_max_diff": rd_diff,
            "ball_max_diff": b_diff,
            "ball_dir_max_diff": bd_diff,
            "score_match": score_match,
            "ownership_match": owned_team_match,
            "game_mode_match": game_mode_match,
            "frame_metrics": frame_metrics
        }

    env2.close()

    report = {
        "success": all_obs_identical,
        "checkpoints_tested": len(saved_states),
        "details": results
    }
    return report


def run_end_to_end_archive_test(states_file: str, trajectory_file: str) -> dict:
    """Validate that states in archive, when restored in fresh env, match trajectory.npz arrays."""
    import gfootball.env as football_env
    # Add backend/src to path
    src_dir = str(Path(__file__).resolve().parent.parent.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from logic.grf_state_archive import GRFStateArchiveReader
    from logic.grf_trajectory import MatchTrajectory

    archive = GRFStateArchiveReader(states_file)
    traj = MatchTrajectory.load_from_npz(Path(trajectory_file))

    env = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        representation='raw',
        render=False,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10
    )
    env.reset()

    test_steps = [0, 5, 20, min(50, archive.total_steps - 1), archive.total_steps - 1]
    step_results = {}
    all_passed = True

    for step in test_steps:
        state_bytes = archive.get_state(step)
        env.set_state(state_bytes)
        obs = env.observation()[0]

        # Trajectory player positions (22 players: 11 left + 11 right)
        traj_players = traj.player_coords[step]  # shape (22, 2)
        l_obs = np.array(obs['left_team'])  # shape (11, 2)
        r_obs = np.array(obs['right_team'])  # shape (11, 2)
        obs_players = np.concatenate([l_obs, r_obs], axis=0)

        p_diff = float(np.max(np.abs(traj_players - obs_players)))

        # Trajectory ball (3 coordinates: x, y, z)
        traj_ball = traj.ball_coords[step]
        b_obs = np.array(obs['ball'])
        b_diff = float(np.max(np.abs(traj_ball - b_obs)))

        # Trajectory score
        traj_score = list(traj.scores[step])
        obs_score = list(obs['score'])
        score_match = (traj_score == obs_score)

        step_passed = (p_diff < 1e-4 and b_diff < 1e-4 and score_match)
        if not step_passed:
            all_passed = False

        step_results[f"step_{step}"] = {
            "passed": step_passed,
            "player_max_diff": p_diff,
            "ball_max_diff": b_diff,
            "score_match": score_match
        }

    env.close()
    return {
        "success": all_passed,
        "steps_tested": len(test_steps),
        "details": step_results
    }


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--end-to-end":
        states_p = sys.argv[2]
        traj_p = sys.argv[3]
        report = run_end_to_end_archive_test(states_p, traj_p)
        print("END_TO_END_TEST_JSON:" + json.dumps(report))
    else:
        report = run_equivalence_test(num_steps=50)
        print("EQUIVALENCE_TEST_JSON:" + json.dumps(report))
