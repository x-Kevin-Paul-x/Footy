import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
w = SimulationWorker({'match_id': 'half_probe'}, max_steps=1510, replay_mode=ReplayMode.NONE)
core = w.env.unwrapped._env
original = core._retrieve_observation
def trace():
    in_play = original()
    o = core._observation
    if 1498 <= w.step_idx <= 1502:
        print(w.step_idx, in_play, o['steps_left'], o['game_mode'], o['ball'], flush=True)
    return in_play
core._retrieve_observation = trace
for _ in range(1510):
    w.step(np.zeros(20, dtype=np.int64))
print('EVENTS', w.events, flush=True)
w.close()
