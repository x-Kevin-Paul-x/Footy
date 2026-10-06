"""Compare previous restricted/overridden play with upstream actor settings."""
import json
import sys
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from logic.simulation.match_executor import GRFMatchExecutor, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy

output = root / 'verification/season_20261004_001100/actor_comparison'
output.mkdir(exist_ok=True)
policy = CPUSinglePolicy(str(root / 'checkpoints/tikick/actor.pt'),
                         str(root / 'third_party/tikick'))
results = []
for profile in ('previous_restricted', 'tikick_kaggle'):
    spec = {'match_id': profile, 'seed_val': 1337, 'max_steps': 3200,
            'home_team': 'Home', 'away_team': 'Away',
            'apply_tactical_bias': profile == 'previous_restricted'}
    if profile == 'tikick_kaggle':
        spec.update(trace_npz=str(output / 'trace_tikick_kaggle.npz'),
                    states_file=str(output / 'trace_tikick_kaggle.grfstate'))
    worker = GRFMatchExecutor(spec, replay_mode=ReplayMode.FULL_STATE
        if profile == 'tikick_kaggle' else ReplayMode.NONE)
    policy.reset_match(worker.match_id, worker.seed_val)
    if profile == 'previous_restricted':
        policy.avail[:, 19] = 0
    worker.policy_provenance = dict(name='TiKick actor',
        checkpoint_sha256=policy.checkpoint_sha256, direct_actions=19,
        builtin_ai_allowed=profile == 'tikick_kaggle',
        inference_profile=profile, available_actions=19 if profile == 'previous_restricted' else 20)
    observations = worker.get_initial_observations()
    histogram = np.zeros(20, dtype=int)
    crowded = 0
    while not worker.done and worker.step_idx < worker.max_steps:
        actions = policy.evaluate(observations, [worker.match_id])
        histogram += np.bincount(actions, minlength=20)
        step = worker.step_idx
        observations, _, _ = worker.step(actions)
        if profile == 'tikick_kaggle':
            np.testing.assert_array_equal(worker.rec_actions[step], actions)
        o = worker.raw_obs[0]
        if int(o['game_mode']) == 0:
            for team in ('left_team', 'right_team'):
                distances = np.linalg.norm(np.asarray(o[team]) - o['ball'][:2], axis=1)
                crowded += int(np.count_nonzero(distances < .10) >= 3)
    result = worker.finalize()
    row = dict(profile=profile, score=list(result.score), steps=worker.step_idx,
               complete=result.match_complete, action_counts=histogram.tolist(),
               crowded_team_frames=crowded, checkpoint_sha256=policy.checkpoint_sha256)
    results.append(row)
    print(json.dumps(row), flush=True)
    worker.close()
(output / 'comparison.json').write_text(json.dumps(results, indent=2))
