import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
w = SimulationWorker({'match_id': 'perspective_probe'}, max_steps=10, replay_mode=ReplayMode.NONE)
left, right = w.raw_obs[0], w.raw_obs[10]
print('ACTIVE', [o['active'] for o in w.raw_obs], flush=True)
print('RIGHT_ALREADY_CANONICAL', np.allclose(right['left_team'], -left['right_team']), flush=True)
print('AGENT_CAN_PLAY_RIGHT', w.env.unwrapped._agent.can_play_right(), flush=True)
w.close()
