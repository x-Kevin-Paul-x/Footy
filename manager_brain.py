"""Q-learning implementation for football manager decision making."""

from typing import Dict, Tuple, List, Any
import random
from collections import defaultdict

class StateEncoder:
    """Convert raw states into discrete states for Q-learning."""
    
    @staticmethod
    def discretize_value(value: float, bins: List[float]) -> int:
        """Convert a continuous value into a discrete bin index."""
        for i, threshold in enumerate(bins):
            if value <= threshold:
                return i
        return len(bins)

    def encode_squad_state(self, raw_state: Dict) -> Tuple:
        """Encode squad-related state information."""
        # Squad size bins: [15, 18, 21, 23, 25]
        squad_size = self.discretize_value(
            raw_state["squad_composition"]["total_players"],
            [15, 18, 21, 23, 25]
        )
        
        # Average age bins: [22, 24, 26, 28, 30]
        age_groups = raw_state["squad_composition"]["age_groups"]
        avg_age = (
            21 * age_groups["under_21"] +
            23 * age_groups["21_to_25"] +
            28 * age_groups["26_to_30"] +
            32 * age_groups["over_30"]
        ) / sum(age_groups.values()) if sum(age_groups.values()) > 0 else 25
        
        age_state = self.discretize_value(avg_age, [22, 24, 26, 28, 30])
        
        # Squad balance (0 to 1) bins: [0.2, 0.4, 0.6, 0.8]
        balance = sum(
            abs(raw_state["squad_composition"]["positions"].get(pos, 0) - ideal)
            for pos, ideal in {"GK": 2, "DEF": 8, "MID": 8, "FWD": 5}.items()
        )
        balance_normalized = 1 - (balance / 20)  # Normalize to 0-1
        balance_state = self.discretize_value(balance_normalized, [0.2, 0.4, 0.6, 0.8])
        
        return (squad_size, age_state, balance_state)

    def encode_financial_state(self, raw_state: Dict) -> Tuple:
        """Encode financial state information."""
        # Budget utilization bins: [0.2, 0.4, 0.6, 0.8]
        budget_used = 1 - (raw_state["financial_health"]["transfer_budget"] / 
                          raw_state["financial_health"]["total_budget"])
        budget_state = self.discretize_value(budget_used, [0.2, 0.4, 0.6, 0.8])
        
        # Wage utilization bins: [0.4, 0.6, 0.8, 0.9]
        wage_state = self.discretize_value(
            raw_state["financial_health"]["wage_utilization"],
            [0.4, 0.6, 0.8, 0.9]
        )
        
        return (budget_state, wage_state)

    def encode_performance_state(self, raw_state: Dict) -> Tuple:
        """Encode team performance state."""
        # Form bins: [0.2, 0.4, 0.6, 0.8]
        form = raw_state["team_performance"]["form"]
        form_state = self.discretize_value(form, [0.2, 0.4, 0.6, 0.8])
        
        # Goals per game bins: [0.5, 1.0, 1.5, 2.0]
        scoring = raw_state["team_performance"]["goals_per_game"]
        scoring_state = self.discretize_value(scoring, [0.5, 1.0, 1.5, 2.0])
        
        # Goals conceded per game bins: [0.5, 1.0, 1.5, 2.0]
        defending = raw_state["team_performance"]["conceded_per_game"]
        defending_state = self.discretize_value(defending, [0.5, 1.0, 1.5, 2.0])
        
        return (form_state, scoring_state, defending_state)

    def encode_market_state(self, raw_state: Dict) -> Tuple:
        """Encode transfer market state."""
        # Market trend bins: [-0.2, -0.1, 0.0, 0.1, 0.2]
        trends = raw_state["market_conditions"]["market_trend"]
        avg_trend = sum(trends.values()) / len(trends) if trends else 0
        trend_state = self.discretize_value(avg_trend, [-0.2, -0.1, 0.0, 0.1, 0.2])
        
        # Season progress bins: [0.25, 0.5, 0.75]
        season_progress = (raw_state.get("current_day", 0) % 365) / 365
        season_state = self.discretize_value(season_progress, [0.25, 0.5, 0.75])
        
        return (trend_state, season_state)

