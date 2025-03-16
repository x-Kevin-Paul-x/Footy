"""Manager profile system for defining strategic preferences and learning parameters."""

import random
from dataclasses import dataclass
from typing import Dict

@dataclass
class ManagerProfile:
    """Define a manager's strategic preferences and personality."""
    
    # Strategic focus (must sum to 1.0)
    short_term_weight: float = 0.5  # Focus on immediate results
    long_term_weight: float = 0.5  # Focus on development
    
    # Risk profile (0.0 to 1.0)
    risk_tolerance: float = 0.5  # Higher means more willing to take risks
    
    # Style preferences (0.0 to 1.0)
    attacking_preference: float = 0.5
    defensive_preference: float = 0.5
    possession_preference: float = 0.5
    
    # Development preferences (0.0 to 1.0)
    youth_preference: float = 0.5
    financial_conservation: float = 0.5
    bargaining_aggression: float = 0.5

    def __post_init__(self):
        """Validate that strategic focus weights sum to 1.0"""
        if not 0.99 <= (self.short_term_weight + self.long_term_weight) <= 1.01:
            raise ValueError("Strategic focus weights must sum to 1.0")
    
    @classmethod
    def create_random_profile(cls) -> 'ManagerProfile':
        """Create a manager profile with random preferences."""
        # Generate short vs long term focus (must sum to 1.0)
        short_term = random.uniform(0.3, 0.7)
        long_term = 1.0 - short_term
        
        return cls(
            short_term_weight=short_term,
            long_term_weight=long_term,
            risk_tolerance=random.uniform(0.2, 0.8),
            attacking_preference=random.uniform(0.3, 0.7),
            defensive_preference=random.uniform(0.3, 0.7),
            possession_preference=random.uniform(0.3, 0.7),
            youth_preference=random.uniform(0.3, 0.7),
            financial_conservation=random.uniform(0.3, 0.7),
            bargaining_aggression=random.uniform(0.3, 0.7)
        )
    
    def calculate_match_reward(self, result: Dict) -> float:
        """Calculate match reward based on manager's preferences."""
        short_term_reward = (
            3.0 * result.get("won", 0) +
            1.0 * result.get("drawn", 0) +
            1.0 * result.get("goals_scored", 0) -
            0.5 * result.get("goals_conceded", 0)
        )
        
        long_term_reward = (
            0.5 * result.get("youth_minutes", 0) / 90 +  # Reward for playing youth
            0.3 * result.get("possession", 50) / 50 if self.possession_preference > 0.5 else 0 +
            0.2 * result.get("player_development", 0)
        )
        
        return (
            self.short_term_weight * short_term_reward +
            self.long_term_weight * long_term_reward
        )
    
    def calculate_transfer_reward(self, transfer: Dict) -> float:
        """Calculate transfer reward based on manager's preferences."""
        # Increased rewards to encourage more transfer activity
        immediate_impact = (
            2.0 * transfer.get("value_for_money", 0) +  # Doubled value for money reward
            2.0 * transfer.get("squad_need_filled", 0)  # Doubled squad need reward
        )
        
        long_term_value = (
            1.5 * transfer.get("potential_profit", 0) +  # Increased potential profit reward
            1.5 * transfer.get("age_profile_improvement", 0) +  # Increased age profile reward
            transfer.get("wage_structure_impact", 0)
        )
        
        financial_prudence = (
            0.5 * transfer.get("budget_efficiency", 0) * self.financial_conservation +  # Reduced penalty
            1.5 * transfer.get("negotiation_success", 0) * self.bargaining_aggression  # Increased negotiation reward
        )
        
        return (
            self.short_term_weight * immediate_impact +
            self.long_term_weight * long_term_value +
            financial_prudence
        )
    
    def get_risk_adjusted_exploration_rate(self, base_rate: float) -> float:
        """Adjust exploration rate based on risk tolerance."""
        return base_rate * (0.5 + self.risk_tolerance)