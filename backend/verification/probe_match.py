import sys
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy

w = SimulationWorker({'match_id': 'duration_probe', 'seed_val': 1337}, max_steps=3200, replay_mode=ReplayMode.NONE)
p = CPUSinglePolicy(str(root / 'checkpoints/tikick/actor.pt'), str(root / 'third_party/tikick'))
p.reset_match(w.match_id, w.seed_val)
obs = w.get_initial_observations()
last_mode = None
while not w.done and w.step_idx < w.max_steps:
    obs, done, _ = w.step(p.evaluate(obs, [w.match_id]))
    o = w.raw_obs[0]
    if o['game_mode'] != last_mode or 1498 <= w.step_idx <= 1510:
        print(json.dumps({'step': w.step_idx, 'steps_left': o['steps_left'], 'mode': o['game_mode'], 'score': o['score'], 'ball': o['ball'].tolist()}), flush=True)
        last_mode = o['game_mode']
print('DONE', w.done, w.step_idx, flush=True)
print('INTERVALS', w.events, flush=True)
w.close()
