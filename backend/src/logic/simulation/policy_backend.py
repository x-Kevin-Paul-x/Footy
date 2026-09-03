"""
Footy Policy Backend Subsystem.
Implements pluggable inference backends for TiKick Deep Reinforcement Learning models:
- CPUSinglePolicy: Independent per-worker CPU inference (zero IPC overhead)
- CPUBatchPolicy: Central multi-threaded CPU batched inference
- CUDABatchPolicy: Central GPU batched inference on RTX 5070 with recurrent state invariance
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import numpy as np
import torch
try:
    import gym
except ImportError:
    try:
        import gymnasium as gym
    except ImportError:
        gym = None


class TiKickModelConfig:
    hidden_size = 256
    gain = 0.01
    use_orthogonal = False
    activation_id = 1
    use_policy_active_masks = False
    use_naive_recurrent_policy = False
    use_recurrent_policy = True
    use_influence_policy = False
    influence_layer_N = 1
    use_policy_vhead = False
    recurrent_N = 1
    use_feature_normalization = True
    use_conv1d = False
    stacked_frames = 1
    layer_N = 3


class PolicyBackend(ABC):
    """Abstract interface for TiKick neural network policy evaluation."""

    @abstractmethod
    def evaluate(
        self,
        observations: np.ndarray,
        match_ids: List[str],
        masks: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Evaluates policy for a batch of agents.
        Args:
            observations: (N_agents, 268) float32 numpy array
            match_ids: list of match_id strings corresponding to each group of 20 agents
            masks: optional (N_agents, 1) float32 array
        Returns:
            actions: (N_agents,) int64 array of discrete action indices [0..32]
        """
        pass

    @abstractmethod
    def reset_match(self, match_id: str):
        """Resets recurrent state associated with a match_id."""
        pass


class CPUSinglePolicy(PolicyBackend):
    """
    Independent per-worker CPU policy.
    Loaded directly inside worker process with OMP_NUM_THREADS=1 for zero IPC overhead.
    """

    def __init__(self, ckpt_path: str, tikick_dir: str):
        if tikick_dir and tikick_dir not in sys.path:
            sys.path.insert(0, tikick_dir)
        from tmarl.networks.policy_network import PolicyNetwork

        torch.set_num_threads(1)
        self.device = torch.device('cpu')
        obs_space = gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32')
        action_space = gym.spaces.Discrete(33)
        self.policy = PolicyNetwork(TiKickModelConfig(), obs_space, action_space, device=self.device)
        state_dict = torch.load(ckpt_path, map_location=self.device)
        self.policy.load_state_dict(state_dict)
        self.policy.eval()

        self.rnn_states = torch.zeros((20, 1, 256), dtype=torch.float32, device=self.device)
        self.masks = torch.ones((20, 1), dtype=torch.float32, device=self.device)
        self.avail = torch.zeros((20, 33), dtype=torch.float32, device=self.device)
        self.avail[:, :20] = 1.0

    def evaluate(
        self,
        observations: np.ndarray,
        match_ids: List[str],
        masks: Optional[np.ndarray] = None
    ) -> np.ndarray:
        obs_t = torch.from_numpy(observations).to(self.device)
        with torch.inference_mode():
            actions_t, _, self.rnn_states = self.policy(
                obs_t, self.rnn_states, self.masks, self.avail, deterministic=True
            )
        return actions_t.detach().cpu().numpy().reshape(-1)

    def reset_match(self, match_id: str, seed_val: Optional[int] = None):
        self.rnn_states = torch.zeros((20, 1, 256), dtype=torch.float32, device=self.device)
        self.masks = torch.ones((20, 1), dtype=torch.float32, device=self.device)
        self.avail = torch.zeros((20, 33), dtype=torch.float32, device=self.device)
        self.avail[:, :20] = 1.0
        if seed_val is not None:
            torch.manual_seed(seed_val % (2**31 - 1))


class CUDABatchPolicy(PolicyBackend):
    """
    Centralized batched GPU policy running on CUDA.
    Maintains persistent match_id -> RNN_hidden_state mapping to guarantee bit-exact determinism.
    """

    def __init__(self, ckpt_path: str, tikick_dir: str, device: str = "cuda"):
        if tikick_dir and tikick_dir not in sys.path:
            sys.path.insert(0, tikick_dir)
        from tmarl.networks.policy_network import PolicyNetwork

        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        if self.device.type == 'cuda':
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

        obs_space = gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32')
        action_space = gym.spaces.Discrete(33)
        self.policy = PolicyNetwork(TiKickModelConfig(), obs_space, action_space, device=self.device)
        state_dict = torch.load(ckpt_path, map_location=self.device)
        self.policy.load_state_dict(state_dict)
        self.policy.eval()

        # Persistent recurrent state index keyed by match_id
        self.match_rnn_states: Dict[str, torch.Tensor] = {}

    def get_or_create_rnn_state(self, match_id: str) -> torch.Tensor:
        if match_id not in self.match_rnn_states:
            self.match_rnn_states[match_id] = torch.zeros(
                (20, 1, 256), dtype=torch.float32, device=self.device
            )
        return self.match_rnn_states[match_id]

    def evaluate(
        self,
        observations: np.ndarray,
        match_ids: List[str],
        masks: Optional[np.ndarray] = None
    ) -> np.ndarray:
        num_matches = len(match_ids)
        total_agents = num_matches * 20
        if total_agents == 0:
            return np.empty((0,), dtype=np.int64)

        # Assemble stacked RNN states in deterministic match_id order
        rnn_list = [self.get_or_create_rnn_state(m_id) for m_id in match_ids]
        stacked_rnn = torch.cat(rnn_list, dim=0)

        obs_t = torch.from_numpy(observations).to(self.device)
        masks_t = torch.ones((total_agents, 1), dtype=torch.float32, device=self.device) if masks is None else torch.from_numpy(masks).to(self.device)
        avail_t = torch.zeros((total_agents, 33), dtype=torch.float32, device=self.device)
        avail_t[:, :20] = 1.0

        with torch.inference_mode():
            actions_t, _, next_rnn = self.policy(
                obs_t, stacked_rnn, masks_t, avail_t, deterministic=True
            )

        # Disperse next RNN hidden states back to persistent match_id map
        for i, m_id in enumerate(match_ids):
            self.match_rnn_states[m_id] = next_rnn[i * 20:(i + 1) * 20].clone()

        return actions_t.detach().cpu().numpy().reshape(-1)

    def reset_match(self, match_id: str):
        if match_id in self.match_rnn_states:
            del self.match_rnn_states[match_id]


class CPUBatchPolicy(CUDABatchPolicy):
    """Centralized batched CPU policy running on PyTorch CPU backend."""

    def __init__(self, ckpt_path: str, tikick_dir: str):
        super().__init__(ckpt_path, tikick_dir, device="cpu")
