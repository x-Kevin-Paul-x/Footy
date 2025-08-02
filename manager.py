import random
import numpy as np
import names
from collections import defaultdict
from typing import Dict, List, Tuple, Any
from manager_profile import ManagerProfile
from manager_brain import ManagerBrain, StateEncoder
from manager_db import create_manager, get_manager, update_manager, delete_manager

class Manager:
    def __init__(self, name=None, experience_level=None, profile=None,
                 youth_promotion_ability_threshold=65, youth_promotion_age_threshold=19):
        """Initialize a manager with Q-learning capabilities."""
        self.name = names.get_full_name() if not name else name
        self.experience_level = min(10, max(1, experience_level if experience_level else random.randint(1, 10)))
        self.team = None

        # Youth promotion thresholds (can be set per manager)
        self.youth_promotion_ability_threshold = youth_promotion_ability_threshold
        self.youth_promotion_age_threshold = youth_promotion_age_threshold
        
        # Create or use provided manager profile
        self.profile = profile if profile else ManagerProfile.create_random_profile()
        
        # Initialize Q-learning brain
        self.brain = ManagerBrain(self.profile)
        
        # Initialize transfer tracking
        self.transfer_attempts = []  # List of bools for success/failure
        self.transfers_made = 0
        self.successful_transfers = 0
        
        # All possible formations
        self.formations = [
            "4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2",
            "4-5-1", "3-4-3", "4-1-4-1", "4-4-1-1", "4-3-2-1",
            "3-6-1", "5-4-1", "4-6-0", "4-2-4", "3-3-4",
            "2-3-5", "5-2-3", "3-4-2-1", "4-3-1-2", "4-2-2-2"
        ]
        
        # Track performance and state
        self.current_match_state = None
        self.last_match_action = None
        self.formation = self.formations[0]
        self.tactics = self._initialize_tactics()
        
        # Market trend tracking
        self.transfer_value_estimates = {}
        self.memory_capacity = 1000  # Max entries to keep in market memory
        self.market_memory = {
            "price_history": defaultdict(list),  # Track price changes
            "position_demand": defaultdict(list),  # Track position popularity
            "seasonal_factors": defaultdict(float),  # Track seasonal effects
            "success_patterns": defaultdict(list)  # Track successful transfers
        }
        
        # Enhanced experience replay memory
        self.transfer_history = []
        self.match_history = []
        self.lineup_history = []
        self.performance_history = []
        self.market_state_history = []
        
        # Performance tracking
        self.matches_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.total_rewards = 0
        self.episode_rewards = []
        self.match_rewards = []
        
        # Current state
        self.formation = self.formations[0]
        self.tactics = self._initialize_tactics()
        
        # Action spaces
        self.tactical_actions = {
            "offensive": list(range(30, 81, 5)),
            "defensive": list(range(30, 81, 5)),
            "pressure": list(range(30, 81, 5))
        }
        
        # Database attributes
        self.manager_id = None
        self.salary = 0.0

    def save_to_database(self):
        """Save manager to database and return manager_id"""
        if self.manager_id is None:
            # Create new manager
            self.manager_id = create_manager(
                name=self.name,
                experience_level=self.experience_level,
                formation=self.formation,
                matches_played=self.matches_played,
                wins=self.wins,
                draws=self.draws,
                losses=self.losses,
                total_rewards=self.total_rewards
            )
        else:
            # Update existing manager
            update_manager(
                manager_id=self.manager_id,
                name=self.name,
                experience_level=self.experience_level,
                formation=self.formation,
                matches_played=self.matches_played,
                wins=self.wins,
                draws=self.draws,
                losses=self.losses,
                total_rewards=self.total_rewards
            )
        return self.manager_id

    @classmethod
    def load_from_database(cls, manager_id):
        """Load manager from database by ID"""
        data = get_manager(manager_id)
        if not data:
            return None
            
        manager = cls(
            name=data["name"],
            experience_level=data["experience_level"]
        )
        manager.manager_id = data["manager_id"]
        manager.formation = data["formation"]
        manager.tactics = data["tactics"]
        manager.salary = data["salary"]
        return manager

    def train_players(self, perf_multiplier=1.0):
        """Train all players (senior and youth) with performance-based improvement."""
        # Train senior squad
        for player in self.team.players:
            player.train_player(
                intensity="medium",
                training_days=3,
                coach_bonus=0,
                focus_area=None
            )
            # Apply performance multiplier
            for attr_type in player.attributes:
                for sub_attr in player.attributes[attr_type]:
                    player.attributes[attr_type][sub_attr] *= perf_multiplier

        # Train youth academy
        for player in getattr(self.team, "youth_academy", []):
            player.train_player(
                intensity="medium",
                training_days=3,
                coach_bonus=0,
                focus_area=None
            )
            for attr_type in player.attributes:
                for sub_attr in player.attributes[attr_type]:
                    player.attributes[attr_type][sub_attr] *= perf_multiplier

    def decide_promotions(self):
        """Promote youth players who meet manager's ability or age threshold, or if squad is thin."""
        if not self.team.youth_academy:
            return

        def get_ability(player):
            try:
                return sum(sum(cat.values()) for cat in player.attributes.values()) / sum(len(cat) for cat in player.attributes.values())
            except Exception:
                return 0

        to_promote = []
        min_squad_size = 18
        max_squad_size = 30

        # If squad is thin, be more aggressive in promoting youth
        for player in self.team.youth_academy:
            if len(self.team.players) + len(to_promote) >= max_squad_size:
                break # Stop if squad will be full

            ability = get_ability(player)
            if (
                ability >= self.youth_promotion_ability_threshold
                or player.age >= self.youth_promotion_age_threshold
                or len(self.team.players) < min_squad_size
            ):
                to_promote.append(player)

        for player in to_promote:
            try:
                self.team.promote_youth_player(player)
            except ValueError as e:
                print(f"Could not promote {player.name}: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get enhanced state representation for learning."""
        if not self.team:
            return None
            
        # Get squad composition
        position_distribution = self._get_position_distribution()
        age_distribution = self._get_age_distribution()
        
        # Get financial health
        financial_state = self._get_financial_state()
        
        # Get team performance metrics
        performance_metrics = self._get_performance_metrics()
        
        # Get market conditions
        market_state = self._get_market_state()
        
        state = {
            "squad_composition": {
                "positions": position_distribution,
                "age_groups": age_distribution,
                "total_players": len(self.team.players),
                "average_rating": self.team.get_squad_strength()
            },
            "financial_health": financial_state,
            "team_performance": performance_metrics,
            "market_conditions": market_state,
            "formation": self.formation,
            "tactics": self.tactics.copy(),
            "recent_performance": self._get_recent_performance()
        }
        return state
    
    def _get_position_distribution(self) -> Dict[str, int]:
        """Get current squad position distribution."""
        distribution = defaultdict(int)
        for player in self.team.players:
            position_group = self._get_position_group(player.position)
            distribution[position_group] += 1
        return dict(distribution)
    
    def _get_age_distribution(self) -> Dict[str, int]:
        """Get squad age distribution in groups."""
        distribution = {
            "under_21": 0,
            "21_to_25": 0,
            "26_to_30": 0,
            "over_30": 0
        }
        for player in self.team.players:
            if player.age < 21:
                distribution["under_21"] += 1
            elif player.age <= 25:
                distribution["21_to_25"] += 1
            elif player.age <= 30:
                distribution["26_to_30"] += 1
            else:
                distribution["over_30"] += 1
        return distribution
    
    def _get_financial_state(self) -> Dict[str, float]:
        """Get detailed financial state."""
        wage_budget = self.team.wage_budget
        transfer_budget = self.team.transfer_budget
        total_wages = sum(self.team.calculate_weekly_expenses()["breakdown"].values())
        
        return {
            "total_budget": self.team.budget,
            "transfer_budget": transfer_budget,
            "wage_budget": wage_budget,
            "wage_utilization": total_wages / wage_budget if wage_budget > 0 else 0,
            "financial_health_score": self._calculate_financial_health_score()
        }
    
    def _get_performance_metrics(self) -> Dict[str, float]:
        """Get detailed team performance metrics."""
        if not self.match_history:
            return {
                "form": 0.0,
                "goals_per_game": 0.0,
                "conceded_per_game": 0.0,
                "win_rate": 0.0
            }
        
        recent_matches = self.match_history[-5:]
        total_matches = len(self.match_history)
        
        metrics = {
            "form": sum(1 if m["winner"] else 0.5 if m["draw"] else 0
                       for m in recent_matches) / len(recent_matches),
            "goals_per_game": sum(m["goals_for"] for m in self.match_history) / total_matches,
            "conceded_per_game": sum(m["goals_against"] for m in self.match_history) / total_matches,
            "win_rate": self.wins / total_matches if total_matches > 0 else 0
        }
        return metrics
    
    def _get_market_state(self) -> Dict[str, Any]:
        """Get current market state analysis."""
        if not self.market_memory["price_history"]:
            return {
                "market_trend": 0.0,
                "position_demand": {},
                "seasonal_factor": 1.0
            }
        
        # Calculate market trends
        price_trends = {}
        for position, prices in self.market_memory["price_history"].items():
            if len(prices) >= 2:
                trend = (prices[-1] - prices[0]) / prices[0]
                price_trends[position] = trend
        
        # Calculate position demand
        position_demand = {
            pos: len(history) / max(len(h) for h in self.market_memory["position_demand"].values())
            for pos, history in self.market_memory["position_demand"].items()
        }
        
        return {
            "market_trend": price_trends,
            "position_demand": position_demand,
            "seasonal_factor": dict(self.market_memory["seasonal_factors"])
        }
    
    def _calculate_financial_health_score(self) -> float:
        """Calculate overall financial health score."""
        if not self.team:
            return 0.0
            
        wage_ratio = self.team.calculate_weekly_expenses()["total"] / self.team.weekly_budget
        transfer_budget_ratio = self.team.transfer_budget / self.team.budget
        
        # Score from 0 to 1, higher is better
        score = (
            (1 - min(wage_ratio, 1)) * 0.4 +  # 40% weight on wage management
            min(transfer_budget_ratio, 1) * 0.6  # 60% weight on transfer budget
        )
        return score
    
    def _calculate_transfer_reward(self, transfer_action: Dict[str, Any],
                                  old_state: Dict[str, Any],
                                  new_state: Dict[str, Any]) -> float:
        """Calculate comprehensive reward for a transfer action."""
        reward = 0.0
        
        # Financial impact (25% weight)
        if transfer_action["type"] == "buy":
            price_value_ratio = self.transfer_value_estimates.get(transfer_action["player"].name, transfer_action["price"]) / transfer_action["price"]
            reward += 0.25 * (price_value_ratio - 1)  # Reward for good value
        else:  # Selling
            sell_price = transfer_action["price"]
            value_estimate = self.transfer_value_estimates.get(transfer_action["player"].name, sell_price)
            profit_ratio = (sell_price / value_estimate - 1)
            reward += 0.25 * profit_ratio
        
        # Squad balance impact (25% weight)
        old_balance = self._calculate_squad_balance(old_state["squad_composition"])
        new_balance = self._calculate_squad_balance(new_state["squad_composition"])
        reward += 0.25 * (new_balance - old_balance)
        
        # Squad needs satisfaction (25% weight)
        if transfer_action["type"] == "buy":
            position_group = self._get_position_group(transfer_action["player"].position)
            current_count = old_state["squad_composition"]["positions"].get(position_group, 0)
            ideal_counts = {"GK": 2, "DEF": 8, "MID": 8, "FWD": 5}
            need_satisfaction = max(0, ideal_counts[position_group] - current_count) / ideal_counts[position_group]
            reward += 0.25 * need_satisfaction
            
        # Performance potential (25% weight)
        if transfer_action["type"] == "buy":
            player = transfer_action["player"]
            # Higher reward for young high-potential players
            age_factor = max(0, (27 - player.age) / 10)  # Peak at age 27
            potential_score = (player.potential / 100) * age_factor
            reward += 0.25 * potential_score
        else:
            # Reward for selling aging players
            player = transfer_action["player"]
            age_decline = max(0, (player.age - 27) / 10)  # Start declining after 27
            reward += 0.25 * age_decline
        
        return reward
    
    def _calculate_squad_balance(self, composition: Dict[str, Any]) -> float:
        """Calculate squad balance score."""
        position_weights = {"GK": 0.1, "DEF": 0.3, "MID": 0.3, "FWD": 0.3}
        ideal_ratios = {"GK": 0.087, "DEF": 0.304, "MID": 0.348, "FWD": 0.261}  # Based on typical squad composition
        
        balance_score = 0.0
        total_players = sum(composition["positions"].values())
        
        if total_players == 0:
            return 0.0
            
        for position, count in composition["positions"].items():
            actual_ratio = count / total_players
            ideal_ratio = ideal_ratios[position]
            balance_score += position_weights[position] * (1 - abs(actual_ratio - ideal_ratio))
        
        return balance_score

    def update_market_memory(self, transfer_data: Dict[str, Any]):
        """Update market memory with new transfer data."""
        player = transfer_data.get("player") # Use .get() for safety
        price = transfer_data.get("price", 0) # Default price if not found

        if player is None:
            # If there's no player object (e.g., a failed buy attempt for a non-existent listing),
            # we can't update market memory based on player specifics.
            # We could log this or simply return.
            # print(f"Debug: update_market_memory called with no player object. Transfer data: {transfer_data}")
            return

        position = self._get_position_group(player.position)
        
        # Update price history
        self.market_memory["price_history"][position].append(price)
        if len(self.market_memory["price_history"][position]) > self.memory_capacity:
            self.market_memory["price_history"][position].pop(0)
        
        # Update position demand
        self.market_memory["position_demand"][position].append(1)
        for pos in self.market_memory["position_demand"]:
            if pos != position:
                self.market_memory["position_demand"][pos].append(0)
        
        # Update seasonal factors (simplified)
        month = transfer_data.get("month", 0)
        if month in [1, 8]:  # Transfer windows
            self.market_memory["seasonal_factors"][month] = (
                self.market_memory["seasonal_factors"][month] * 0.9 +
                0.1 * (price / self.transfer_value_estimates[player.name])
            )

    def analyze_transfer_target(self, player: Any, asking_price: float) -> float:
        """Enhanced analysis of potential transfer target."""
        if not self.team:
            return 0.0
            
        state = self.get_state()
        position_group = self._get_position_group(player.position)
        
        # Base value score (30%)
        market_value = self.transfer_value_estimates.get(player.name, asking_price)
        value_score = market_value / asking_price if asking_price > 0 else 0
        
        # Squad need score (30%)
        current_in_position = state["squad_composition"]["positions"].get(position_group, 0)
        ideal_counts = {"GK": 2, "DEF": 8, "MID": 8, "FWD": 5}
        need_score = max(0, ideal_counts[position_group] - current_in_position) / ideal_counts[position_group]
        
        # Development potential score (20%)
        age_factor = max(0, (27 - player.age) / 10)  # Peak at age 27
        potential_score = (player.potential / 100) * age_factor
        
        # Financial viability score (20%)
        budget_ratio = asking_price / self.team.transfer_budget if self.team.transfer_budget > 0 else float('inf')
        financial_score = 1 - min(1, budget_ratio)
        
        # Wage impact score (10% penalty if over wage budget)
        current_wages = self.team.calculate_weekly_expenses()["total"]
        new_wages = current_wages + player.wage
        wage_budget_ratio = new_wages / self.team.wage_budget if self.team.wage_budget > 0 else float('inf')
        wage_score = 1 - min(1, wage_budget_ratio)
        if wage_budget_ratio > 1:
            wage_score = -0.1  # Penalty for exceeding wage budget
        
        # Weighted total score
        total_score = (
            0.3 * value_score +
            0.3 * need_score +
            0.2 * potential_score +
            0.2 * financial_score +
            0.1 * wage_score
        )
        
        return total_score

    def evaluate_free_agents(self, transfer_market):
        """Evaluate and sign free agents for critical positions if squad is thin."""
        min_squad_size = 18
        emergency_squad_size = 16
        actions = []

        squad_needs = self.team.get_squad_needs()
        needed_positions = [need["position"] for need in squad_needs["needs"]]

        # Only act if squad is thin
        if len(self.team.players) < min_squad_size:
            free_agents = transfer_market.get_free_agents()
            # Prioritize needed positions
            for pos in needed_positions:
                candidates = [p for p in free_agents if self._get_position_group(p.position) == pos]
                candidates = sorted(candidates, key=lambda p: p.get_overall_rating(), reverse=True)
                for player in candidates:
                    # Emergency override if squad < emergency_squad_size
                    actions.append(("free_agent", player))
                    if len(self.team.players) + len(actions) >= emergency_squad_size:
                        break
                if len(self.team.players) + len(actions) >= emergency_squad_size:
                    break
        return actions

    def make_transfer_decision(self, transfer_market):
        """Make transfer decisions using Q-learning. Aggressively buy and sign free agents if squad is thin."""
        raw_state = self.get_state()
        state = self.brain.encode_state(raw_state)
        
        # Get all possible actions
        possible_actions = self._get_possible_transfer_actions(transfer_market)

        # Evaluate free agents if squad is thin
        free_agent_actions = self.evaluate_free_agents(transfer_market)

        # If squad is thin, be much more aggressive
        min_squad_size = 18
        if len(self.team.players) < min_squad_size:
            # Prioritize buying actions
            buy_actions = [a for a in possible_actions if a[0] == "buy"]
            if buy_actions:
                # Force a buy action if squad is critically low
                if len(self.team.players) < 15:
                    action = random.choice(buy_actions)
                else:
                    # Increase probability of buying
                    action = self.brain.select_action(state, buy_actions, "transfer")
            else:
                # Fallback to normal selection if no buy actions are possible
                action = self.brain.select_action(state, possible_actions, "transfer")
        else:
            action = self.brain.select_action(state, possible_actions, "transfer")

        self.last_transfer_state = state
        self.last_transfer_action = action
        
        # Convert Q-learning action to transfer actions
        transfer_actions = self._convert_q_action_to_transfer_actions(action, transfer_market)

        # Add free agent actions if squad is thin
        if free_agent_actions:
            transfer_actions.extend(free_agent_actions)
        
        # Debug output if enabled
        if hasattr(self, '_debug') and self._debug:
            print(f"\n{self.name} - Transfer Decision Making:")
            print(f"Available Actions: {len(possible_actions)}")
            print(f"Team Budget: £{self.team.budget:,.2f}")
            print(f"Squad Size: {len(self.team.players)}")
            # Print the Q-values for ALL possible actions
            print("Possible Actions with Q-Values:")
            qtable = self.brain._get_qtable("transfer")  # Get the transfer Q-table
            for action in possible_actions:
                q_value = qtable.get_value(state, action)
                print(f"  Action: {action}, Q-value: {q_value:.4f}")

        # Debug output selected actions
        if hasattr(self, '_debug') and self._debug and transfer_actions:
            print("\nSelected Actions:")
            for action_type, *params in transfer_actions:
                if action_type == "list":
                    player, price = params
                    print(f"List {player.name} for £{price:,.2f}")
                elif action_type == "buy":
                    listing, offer = params
                    print(f"Bid £{offer:,.2f} for {listing.player.name}")
                elif action_type == "free_agent":
                    player = params[0]
                    print(f"Sign free agent {player.name}")
        
        return transfer_actions
    
    def _get_possible_transfer_actions(self, transfer_market):
        """Generate possible transfer actions with enhanced market incentives."""
        actions = []
        squad_needs = self.team.get_squad_needs()
        
        # Selling actions
        if len(self.team.players) > 18:  # Only sell if squad is not thin
            for player in self.team.players:
                market_value = transfer_market.calculate_player_value(player)
                
                # Simplified selling logic: sell older players or if position is overstaffed
                position_group = self._get_position_group(player.position)
                current_in_pos = squad_needs["position_analysis"][position_group]["current"]
                ideal_in_pos = squad_needs["position_analysis"][position_group]["ideal"]

                if player.age > 30 or current_in_pos > ideal_in_pos:
                    actions.append(("sell", player, market_value * random.uniform(0.9, 1.1)))

        # Buying actions - more aggressive when squad is small
        if len(self.team.players) < 25:
            budget_for_buys = self.team.transfer_budget
            if len(self.team.players) < 18:
                budget_for_buys *= 1.5 # Use more budget if desperate

            available_players = transfer_market.get_available_players(max_price=budget_for_buys)
            
            for listing in available_players:
                # Prioritize signing players for positions in need
                player_pos_group = self._get_position_group(listing.player.position)
                pos_needs = squad_needs["needs"]
                is_needed = any(need["position"] == player_pos_group for need in pos_needs)

                # Be more likely to bid if the position is needed or squad is very small
                if is_needed or len(self.team.players) < 15:
                    offer_price = listing.asking_price * random.uniform(0.85, 1.05)
                    if self.team.can_afford_transfer(offer_price, listing.player.wage):
                         actions.append(("buy", listing.listing_id, offer_price))

        # Always have a "do nothing" option
        actions.append(("none", None, 0))
        return actions

    def _convert_q_action_to_transfer_actions(self, q_action, transfer_market):
        """Convert Q-learning action to actual transfer actions."""
        action_type, target, _ = q_action  # Ignore the Q-value 'price'
        if action_type == "none":
            return []

        actions = []
        if action_type == "sell":
            # Find the corresponding "sell" action in possible_actions to get the intended price
            for possible_action in self._get_possible_transfer_actions(transfer_market):
                if possible_action[0] == "sell" and possible_action[1] == target:
                    actions.append(("list", target, possible_action[2])) # Use the price from possible_actions
                    break  # Exit inner loop once found
        elif action_type == "buy":
            # Find the listing by ID
            listing = None
            for l in transfer_market.transfer_list:
                if l.listing_id == target:
                    listing = l
                    break
            if listing: # 'listing' is the TransferListing object, 'target' is the listing_id (int)
                # Find the corresponding "buy" action in possible_actions to get the intended offer price
                # The 'target' (listing_id) is what league.py expects.
                # The price should come from the Q-action's parameters or be re-evaluated.
                # Let's assume the price from the original q_action is what we want to offer.
                # q_action was (action_type, target_id, price_from_q_value)
                # So, the price is q_action[2]
                
                # We need to find the original offer price associated with this listing_id from _get_possible_transfer_actions
                # as the q_action's price component might be a Q-value, not the offer.
                # The q_action is ("buy", listing_id_int, q_value_or_price_indicator)
                # The actual offer price was determined in _get_possible_transfer_actions.
                
                original_offer_price = None
                for pa in self._get_possible_transfer_actions(transfer_market):
                    if pa[0] == "buy" and pa[1] == target: # target is listing_id_int
                        original_offer_price = pa[2] # This is the offer price
                        break
                
                if original_offer_price is not None:
                    actions.append(("buy", target, original_offer_price)) # target is listing_id (int)
                else:
                    # This case should ideally not happen if target was in possible_actions
                    # Fallback or log error
                    print(f"Warning (Manager): Could not find original offer price for listing ID {target}. Using listing asking price.")
                    actions.append(("buy", target, listing.asking_price)) # Fallback to asking price

        return actions


    def set_debug(self, enabled=True):
        """Enable or disable debug output."""
        self._debug = enabled
        if enabled:
            self._debug_stats = {
                "total_decisions": 0,
                "exploration_decisions": 0,
                "avg_reward": 0.0,
                "learning_steps": 0
            }

    def learn_from_match(self, match_result: Dict[str, Any]):
        """Learn from match results using Q-learning."""
        if not hasattr(self, 'last_match_state') or not self.last_match_state:
            return
            
        # Get new state
        new_raw_state = self.get_state()
        new_state = self.brain.encode_state(new_raw_state)
        
        # Calculate match reward based on profile
        match_dict = {
            "won": 1 if match_result.get("winner", False) else 0,
            "drawn": 1 if match_result.get("draw", False) else 0,
            "goals_scored": match_result.get("goals_for", 0),
            "goals_conceded": match_result.get("goals_against", 0),
            "youth_minutes": match_result.get("youth_minutes", 0),
            "possession": match_result.get("possession", 50),
            "player_development": match_result.get("player_development", 0)
        }
        reward = self.profile.calculate_match_reward(match_dict)
        
        # Get possible next actions for learning
        possible_next_actions = self._get_possible_match_actions()
        
        # Learn from experience
        self.brain.learn(
            self.last_match_state,
            self.last_match_action,
            reward,
            new_state,
            possible_next_actions,
            "match"
        )
        
        # Record match result and update performance tracking
        self.match_history.append(match_result)
        self.match_rewards.append(reward)
        self.total_rewards += reward
        
        # Debug output if enabled
        if hasattr(self, '_debug') and self._debug:
            print(f"\nMatch Learning Update - {self.name}:")
            print(f"Result: {'Win' if match_dict['won'] else 'Draw' if match_dict['drawn'] else 'Loss'}")
            print(f"Goals: {match_dict['goals_scored']}-{match_dict['goals_conceded']}")
            print(f"Reward: {reward:.2f}")
            print(f"Formation: {self.formation}")
            print(f"Current Exploration Rate: {self.brain.get_exploration_rate():.2f}")
        
        # Reset match state
        self.last_match_state = None
        self.last_match_action = None

    def learn_from_transfer(self, transfer_result: Dict[str, Any]):
        """Learn from transfer results using Q-learning. Give positive reward if fixing a forfeit by signing a player."""
        if not hasattr(self, 'last_transfer_state') or not self.last_transfer_state:
            return
            
        # Get new state
        new_raw_state = self.get_state()
        new_state = self.brain.encode_state(new_raw_state)
        
        # Create transfer dictionary for profile-based reward calculation
        transfer_dict = {
            "value_for_money": transfer_result.get("value_ratio", 1.0),
            "squad_need_filled": transfer_result.get("need_satisfaction", 0.0),
            "potential_profit": transfer_result.get("profit_potential", 0.0),
            "age_profile_improvement": transfer_result.get("age_impact", 0.0),
            "wage_structure_impact": transfer_result.get("wage_impact", 0.0),
            "budget_efficiency": transfer_result.get("budget_efficiency", 0.0),
            "negotiation_success": transfer_result.get("negotiation_outcome", 0.0)
        }
        
        # Calculate reward using profile preferences
        reward = self.profile.calculate_transfer_reward(transfer_dict)

        # If transfer_result indicates a forfeit was fixed, give a strong positive reward
        if transfer_result.get("forfeit_fixed"):
            reward += 50.0

        # Get possible next actions
        possible_next_actions = self._get_possible_transfer_actions(transfer_result.get("market"))
        
        # Learn from experience
        self.brain.learn(
            self.last_transfer_state,
            self.last_transfer_action,
            reward,
            new_state,
            possible_next_actions,
            "transfer"
        )
        
        # Update market memory
        self.update_market_memory({
            "player": transfer_result.get("player"),
            "price": transfer_result.get("price", 0),
            "month": transfer_result.get("month", 0)
        })
        
        # Reset transfer state
        self.last_transfer_state = None
        self.last_transfer_action = None
        
    def _get_possible_match_actions(self) -> List[Tuple]:
        """Get all possible match actions for the current state."""
        actions = []
        
        # Formation changes
        for formation in self.formations:
            actions.append(("formation", formation))
        
        # Tactical adjustments
        for offensive in range(30, 81, 10):
            for defensive in range(30, 81, 10):
                for pressure in range(30, 81, 10):
                    actions.append(("tactics", (
                        ("offensive", offensive),
                        ("defensive", defensive), 
                        ("pressure", pressure)
                    )))  # Convert tactics dict to tuple of tuples
        
        return actions
    
    def select_lineup(self, available_players: List[Any], opponent=None) -> Tuple[List[Any], List[str]]:
        """Select team lineup using Q-learning."""
        # Exclude injured players
        healthy_players = [p for p in available_players if not getattr(p, "is_injured", False)]
        raw_state = self.get_state()
        if raw_state is None:
            # Fallback to basic selection if no state available
            return self._select_basic_lineup(healthy_players)
            
        state = self.brain.encode_state(raw_state)
        
        # Get all possible lineup combinations
        possible_actions = self._get_lineup_actions(healthy_players)
        if not possible_actions:
            return self._select_basic_lineup(healthy_players)
        
        # Select action using Q-learning
        action = self.brain.select_action(state, possible_actions, "lineup")
        self.last_match_state = state
        self.last_match_action = action
        
        # Decode the selected action
        formation, players = action
        self.formation = formation
        positions = self._get_positions_for_formation(formation)
        
        return players, positions
    
    def _select_basic_lineup(self, available_players: List[Any]) -> Tuple[List[Any], List[str]]:
        """Basic lineup selection without Q-learning."""
        # Exclude injured players
        healthy_players = [p for p in available_players if not getattr(p, "is_injured", False)]
        formation = self.formation
        positions = self._get_positions_for_formation(formation)
        
        # Group players by position
        goalkeepers = [p for p in healthy_players if p.position == "GK"]
        defenders = [p for p in healthy_players if p.position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]]
        midfielders = [p for p in healthy_players if p.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]]
        forwards = [p for p in healthy_players if p.position in ["ST", "CF", "SS", "LW", "RW"]]
        
        # Sort players by role (STARTER first) then by rating
        role_priority = {"STARTER": 0, "BENCH": 1, "YOUTH": 2}
        
        def get_player_priority(player):
            rating = sum(sum(cat.values()) for cat in player.attributes.values()) / \
                     (len(player.attributes) * len(next(iter(player.attributes.values()))))
            return (role_priority.get(player.squad_role, 3), -rating)  # Negative for descending sort
        
        sorted_gk = sorted(goalkeepers, key=get_player_priority)
        sorted_def = sorted(defenders, key=get_player_priority)
        sorted_mid = sorted(midfielders, key=get_player_priority)
        sorted_fwd = sorted(forwards, key=get_player_priority)
        
        # Build lineup based on formation
        lineup = []
        for pos in positions:
            if pos == "GK" and sorted_gk:
                lineup.append(sorted_gk[0])
            elif pos in ["CB", "LB", "RB", "LWB", "RWB", "SW"] and sorted_def:
                lineup.append(sorted_def.pop(0))
            elif pos in ["CM", "CDM", "CAM", "LM", "RM", "DM"] and sorted_mid:
                lineup.append(sorted_mid.pop(0))
            elif sorted_fwd:
                lineup.append(sorted_fwd.pop(0))
        
        # Fill remaining spots with best available players
        def get_player_rating(player):
            return sum(sum(cat.values()) for cat in player.attributes.values()) / (
                len(player.attributes) * len(next(iter(player.attributes.values())))
            )
        while len(lineup) < 11 and (sorted_def or sorted_mid or sorted_fwd):
            best_remaining = []
            if sorted_def:
                best_remaining.append(sorted_def[0])
            if sorted_mid:
                best_remaining.append(sorted_mid[0])
            if sorted_fwd:
                best_remaining.append(sorted_fwd[0])
            
            if best_remaining:
                best_player = max(best_remaining, key=get_player_rating)
                lineup.append(best_player)
                if best_player in sorted_def:
                    sorted_def.pop(0)
                elif best_player in sorted_mid:
                    sorted_mid.pop(0)
                else:
                    sorted_fwd.pop(0)
        
        return tuple(lineup), positions  # Ensure tuple for Q-table compatibility
    
    def _get_lineup_actions(self, available_players: List[Any]) -> List[Tuple]:
        """Generate possible lineup combinations."""
        actions = []
        for formation in self.formations:
            positions = self._get_positions_for_formation(formation)
            
            # Group players by position type
            players_by_type = {
                "GK": [p for p in available_players if p.position == "GK"],
                "DEF": [p for p in available_players if p.position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]],
                "MID": [p for p in available_players if p.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]],
                "FWD": [p for p in available_players if p.position in ["ST", "CF", "SS", "LW", "RW"]]
            }
            
            # Count required positions
            needs = {
                "GK": sum(1 for p in positions if p == "GK"),
                "DEF": sum(1 for p in positions if p in ["CB", "LB", "RB", "LWB", "RWB", "SW"]),
                "MID": sum(1 for p in positions if p in ["CM", "CDM", "CAM", "LM", "RM", "DM"]),
                "FWD": sum(1 for p in positions if p in ["ST", "CF", "SS", "LW", "RW"])
            }
            
            # Check if we have enough players for this formation
            if all(len(players_by_type[pos_type]) >= count for pos_type, count in needs.items()):
                # Create valid lineup
                lineup = self._create_lineup_for_formation(formation, players_by_type, needs)
                if lineup and len(lineup) == 11:
                    actions.append((formation, tuple(lineup)))  # Convert lineup list to tuple
        
        return actions

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get enhanced learning statistics."""
        if not self.match_history:
            return {
                "total_rewards": 0,
                "win_rate": 0.0,
                "draw_rate": 0.0,
                "exploration_rate": self.brain.get_exploration_rate(),
                "learning_rate": self.brain.match_qtable.learning_rate,
                "market_learning": {
                    "price_trends": {},
                    "position_demand": {},
                    "seasonal_patterns": {}
                },
                "formation_preferences": [],
                "matches_played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0
            }
        
        # Calculate advanced statistics
        matches_played = len(self.match_history)
        wins = sum(1 for match in self.match_history if match["winner"])
        draws = sum(1 for match in self.match_history if match["draw"])
        
        # Calculate market learning metrics
        market_learning = {
            "price_trends": {
                pos: (prices[-1] / prices[0] - 1) if len(prices) > 1 else 0
                for pos, prices in self.market_memory["price_history"].items()
            },
            "position_demand": {
                pos: sum(demand[-5:]) / 5 if len(demand) >= 5 else 0
                for pos, demand in self.market_memory["position_demand"].items()
            },
            "seasonal_patterns": dict(self.market_memory["seasonal_factors"])
        }
        
        return {
            "total_rewards": self.total_rewards,
            "win_rate": (wins / matches_played) * 100,
            "draw_rate": (draws / matches_played) * 100,
            "exploration_rate": self.brain.get_exploration_rate(),
            "learning_rate": self.brain.match_qtable.learning_rate,
            "market_learning": market_learning,
            "formation_preferences": [(self.formation, 1.0)],  # Default to current formation with weight 1.0
            "matches_played": matches_played,
            "wins": wins,
            "draws": draws,
            "losses": matches_played - wins - draws,
            "average_reward": sum(self.episode_rewards[-10:]) / min(10, len(self.episode_rewards)) if self.episode_rewards else 0.0
        }
        
    def analyze_market_trends(self):
        """Analyze market trends to inform transfer decisions."""
        trends = {}
        
        # Analyze each position group
        for position in ["GK", "DEF", "MID", "FWD"]:
            prices = self.market_memory["price_history"].get(position, [])
            demand = self.market_memory["position_demand"].get(position, [])
            
            if len(prices) > 1:
                # Calculate price trend
                recent_prices = prices[-min(5, len(prices)):]
                price_trend = (recent_prices[-1] / recent_prices[0] - 1)
                
                # Calculate demand trend
                recent_demand = demand[-min(5, len(demand)):]
                demand_trend = sum(recent_demand) / len(recent_demand)
                
                # Get seasonal factor
                current_month = (self.team.league.current_day % 365) // 30 if hasattr(self.team, 'league') else 0
                seasonal_factor = self.market_memory["seasonal_factors"].get(current_month, 1.0)
                
                trends[position] = {
                    "price_trend": price_trend,
                    "demand_trend": demand_trend,
                    "seasonal_factor": seasonal_factor,
                    "market_score": (price_trend + demand_trend) * seasonal_factor
                }
        
        return trends
    
    def predict_player_development(self, player):
        """Predict player's potential development and future value."""
        age = player.age
        potential = player.potential
        current_ability = sum(sum(cat.values()) for cat in player.attributes.values()) / (
            len(player.attributes) * len(next(iter(player.attributes.values())))
        )
        
        # Calculate development potential
        years_to_peak = max(0, 27 - age)  # Assume peak at 27
        development_rate = (potential - current_ability) / max(1, years_to_peak)
        
        # Calculate value trajectory
        current_value = self.transfer_value_estimates.get(player.name, 0)
        projected_values = []
        
        for year in range(5):  # Project 5 years ahead
            projected_age = age + year
            if projected_age < 27:
                # Growth phase
                projected_ability = min(potential, current_ability + development_rate * year)
            else:
                # Decline phase
                decline_rate = 0.05 * (projected_age - 27)  # 5% decline per year after 27
                projected_ability = current_ability * (1 - decline_rate)
            
            projected_value = current_value * (projected_ability / current_ability)
            projected_values.append(projected_value)
        
        return {
            "current_ability": current_ability,
            "potential": potential,
            "development_rate": development_rate,
            "projected_values": projected_values,
            "peak_value": max(projected_values)
        }
    
    def _similar_tactics(self, tactics1, tactics2):
        """Check if two tactical setups are similar."""
        return all(abs(tactics1[k] - tactics2[k]) < 10 for k in tactics1)
    
    def get_stats(self):
        """Get current learning statistics with enhanced metrics."""
        base_stats = self.get_learning_stats()
        
        # Add market analysis
        market_trends = self.analyze_market_trends()
        
        # Calculate transfer success rate from attempts
        if not hasattr(self, 'transfer_attempts'):
            self.transfer_attempts = []
        
        # Get recent attempts (last 20)
        recent_attempts = self.transfer_attempts[-20:]
        transfer_success_rate = (sum(1 for success in recent_attempts if success) / len(recent_attempts)) if recent_attempts else 0
        
        stats = {
            **base_stats,
            "market_trends": market_trends,
            "transfer_success_rate": transfer_success_rate,
            "current_exploration_rate": self.brain.get_exploration_rate(),
            "memory_usage": {
                "transfer_history": len(self.transfer_history),
                "market_memory": {k: len(v) for k, v in self.market_memory.items()},
                "value_estimates": len(self.transfer_value_estimates)
            }
        }
        
        # Add debug info if enabled
        if hasattr(self, '_debug') and self._debug:
            print("\nManager Learning Stats:")
            print(f"Matches Played: {self.matches_played}")
            print(f"Win Rate: {(self.wins/self.matches_played)*100:.1f}% ({self.wins}-{self.draws}-{self.losses})")
            print(f"Average Reward: {sum(self.match_rewards[-10:]) / min(10, len(self.match_rewards)):.2f}")
            print(f"Exploration Rate: {self.brain.get_exploration_rate():.2f}")
            print(f"Transfer Success Rate: {transfer_success_rate*100:.1f}%")
            
        return stats

    def _get_position_group(self, position):
        """Convert specific position to position group."""
        if position == "GK":
            return "GK"
        elif position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]:
            return "DEF"
        elif position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]:
            return "MID"
        else:
            return "FWD"
            
    def _get_positions_for_formation(self, formation: str) -> List[str]:
        """Convert formation string to list of positions."""
        positions = ["GK"]  # Always need a goalkeeper
        parts = formation.split("-")
        
        # Map formation numbers to position types
        def_positions = ["CB", "LB", "RB", "SW"]  # Defensive positions
        mid_positions = ["CM", "CDM", "CAM", "LM", "RM"]  # Midfield positions
        fwd_positions = ["ST", "CF", "LW", "RW"]  # Forward positions
        
        # Add defenders
        num_defenders = int(parts[0])
        for i in range(num_defenders):
            positions.append(def_positions[i % len(def_positions)])
            
        # Add midfielders
        num_midfielders = int(parts[1])
        for i in range(num_midfielders):
            positions.append(mid_positions[i % len(mid_positions)])
            
        # Add forwards
        num_forwards = int(parts[2])
        for i in range(num_forwards):
            positions.append(fwd_positions[i % len(fwd_positions)])
            
        return positions
    
    def _get_recent_performance(self):
        """Calculate recent performance metrics."""
        if not self.match_history:
            return {"wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}
        
        recent_matches = self.match_history[-5:]
        performance = defaultdict(int)
        for match in recent_matches:
            if match["winner"]:
                performance["wins"] += 1
            elif match["draw"]:
                performance["draws"] += 1
            else:
                performance["losses"] += 1
            performance["goals_for"] += match.get("goals_for", 0)
            performance["goals_against"] += match.get("goals_against", 0)
        return dict(performance)
    
    def _evaluate_squad_stability(self) -> float:
        """Evaluate how stable/balanced the current squad is."""
        if not self.team:
            return 0.0
            
        squad_needs = self.team.get_squad_needs()
        
        # Get distributions from squad needs
        current_distribution = squad_needs["current_distribution"]
        ideal_distribution = squad_needs["ideal_distribution"]
        
        # Check position balance (40% weight)
        total_imbalance = 0
        for pos, ideal in ideal_distribution.items():
            current = current_distribution.get(pos, 0)
            total_imbalance += abs(current - ideal)
        position_score = max(0, 1 - (total_imbalance / 20))
        
        # Check age distribution (30% weight)
        age_groups = self._get_age_distribution()
        total_players = len(self.team.players)
        if total_players == 0:
            return 0.0
            
        age_balance = min(
            age_groups["21_to_25"] / total_players if total_players > 0 else 0,  # Want young players
            age_groups["26_to_30"] / total_players if total_players > 0 else 0   # Want prime players
        )
        
        # Check squad depth (30% weight)
        min_size, max_size = 18, 25
        current_size = len(self.team.players)
        depth_score = 1.0 if min_size <= current_size <= max_size else 0.0
        
        # Calculate final stability score
        stability = (
            0.4 * position_score +
            0.3 * age_balance +
            0.3 * depth_score
        )
        
        return stability

    def _initialize_tactics(self):
        """Initialize tactics with some randomization for exploration."""
        return {
            "offensive": random.randint(40, 60),
            "defensive": random.randint(40, 60),
            "pressure": random.randint(40, 60)
        }

    def _create_lineup_for_formation(self, formation: str, players_by_type: Dict[str, List[Any]],
                                   needs: Dict[str, int]) -> List[Any]:
        """Create a lineup that fits the formation requirements."""
        # Helper function to sort players by rating
        def get_player_rating(player):
            return sum(sum(cat.values()) for cat in player.attributes.values()) / \
                   (len(player.attributes) * len(next(iter(player.attributes.values()))))
        
        # Sort players by rating in each position group
        sorted_players = {
            pos_type: sorted(players, key=get_player_rating, reverse=True)
            for pos_type, players in players_by_type.items()
        }
        
        # Initialize lineup
        lineup = []
        
        # Add goalkeeper
        if sorted_players["GK"] and needs["GK"] > 0:
            lineup.append(sorted_players["GK"][0])
        else:
            return None
        
        # Add outfield players by position type
        for pos_type in ["DEF", "MID", "FWD"]:
            count_needed = needs[pos_type]
            available = sorted_players[pos_type][:count_needed]
            
            if len(available) < count_needed:
                return None  # Not enough players for this formation
                
            lineup.extend(available)
            
            # Update remaining available players
            sorted_players[pos_type] = sorted_players[pos_type][count_needed:]
        
        # Verify we have exactly 11 players
        if len(lineup) != 11:
            return None
            
        return lineup
