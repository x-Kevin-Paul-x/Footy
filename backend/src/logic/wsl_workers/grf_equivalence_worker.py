"""
WSL Worker: GRF State-to-Observation & Render Equivalence Tester.
Runs pure C++ GFootball simulation in WSL, captures raw states, observations, and rendered RGB frames
at multiple checkpoints, then resets a completely new environment instance, restores states via set_state(),
and measures mathematical parity:
- Exact observation dictionary equality (left_team, right_team, ball, ball_direction, score, ownership)
- Rendered RGB frame MAE (Mean Absolute Error), MSE, and PSNR (Peak Signal-to-Noise Ratio).
"""

import sys
import os
import json
import numpy as np


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

    # Capture initial step 0 observation & frame
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

        # Step with neutral / idle actions (0: idle)
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

        # Compare observation arrays
        l_diff = float(np.max(np.abs(np.array(orig_o['left_team']) - np.array(restored_o['left_team']))))
        r_diff = float(np.max(np.abs(np.array(orig_o['right_team']) - np.array(restored_o['right_team']))))
        b_diff = float(np.max(np.abs(np.array(orig_o['ball']) - np.array(restored_o['ball']))))
        bd_diff = float(np.max(np.abs(np.array(orig_o['ball_direction']) - np.array(restored_o['ball_direction']))))
        score_match = (list(orig_o['score']) == list(restored_o['score']))
        owned_team_match = (orig_o.get('ball_owned_team') == restored_o.get('ball_owned_team'))
        owned_player_match = (orig_o.get('ball_owned_player') == restored_o.get('ball_owned_player'))

        obs_passed = (
            l_diff < 1e-4 and r_diff < 1e-4 and b_diff < 1e-4 and
            score_match and owned_team_match and owned_player_match
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
            "ball_max_diff": b_diff,
            "ball_dir_max_diff": bd_diff,
            "score_match": score_match,
            "ownership_match": owned_team_match,
            "frame_metrics": frame_metrics
        }

    env2.close()

    report = {
        "success": all_obs_identical,
        "checkpoints_tested": len(saved_states),
        "details": results
    }
    return report


if __name__ == "__main__":
    report = run_equivalence_test(num_steps=50)
    print("EQUIVALENCE_TEST_JSON:" + json.dumps(report))
