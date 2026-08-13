"""Reinforcement learning and state embedding models for football manager decision making."""

from collections import defaultdict
import random
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class ContinuousStateEncoder:
    """
    Vectorized continuous feature encoder for football manager states.
    Produces a 24-dimensional normalized embedding vector eliminating state sparsity.
    """

    def encode_continuous_state(self, raw_state: Dict[str, Any]) -> np.ndarray:
        obs = np.zeros(24, dtype=np.float32)
        if not raw_state:
            return obs

        squad_comp = raw_state.get("squad_composition", {})
        financial = raw_state.get("financial_health", {})
        performance = raw_state.get("team_performance", {})
        market = raw_state.get("market_conditions", {})
        recent = raw_state.get("recent_performance", {})

        # 1. Financial Embeddings (0-2)
        transfer_budget = float(financial.get("transfer_budget", raw_state.get("budget", 0)))
        total_budget = float(financial.get("total_budget", max(1.0, transfer_budget)))
        wage_budget = float(financial.get("wage_budget", 1.0))
        total_wages = float(financial.get("total_wages", 0.0))

        obs[0] = np.clip(transfer_budget / 200_000_000.0, 0.0, 1.0)
        obs[1] = np.clip(total_wages / max(1.0, wage_budget), 0.0, 1.0)
        obs[2] = np.clip(transfer_budget / max(1.0, total_budget), 0.0, 1.0)

        # 2. Squad Quality & Composition (3-8)
        total_players = float(squad_comp.get("total_players", raw_state.get("squad_size", 25)))
        avg_age = float(squad_comp.get("average_age", raw_state.get("avg_age", 26.0)))
        avg_rating = float(squad_comp.get("average_rating", raw_state.get("avg_rating", 70.0)))
        avg_potential = float(raw_state.get("avg_potential", avg_rating + 4.0))

        positions = squad_comp.get("positions", {})
        gk = float(positions.get("GK", 2))
        df = float(positions.get("DEF", 8))
        mf = float(positions.get("MID", 8))
        fw = float(positions.get("FWD", 6))

        obs[3] = np.clip(total_players / 35.0, 0.0, 1.0)
        obs[4] = np.clip(avg_age / 40.0, 0.0, 1.0)
        obs[5] = np.clip(avg_rating / 100.0, 0.0, 1.0)
        obs[6] = np.clip(avg_potential / 100.0, 0.0, 1.0)
        # Balance index across 4 core groups
        obs[7] = np.clip((gk / 4.0 + df / 10.0 + mf / 10.0 + fw / 8.0) / 4.0, 0.0, 1.0)
        obs[8] = float(raw_state.get("injured_pct", 0.0))

        # 3. League Context & Performance (9-15)
        position = float(raw_state.get("position", 10))
        points = float(raw_state.get("points", 0))
        goal_diff = float(raw_state.get("goal_diff", 0))
        weeks_remaining = float(raw_state.get("weeks_remaining", 38))
        window_open = 1.0 if (market.get("transfer_window_open", raw_state.get("transfer_window_open", False))) else 0.0

        obs[9] = np.clip(position / 20.0, 0.0, 1.0)
        obs[10] = np.clip(points / 100.0, 0.0, 1.0)
        obs[11] = np.clip((goal_diff + 50.0) / 100.0, 0.0, 1.0)
        obs[12] = np.clip(weeks_remaining / 38.0, 0.0, 1.0)
        obs[13] = window_open
        obs[14] = np.clip(float(raw_state.get("market_inflation", 1.0)) / 2.0, 0.0, 1.0)
        obs[15] = float(performance.get("form", raw_state.get("form", 0.5)))

        # 4. Squad Health & Profiles (16-19)
        obs[16] = float(raw_state.get("youth_ratio", 0.25))
        obs[17] = float(raw_state.get("star_ratio", 0.15))
        obs[18] = float(recent.get("win_rate", raw_state.get("recent_win_rate", 0.35)))
        obs[19] = float(recent.get("draw_rate", raw_state.get("recent_draw_rate", 0.25)))

        # 5. Goalscoring Metrics (20-23)
        obs[20] = np.clip(float(performance.get("goals_per_game", raw_state.get("goals_per_game", 1.2))) / 3.0, 0.0, 1.0)
        obs[21] = np.clip(float(performance.get("conceded_per_game", raw_state.get("conceded_per_game", 1.1))) / 3.0, 0.0, 1.0)
        obs[22] = 0.5  # Tactical familiarity
        obs[23] = 0.5  # Team morale

        return obs


