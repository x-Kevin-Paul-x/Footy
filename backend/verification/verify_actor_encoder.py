"""Compare live GRF actor inputs with the vendored TiKick reference encoder."""
import ast
import sys
import hashlib
from pathlib import Path
import numpy as np
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy

tree = ast.parse((ROOT / 'third_party/tikick/tmarl/envs/football/football.py').read_text())
wrapper = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RllibGFootball')
methods = [n for n in wrapper.body if isinstance(n, ast.FunctionDef) and n.name in ('raw2vec','get_offside')]
reference = ast.ClassDef(name='ReferenceEncoder',bases=[],keywords=[],body=methods,decorator_list=[])
module = ast.fix_missing_locations(ast.Module(body=[reference],type_ignores=[]))
namespace = {'np':np}
exec(compile(module,'vendored TiKick encoder','exec'),namespace)
encoders = [namespace['ReferenceEncoder']() for _ in range(2)]
for encoder in encoders:
    encoder.num_agents=10
    encoder.last_loffside=np.zeros(11)
    encoder.last_roffside=np.zeros(11)
checkpoint=ROOT / 'checkpoints/tikick/actor.pt'
policy=CPUSinglePolicy(str(checkpoint),str(ROOT / 'third_party/tikick'))
worker=SimulationWorker({'match_id':'actor_encoder_contract','seed_val':1337},max_steps=32,replay_mode=ReplayMode.NONE)
policy.reset_match(worker.match_id,worker.seed_val)
from tmarl.configs.config import get_config
from tmarl.networks.policy_network import PolicyNetwork
import gym
reference_policy = PolicyNetwork(get_config().parse_args([]),
    gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32'),
    gym.spaces.Discrete(33), device=torch.device('cpu'))
reference_policy.load_state_dict(torch.load(checkpoint, map_location='cpu'))
reference_policy.eval()
reference_rnn = torch.zeros((20, 1, 256))
available = torch.zeros((20, 33))
available[:, :20] = 1
try:
    for tick in range(32):
        observed=worker.get_initial_observations()
        expected=np.concatenate([encoders[0].raw2vec(worker.raw_obs[:10]),encoders[1].raw2vec(worker.raw_obs[10:])]).astype(np.float32)
        np.testing.assert_allclose(observed,expected,rtol=0,atol=2e-6)
        actions=policy.evaluate(observed,[worker.match_id])
        with torch.inference_mode():
            reference_actions, _, reference_rnn = reference_policy(expected,
                reference_rnn, torch.ones((20, 1)), available, deterministic=True)
        np.testing.assert_array_equal(actions, reference_actions.numpy().reshape(-1))
        assert len(actions)==20 and np.all((actions>=0)&(actions<20))
        worker.step(actions)
    assert policy.checkpoint_sha256==hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    print('TIKICK_REFERENCE_ENCODER_MATCHED_32_TICKS_BOTH_TEAMS',flush=True)
    print('TIKICK_UPSTREAM_ACTIONS_MATCHED_32_TICKS_BOTH_TEAMS',flush=True)
    print('ACTOR_SHA256',policy.checkpoint_sha256,flush=True)
finally:
    worker.close()
