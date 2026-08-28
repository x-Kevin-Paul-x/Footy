"""Action-Masked Deep Q-Network (DQN) for Football Manager Reinforcement Learning."""

import random
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:
    class MaskedQNetwork(nn.Module):
        """Deep Q-Network with support for continuous state embeddings and action masking."""

        def __init__(self, obs_dim: int = 24, action_dim: int = 5, hidden_dim: int = 128):
            super().__init__()
            self.obs_dim = obs_dim
            self.action_dim = action_dim

            self.feature_net = nn.Sequential(
                nn.Linear(obs_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
            )
            self.value_head = nn.Linear(hidden_dim, 1)
            self.advantage_head = nn.Linear(hidden_dim, action_dim)

        def forward(self, x: torch.Tensor, action_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
            """
            Compute Dueling Q-values with optional action masking.
            Q(s, a) = V(s) + (A(s, a) - mean(A(s, a)))
            """
            features = self.feature_net(x)
            values = self.value_head(features)
            advantages = self.advantage_head(features)
            
            # Dueling architecture aggregation
            q_values = values + (advantages - advantages.mean(dim=-1, keepdim=True))

            if action_mask is not None:
                # Mask out invalid actions by subtracting large constant (1e9)
                # action_mask has 1 for valid, 0 for invalid
                mask = action_mask.to(dtype=q_values.dtype, device=q_values.device)
                large_neg = 1e9
                q_values = q_values - (1.0 - mask) * large_neg

            return q_values


class ReplayBuffer:
    """Experience replay buffer supporting action masks."""

    def __init__(self, capacity: int = 50000):
        self.buffer = deque(maxlen=capacity)

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        action_mask: np.ndarray,
        next_action_mask: np.ndarray,
    ):
        self.buffer.append((state, action, reward, next_state, done, action_mask, next_action_mask))

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones, masks, next_masks = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
            np.array(masks, dtype=np.float32),
            np.array(next_masks, dtype=np.float32),
        )

    def __len__(self) -> int:
        return len(self.buffer)


class DQNAgent:
    """Action-Masked Double Deep Q-Network Agent."""

    def __init__(
        self,
        obs_dim: int = 24,
        action_dim: int = 5,
        hidden_dim: int = 128,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_capacity: int = 50000,
        device: Optional[str] = None,
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.tau = tau
        self.torch_available = TORCH_AVAILABLE

        if not self.torch_available:
            print("Warning: PyTorch not found. DQNAgent running in fallback heuristic mode.")
            return

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.policy_net = MaskedQNetwork(obs_dim, action_dim, hidden_dim).to(self.device)
        self.target_net = MaskedQNetwork(obs_dim, action_dim, hidden_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.memory = ReplayBuffer(buffer_capacity)
        self.training_steps = 0

    def select_action(
        self,
        obs: Union[np.ndarray, List[float]],
        action_mask: Optional[Union[np.ndarray, List[int], List[bool]]] = None,
        training: bool = False,
        epsilon: float = 0.0,
    ) -> int:
        """
        Select action respecting action mask.
        In training, with probability epsilon, select randomly from VALID actions.
        Otherwise, select argmax of masked Q-values.
        """
        if action_mask is None:
            mask_arr = np.ones(self.action_dim, dtype=np.float32)
        else:
            mask_arr = np.array(action_mask, dtype=np.float32)

        valid_actions = np.where(mask_arr > 0.5)[0]
        if len(valid_actions) == 0:
            # Fallback to action 0 if nothing is flagged valid
            valid_actions = np.array([0])
            mask_arr[0] = 1.0

        if training and random.random() < epsilon:
            return int(random.choice(valid_actions))

        if not self.torch_available:
            return int(valid_actions[0])

        self.policy_net.eval()
        with torch.no_grad():
            state_tensor = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            mask_tensor = torch.as_tensor(mask_arr, dtype=torch.float32, device=self.device).unsqueeze(0)
            q_values = self.policy_net(state_tensor, action_mask=mask_tensor)
            action = int(torch.argmax(q_values, dim=1).item())

        # Safety check: ensure selected action is in valid set
        if action not in valid_actions:
            action = int(valid_actions[0])

        return action

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        action_mask: np.ndarray,
        next_action_mask: np.ndarray,
    ):
        if self.torch_available:
            self.memory.push(state, action, reward, next_state, done, action_mask, next_action_mask)

    def train_step(self, batch_size: int = 64) -> Optional[float]:
        """Perform one Double-DQN gradient update with masked target action selection."""
        if not self.torch_available or len(self.memory) < batch_size:
            return None

        states, actions, rewards, next_states, dones, masks, next_masks = self.memory.sample(batch_size)

        state_tensor = torch.as_tensor(states, dtype=torch.float32, device=self.device)
        action_tensor = torch.as_tensor(actions, dtype=torch.int64, device=self.device).unsqueeze(1)
        reward_tensor = torch.as_tensor(rewards, dtype=torch.float32, device=self.device).unsqueeze(1)
        next_state_tensor = torch.as_tensor(next_states, dtype=torch.float32, device=self.device)
        done_tensor = torch.as_tensor(dones, dtype=torch.float32, device=self.device).unsqueeze(1)
        mask_tensor = torch.as_tensor(masks, dtype=torch.float32, device=self.device)
        next_mask_tensor = torch.as_tensor(next_masks, dtype=torch.float32, device=self.device)

        self.policy_net.train()
        current_q = self.policy_net(state_tensor, action_mask=mask_tensor).gather(1, action_tensor)

        with torch.no_grad():
            # Double DQN: Select best action using policy net with mask, evaluate with target net
            next_policy_q = self.policy_net(next_state_tensor, action_mask=next_mask_tensor)
            best_next_actions = torch.argmax(next_policy_q, dim=1, keepdim=True)

            next_target_q = self.target_net(next_state_tensor, action_mask=next_mask_tensor)
            target_q_val = next_target_q.gather(1, best_next_actions)

            expected_q = reward_tensor + (1.0 - done_tensor) * self.gamma * target_q_val

        loss = nn.functional.smooth_l1_loss(current_q, expected_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        # Polyak soft update for target net
        for target_param, policy_param in zip(self.target_net.parameters(), self.policy_net.parameters()):
            target_param.data.copy_(self.tau * policy_param.data + (1.0 - self.tau) * target_param.data)

        self.training_steps += 1
        return float(loss.item())

    def save(self, path: Union[str, Path]):
        if not self.torch_available:
            return
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "policy_state_dict": self.policy_net.state_dict(),
                "target_state_dict": self.target_net.state_dict(),
                "obs_dim": self.obs_dim,
                "action_dim": self.action_dim,
                "training_steps": self.training_steps,
            },
            str(path),
        )

    def load(self, path: Union[str, Path]):
        if not self.torch_available:
            return
        path = Path(path)
        if not path.exists():
            print(f"Warning: Model file not found at {path}")
            return
        checkpoint = torch.load(str(path), map_location=self.device)
        self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
        self.target_net.load_state_dict(checkpoint.get("target_state_dict", checkpoint["policy_state_dict"]))
        self.training_steps = checkpoint.get("training_steps", 0)
        self.policy_net.eval()
        self.target_net.eval()
