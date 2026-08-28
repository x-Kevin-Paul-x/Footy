"""Gymnasium-compatible Football Simulation Environment for RL Manager Training."""

import random
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False


class TransferMarketSim:
    def __init__(self):
        self.transfer_list: List[Dict[str, Any]] = []
        self.free_agents: List[Dict[str, Any]] = []
        self.current_week = 0

    def seed_market(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.transfer_list = [
            {"id": i, "name": f"Player_{i}", "position": "FWD", "market_value": 5_000_000, "rating": 72}
            for i in range(1, 15)
        ]
        self.free_agents = [
            {"id": i, "name": f"FreeAgent_{i}", "position": "MID", "market_value": 0, "rating": 67}
            for i in range(15, 25)
        ]

    def set_week(self, week: int):
        self.current_week = week

    def get_current_window(self) -> Optional[str]:
        # Summer window: weeks 0-7, Winter window: weeks 18-21
        if self.current_week < 8:
            return "summer"
        elif 18 <= self.current_week <= 21:
            return "winter"
        return None

    def is_transfer_window_open(self) -> bool:
        return self.get_current_window() is not None


class FootyEnv:
    """
    Footy environment with continuous 24-dimensional feature embeddings
    and real-time Action Masking support for transfer budgeting.
    """
    ACTION_DO_NOTHING = 0
    ACTION_SCOUT_OR_YOUTH = 1
    ACTION_BUY_CHEAP = 2
    ACTION_BUY_VALUE = 3
    ACTION_BUY_STAR = 4

    ACTION_COSTS = {
        0: 0,
        1: 500_000,
        2: 4_000_000,
        3: 18_000_000,
        4: 50_000_000,
    }

    ACTION_RATING_BOOSTS = {
        0: 0.0,
        1: 0.2,
        2: 0.5,
        3: 1.2,
        4: 2.5,
    }

    def __init__(self, num_teams: int = 20, season_length: int = 38, fast_mode: bool = True):
        self.num_teams = num_teams
        self.season_length = season_length
        self.fast_mode = fast_mode
        self.transfer_market = TransferMarketSim()

        self.obs_dim = 24
        self.action_dim = 5

        # Gym spaces if Gymnasium is present
        if GYM_AVAILABLE:
            self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(self.obs_dim,), dtype=np.float32)
            self.action_space = spaces.Discrete(self.action_dim)

        self.reset()

    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.season = 1
        self.week = 0
        self.points = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.goals_for = 0
        self.goals_against = 0
        
        self.budget = float(random.randint(25_000_000, 120_000_000))
        self.initial_budget = self.budget
        self.squad_size = random.randint(22, 28)
        self.avg_rating = float(random.randint(68, 80))
        self.avg_potential = float(min(90, self.avg_rating + random.randint(3, 10)))
        self.avg_age = float(random.uniform(24.0, 28.5))
        self.position = random.randint(1, self.num_teams)
        self.form = 0.5
        self.action_history: Dict[int, int] = {i: 0 for i in range(self.action_dim)}

        self.transfer_market.seed_market(seed)
        self.transfer_market.set_week(self.week)

        obs = self._get_observation()
        info = self._get_info()
        return obs, info

    def get_action_mask(self) -> np.ndarray:
        """
        Compute binary action mask [5,] where 1 = valid, 0 = invalid.
        Prevents managers from buying players when budget is insufficient or window is closed.
        """
        mask = np.ones(self.action_dim, dtype=np.float32)
        window_open = self.transfer_market.is_transfer_window_open()

        # Action 0 (Do Nothing): always valid
        mask[0] = 1.0

        # Action 1 (Scout/Youth Academy): valid if budget >= £500k
        mask[1] = 1.0 if self.budget >= self.ACTION_COSTS[1] else 0.0

        # Action 2 (Buy Cheap/Youth): valid if window open, budget >= £4M, squad size < 32
        mask[2] = 1.0 if (window_open and self.budget >= self.ACTION_COSTS[2] and self.squad_size < 32) else 0.0

        # Action 3 (Buy Value/Prime): valid if window open, budget >= £18M, squad size < 30
        mask[3] = 1.0 if (window_open and self.budget >= self.ACTION_COSTS[3] and self.squad_size < 30) else 0.0

        # Action 4 (Buy Star): valid if window open, budget >= £50M, squad size < 30
        mask[4] = 1.0 if (window_open and self.budget >= self.ACTION_COSTS[4] and self.squad_size < 30) else 0.0

        return mask

    def _get_observation(self) -> np.ndarray:
        obs = np.zeros(self.obs_dim, dtype=np.float32)
        window_open = 1.0 if self.transfer_market.is_transfer_window_open() else 0.0
        
        # 1. Financial Embeddings (0-2)
        obs[0] = np.clip(self.budget / 200_000_000.0, 0.0, 1.0)
        obs[1] = np.clip((self.squad_size * 40_000 * 52) / max(1.0, self.budget * 0.5), 0.0, 1.0) # Wage utilization proxy
        obs[2] = np.clip(self.budget / max(1.0, self.initial_budget), 0.0, 1.0)

        # 2. Squad Quality & Composition (3-8)
        obs[3] = np.clip(self.squad_size / 35.0, 0.0, 1.0)
        obs[4] = np.clip(self.avg_age / 40.0, 0.0, 1.0)
        obs[5] = np.clip(self.avg_rating / 100.0, 0.0, 1.0)
        obs[6] = np.clip(self.avg_potential / 100.0, 0.0, 1.0)
        obs[7] = 0.8  # Positional balance index
        obs[8] = 0.05 # Injury rate

        # 3. League Context & Performance (9-15)
        obs[9] = np.clip(self.position / float(self.num_teams), 0.0, 1.0)
        obs[10] = np.clip(self.points / 100.0, 0.0, 1.0)
        obs[11] = np.clip((self.goals_for - self.goals_against + 50) / 100.0, 0.0, 1.0)
        obs[12] = np.clip((self.season_length - self.week) / float(self.season_length), 0.0, 1.0)
        obs[13] = window_open
        obs[14] = 0.5 # Market inflation index
        obs[15] = self.form

        # 4. Squad Health & Profiles (16-19)
        obs[16] = 0.25 # Youth ratio
        obs[17] = 0.15 # Star ratio
        obs[18] = self.wins / max(1, self.week) if self.week > 0 else 0.3
        obs[19] = self.draws / max(1, self.week) if self.week > 0 else 0.2

        # 5. Goalscoring Metrics (20-23)
        obs[20] = np.clip((self.goals_for / max(1, self.week)) / 3.0, 0.0, 1.0)
        obs[21] = np.clip((self.goals_against / max(1, self.week)) / 3.0, 0.0, 1.0)
        obs[22] = 0.5  # Tactical familiarity
        obs[23] = 0.5  # Team morale

        return obs

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.week += 1
        self.transfer_market.set_week(self.week)
        action_mask = self.get_action_mask()

        # Handle Action Execution
        self.action_history[action] = self.action_history.get(action, 0) + 1
        cost = self.ACTION_COSTS.get(action, 0)
        boost = self.ACTION_RATING_BOOSTS.get(action, 0.0)

        # Penalize severely if agent forced an illegal/unaffordable action (should be prevented by mask)
        action_penalty = 0.0
        if action_mask[action] < 0.5:
            action_penalty = -5.0
            cost = 0
            boost = 0.0

        if cost > 0 and self.budget >= cost:
            self.budget -= cost
            self.avg_rating = min(92.0, self.avg_rating + boost)
            if action in (2, 3, 4):
                self.squad_size += 1

        # Match outcome simulation based on squad rating
        base_win_prob = np.clip((self.avg_rating - 65.0) / 35.0 * 0.7 + 0.15, 0.05, 0.85)
        roll = random.random()
        if roll < base_win_prob:
            pts = 3
            self.wins += 1
            gf = random.randint(1, 4)
            ga = random.randint(0, 1)
            self.form = min(1.0, self.form + 0.1)
        elif roll < base_win_prob + 0.25:
            pts = 1
            self.draws += 1
            gf = random.randint(0, 2)
            ga = gf
        else:
            pts = 0
            self.losses += 1
            gf = random.randint(0, 1)
            ga = random.randint(1, 3)
            self.form = max(0.0, self.form - 0.1)

        self.points += pts
        self.goals_for += gf
        self.goals_against += ga

        # Update table position
        expected_rank = max(1, min(self.num_teams, int(self.num_teams - (self.points / max(1, self.week * 3)) * self.num_teams) + 1))
        self.position = expected_rank

        # Reward formulation: points gain + table rank bonus + financial sustainability + action legality
        reward = float(pts * 2.0) + (1.0 if self.position <= 4 else 0.0) + action_penalty
        
        current_season = self.season
        terminated = self.week >= self.season_length
        completed_points = self.points
        completed_pos = self.position

        if terminated:
            # End of season bonus for high finish and positive balance
            if self.position == 1:
                reward += 20.0
            elif self.position <= 4:
                reward += 10.0
            if self.budget > self.initial_budget * 0.5:
                reward += 5.0
            
            # Rollover for next season
            self.season += 1
            self.week = 0
            self.points = 0

        obs = self._get_observation()
        info = {
            "season": current_season,
            "week": self.week,
            "points": completed_points,
            "position": completed_pos,
            "completed_season_points": completed_points,
            "completed_season_position": completed_pos,
            "final_position": completed_pos,
            "final_points": completed_points,
            "final_budget": self.budget,
            "final_squad_size": self.squad_size,
            "actions": self.action_history.copy(),
            "action_mask": self.get_action_mask(),
        }
        return obs, reward, terminated, False, info

    def _get_info(self) -> Dict[str, Any]:
        return {
            "season": self.season,
            "week": self.week,
            "points": self.points,
            "position": self.position,
            "final_position": self.position,
            "final_points": self.points,
            "final_budget": self.budget,
            "final_squad_size": self.squad_size,
            "actions": self.action_history.copy(),
            "action_mask": self.get_action_mask(),
        }

    def close(self):
        pass
