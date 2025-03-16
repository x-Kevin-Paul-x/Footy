"""Q-learning implementation for football manager decision making."""

from typing import Dict, Tuple, List, Any
import random
from collections import defaultdict

class StateEncoder:
    """Convert raw states into discrete states for Q-learning."""
    
    def encode_state(self, raw_state: dict) -> tuple:
        """Combine all encoded state components into a single tuple"""
        squad = self.encode_squad_state(raw_state)
        financial = self.encode_financial_state(raw_state)
        performance = self.encode_performance_state(raw_state)
        market = self.encode_market_state(raw_state)
        return squad + financial + performance + market
    
    @staticmethod
    def discretize_value(value: float, bins: List[float]) -> int:
        """Convert a continuous value into a discrete bin index."""
        for i, threshold in enumerate(bins):
            if value <= threshold:
                return i
        return len(bins)

    def encode_squad_state(self, raw_state: Dict) -> Tuple:
        """Encode squad state with continuous values and role analysis."""
        squad_data = raw_state.get("squad_composition", {})
        market_data = raw_state.get("market_conditions", {})
        
        # Continuous squad metrics
        total_players = squad_data.get("total_players", 0)
        avg_age = squad_data.get("average_age", 25)  # Default to average age
        
        # Squad balance metrics
        positions = squad_data.get("positions", {"ANY": 1})  # Default to balanced position
        max_pos = max(positions.values()) if positions else 1
        position_balance = sum(positions.values()) / max_pos if max_pos > 0 else 0
        
        # Squad roles (if available)
        squad_roles = squad_data.get("squad_roles", {})
        current_roles = squad_roles.get("current", {})
        required_roles = squad_roles.get("requirements", {})
        
        # Calculate role fulfillment (with defaults)
        role_gaps = 0
        if current_roles and required_roles:
            role_gaps = sum(
                abs(current_roles.get(role, 0) - required_roles.get(role, 0))
                for role in set(current_roles) | set(required_roles)
            )
            
        # Market dynamics
        supply_demand = market_data.get("supply_demand_ratio", {})
        market_ratio = supply_demand.get("ANY", 0.5)  # Default to balanced market
        
        return (
            total_players / 30,   # Normalized to 0-1 (assuming max squad size 30)
            avg_age / 40,         # Normalized assuming max age 40
            role_gaps / 20,       # Normalized by max possible gap
            position_balance,     # Already normalized 0-1
            market_ratio         # Already normalized 0-1
        )

    def encode_financial_state(self, raw_state: Dict) -> Tuple:
        """Encode financial state information."""
        financial = raw_state.get("financial_health", {})
        
        # Budget utilization calculation with defaults
        transfer_budget = financial.get("transfer_budget", 0)
        total_budget = financial.get("total_budget", 1)  # Avoid division by zero
        budget_used = 1 - (transfer_budget / total_budget) if total_budget > 0 else 1
        budget_state = self.discretize_value(budget_used, [0.2, 0.4, 0.6, 0.8])
        
        # Wage utilization calculation with defaults
        wage_budget = financial.get("wage_budget", 0)
        wage_utilization = wage_budget / total_budget if total_budget > 0 else 0
        wage_state = self.discretize_value(wage_utilization, [0.4, 0.6, 0.8, 0.9])
        
        return (budget_state, wage_state)

    def encode_performance_state(self, raw_state: Dict) -> Tuple:
        """Encode team performance state."""
        performance = raw_state.get("team_performance", {})
        
        # Form bins: [0.2, 0.4, 0.6, 0.8]
        form = performance.get("form", 0.5)  # Default to average form
        form_state = self.discretize_value(form, [0.2, 0.4, 0.6, 0.8])
        
        # Goals per game bins: [0.5, 1.0, 1.5, 2.0]
        scoring = performance.get("goals_per_game", 1.0)  # Default to 1 goal/game
        scoring_state = self.discretize_value(scoring, [0.5, 1.0, 1.5, 2.0])
        
        # Goals conceded per game bins: [0.5, 1.0, 1.5, 2.0]
        defending = performance.get("conceded_per_game", 1.0)  # Default to 1 goal/game
        defending_state = self.discretize_value(defending, [0.5, 1.0, 1.5, 2.0])
        
        return (form_state, scoring_state, defending_state)

    def encode_market_state(self, raw_state: Dict) -> Tuple:
        """Encode transfer market state."""
        market_data = raw_state.get("market_conditions", {})
        
        # Market trend bins: [-0.2, -0.1, 0.0, 0.1, 0.2]
        trends = market_data.get("market_trend", {"overall": 0.0})
        avg_trend = sum(trends.values()) / len(trends) if trends else 0.0
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
        
        # Base exploration rates - increased to encourage more exploration
        self.base_exploration_rate = 0.5
        self.min_exploration_rate = 0.2
        
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