class QTable:
    """Q-table implementation with defaultdict."""
    
    def __init__(self):
        self.q_values = defaultdict(lambda: defaultdict(float))
        self.learning_rate = 0.1
        self.gamma = 0.95
    
    def get_value(self, state: Tuple, action: Any) -> float:
        """Get Q-value for a state-action pair."""
        return self.q_values[state][action]
    
    def update(self, state: Tuple, action: Any, reward: float, next_state: Tuple,
              possible_next_actions: List[Any]):
        """Update Q-value using Q-learning formula."""
        current_q = self.get_value(state, action)
        next_max_q = max(self.get_value(next_state, a) for a in possible_next_actions)
        
        new_q = current_q + self.learning_rate * (
            reward + self.gamma * next_max_q - current_q
        )
        
        self.q_values[state][action] = new_q

class ManagerBrain:
    """Main reinforcement learning component using Q-learning."""
    
    def __init__(self, profile):
        self.profile = profile
        self.state_encoder = StateEncoder()
        
        # Separate Q-tables for different types of decisions
        self.match_qtable = QTable()
        self.transfer_qtable = QTable()
        self.training_qtable = QTable()
        self.lineup_qtable = QTable()
        
        # Base exploration rates
        self.base_exploration_rate = 0.2
        self.min_exploration_rate = 0.05
        
        # Track learning progress
        self.episode_rewards = []
    
    def get_exploration_rate(self) -> float:
        """Get current exploration rate adjusted for manager's profile."""
        base_rate = max(
            self.min_exploration_rate,
            self.base_exploration_rate * (1 - len(self.episode_rewards) / 1000)
        )
        return self.profile.get_risk_adjusted_exploration_rate(base_rate)
    
    def encode_state(self, raw_state: Dict) -> Tuple:
        """Encode raw state into discrete state tuple."""
        squad_state = self.state_encoder.encode_squad_state(raw_state)
        financial_state = self.state_encoder.encode_financial_state(raw_state)
        performance_state = self.state_encoder.encode_performance_state(raw_state)
        market_state = self.state_encoder.encode_market_state(raw_state)
        
        # Convert tactics dict to sorted tuple of tuples
        tactics = tuple(sorted(raw_state["tactics"].items()))
        
        return squad_state + financial_state + performance_state + market_state + (tactics,)
    
    def select_action(self, state: Tuple, possible_actions: List[Any],
                     action_type: str = "match") -> Any:
        """Select action using epsilon-greedy policy."""
        qtable = self._get_qtable(action_type)
        
        if random.random() < self.get_exploration_rate():
            return random.choice(possible_actions)
        
        # Choose action with highest Q-value
        return max(
            possible_actions,
            key=lambda a: qtable.get_value(state, a)
        )
    
    def learn(self, state: Tuple, action: Any, reward: float,
              next_state: Tuple, possible_next_actions: List[Any],
              action_type: str = "match"):
        """Learn from experience using Q-learning."""
        qtable = self._get_qtable(action_type)
        
        # Apply reward adjustments based on manager profile
        if action_type == "match":
            reward = self.profile.calculate_match_reward({"reward": reward})
        elif action_type == "transfer":
            reward = self.profile.calculate_transfer_reward({"reward": reward})
        
        qtable.update(state, action, reward, next_state, possible_next_actions)
        self.episode_rewards.append(reward)
    
    def _get_qtable(self, action_type: str) -> QTable:
        """Get the appropriate Q-table for the action type."""
        if action_type == "match":
            return self.match_qtable
        elif action_type == "transfer":
            return self.transfer_qtable
        elif action_type == "training":
            return self.training_qtable
        elif action_type == "lineup":
            return self.lineup_qtable
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def get_stats(self) -> Dict:
        """Get learning statistics."""
        recent_rewards = self.episode_rewards[-100:] if self.episode_rewards else []
        
        return {
            "total_episodes": len(self.episode_rewards),
            "recent_avg_reward": sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0,
            "exploration_rate": self.get_exploration_rate(),
            "profile": {
                "short_term_weight": self.profile.short_term_weight,
                "long_term_weight": self.profile.long_term_weight,
                "risk_tolerance": self.profile.risk_tolerance
            }
        }