class StateEncoder:
    """Convert raw states into discrete states for legacy Q-learning."""

    def encode_state(self, raw_state: dict) -> tuple:
        squad = self.encode_squad_state(raw_state)
        financial = self.encode_financial_state(raw_state)
        performance = self.encode_performance_state(raw_state)
        market = self.encode_market_state(raw_state)
        return squad + financial + performance + market

    @staticmethod
    def discretize_value(value: float, bins: List[float]) -> int:
        for i, threshold in enumerate(bins):
            if value <= threshold:
                return i
        return len(bins)

    def encode_squad_state(self, raw_state: Dict) -> Tuple:
        squad_data = raw_state.get("squad_composition", {})
        total_players = squad_data.get("total_players", 0)
        avg_age = squad_data.get("average_age", 25)
        return (total_players / 30, avg_age / 40)

    def encode_financial_state(self, raw_state: Dict) -> Tuple:
        financial = raw_state.get("financial_health", {})
        transfer_budget = financial.get("transfer_budget", 0)
        total_budget = financial.get("total_budget", 1)
        budget_used = 1 - (transfer_budget / total_budget) if total_budget > 0 else 1
        budget_state = self.discretize_value(budget_used, [0.2, 0.4, 0.6, 0.8])
        return (budget_state,)

    def encode_performance_state(self, raw_state: Dict) -> Tuple:
        performance = raw_state.get("team_performance", {})
        form = performance.get("form", 0.5)
        form_state = self.discretize_value(form, [0.2, 0.4, 0.6, 0.8])
        return (form_state,)

    def encode_market_state(self, raw_state: Dict) -> Tuple:
        season_progress = (raw_state.get("current_day", 0) % 365) / 365
        season_state = self.discretize_value(season_progress, [0.25, 0.5, 0.75])
        return (season_state,)


class QTable:
    """Q-table implementation with defaultdict."""

    def __init__(self):
        self.q_values = defaultdict(lambda: defaultdict(float))
        self.learning_rate = 0.3
        self.gamma = 0.85

    def get_value(self, state: Tuple, action: Any) -> float:
        return self.q_values[state][action]

    def update(
        self,
        state: Tuple,
        action: Any,
        reward: float,
        next_state: Tuple,
        possible_next_actions: List[Any],
    ):
        current_q = self.get_value(state, action)
        next_max_q = max([self.get_value(next_state, a) for a in possible_next_actions], default=0.0)
        new_q = current_q + self.learning_rate * (reward + self.gamma * next_max_q - current_q)
        self.q_values[state][action] = new_q


class ManagerBrain:
    """Reinforcement learning component utilizing Action-Masked DQN and continuous state embeddings."""

    def __init__(self, profile, use_dqn: bool = True):
        self.profile = profile
        self.discrete_encoder = StateEncoder()
        self.continuous_encoder = ContinuousStateEncoder()
        self.use_dqn = use_dqn
        self.dqn_agent = None

        if use_dqn:
            try:
                from ml.dqn_agent import DQNAgent, TORCH_AVAILABLE
                if TORCH_AVAILABLE:
                    self.dqn_agent = DQNAgent(
                        obs_dim=24,
                        action_dim=5,
                        hidden_dim=128,
                        learning_rate=3e-4,
                        gamma=0.99,
                    )
                else:
                    self.use_dqn = False
            except Exception as e:
                print(f"Warning: DQN agent initialization error: {e}")
                self.use_dqn = False

        # Tabular Q-tables for legacy fallback
        self.match_qtable = QTable()
        self.transfer_qtable = QTable()
        self.training_qtable = QTable()
        self.lineup_qtable = QTable()

        self.base_exploration_rate = 0.8
        self.min_exploration_rate = 0.2
        self.episode_rewards = []

    def get_exploration_rate(self) -> float:
        base_rate = max(
            self.min_exploration_rate,
            self.base_exploration_rate * (1 - len(self.episode_rewards) / 1000),
        )
        return self.profile.get_risk_adjusted_exploration_rate(base_rate)

    def encode_state(self, raw_state: Dict) -> Tuple:
        """Legacy discrete tuple encoding."""
        squad_state = self.discrete_encoder.encode_squad_state(raw_state)
        financial_state = self.discrete_encoder.encode_financial_state(raw_state)
        performance_state = self.discrete_encoder.encode_performance_state(raw_state)
        market_state = self.discrete_encoder.encode_market_state(raw_state)
        return squad_state + financial_state + performance_state + market_state

    def get_continuous_embedding(self, raw_state: Dict) -> np.ndarray:
        """Continuous 24-dim state vector for DQN."""
        return self.continuous_encoder.encode_continuous_state(raw_state)

    def load_model(self, path: str):
        """Load trained DQN weights."""
        if self.dqn_agent:
            self.dqn_agent.load(path)
            print(f"ManagerBrain: Successfully loaded DQN model from {path}")
        else:
            print("Notice: DQN agent not initialized; model weights not loaded.")

    def select_action(
        self,
        state: Any,
        possible_actions: List[Any],
        action_type: str = "match",
        raw_state: Optional[Dict] = None,
        action_mask: Optional[Union[np.ndarray, List[float], List[int]]] = None,
    ) -> Any:
        """Select action using Action-Masked DQN or epsilon-greedy Q-learning."""
        if self.use_dqn and self.dqn_agent and raw_state and len(possible_actions) == 5:
            obs = self.get_continuous_embedding(raw_state)
            action_idx = self.dqn_agent.select_action(
                obs,
                action_mask=action_mask,
                training=False,
                epsilon=0.0,
            )
            return possible_actions[action_idx]

        # Fallback to tabular Q-learning / heuristic
        qtable = self._get_qtable(action_type)
        if random.random() < self.get_exploration_rate():
            return random.choice(possible_actions)

        state_tuple = state if isinstance(state, tuple) else self.encode_state(raw_state or {})
        return max(possible_actions, key=lambda a: qtable.get_value(state_tuple, a))

    def _get_qtable(self, action_type: str) -> QTable:
        if action_type == "match":
            return self.match_qtable
        elif action_type == "transfer":
            return self.transfer_qtable
        elif action_type == "training":
            return self.training_qtable
        elif action_type == "lineup":
            return self.lineup_qtable
        raise ValueError(f"Unknown action type: {action_type}")

    def learn(
        self,
        state: Tuple,
        action: Any,
        reward: float,
        next_state: Tuple,
        possible_next_actions: List[Any],
        action_type: str = "match",
    ):
        qtable = self._get_qtable(action_type)
        if action_type == "match":
            reward = self.profile.calculate_match_reward({"reward": reward})
        elif action_type == "transfer":
            reward = self.profile.calculate_transfer_reward({"reward": reward})

        qtable.update(state, action, reward, next_state, possible_next_actions)
        self.episode_rewards.append(reward)

    def get_stats(self) -> Dict[str, Any]:
        recent = self.episode_rewards[-100:] if self.episode_rewards else []
        return {
            "total_episodes": len(self.episode_rewards),
            "recent_avg_reward": sum(recent) / len(recent) if recent else 0.0,
            "exploration_rate": self.get_exploration_rate(),
            "use_dqn": self.use_dqn,
            "has_trained_dqn": self.dqn_agent is not None,
        }
