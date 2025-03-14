import random
import numpy as np
import names
from collections import defaultdict

class Manager:
    def __init__(self, name=None, experience_level=None):
        """Initialize a manager with reinforcement learning capabilities."""
        self.name = names.get_full_name() if not name else name
        self.experience_level = min(10, max(1, experience_level if experience_level else random.randint(1, 10)))
        self.team = None
        
        # All possible formations
        self.formations = [
            "4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2",
            "4-5-1", "3-4-3", "4-1-4-1", "4-4-1-1", "4-3-2-1",
            "3-6-1", "5-4-1", "4-6-0", "4-2-4", "3-3-4",
            "2-3-5", "5-2-3", "3-4-2-1", "4-3-1-2", "4-2-2-2"
        ]
        
        # Learning parameters
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        self.gamma = 0.9  # Discount factor for future rewards
        
        # State-Action-Value functions (Q-tables)
        self.formation_weights = {f: 1.0 for f in self.formations}
        self.player_position_ratings = defaultdict(lambda: defaultdict(lambda: 1.0))
        self.player_chemistry = defaultdict(lambda: defaultdict(lambda: 1.0))
        self.tactics_memory = defaultdict(list)
        self.transfer_value_estimates = defaultdict(float)  # Player value estimates
        
        # Experience replay memory
        self.match_history = []
        self.matches_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.transfer_history = []
        self.lineup_history = []
        self.performance_history = []
        
        # Performance metrics
        self.total_rewards = 0
        self.episode_rewards = []
        self.match_rewards = []
        
        # Current state
        self.formation = self.formations[0]  # Start with default formation
        self.tactics = self._initialize_tactics()
        
        # Action spaces
        self.tactical_actions = {
            "offensive": list(range(30, 81, 5)),  # 30-80 in steps of 5
            "defensive": list(range(30, 81, 5)),
            "pressure": list(range(30, 81, 5))
        }
        
    def _get_positions_for_formation(self, formation):
        """Convert formation string to list of required positions."""
        parts = formation.split('-')
        def_count = int(parts[0])
        fwd_count = int(parts[-1])
        # Sum up all middle numbers for midfielders
        mid_count = sum(int(x) for x in parts[1:-1])
        
        positions = ["GK"]  # Always need a goalkeeper
        
        # Add defenders
        if def_count == 3:
            positions.extend(["CB", "CB", "CB"])
        elif def_count == 4:
            positions.extend(["LB", "CB", "CB", "RB"])
        elif def_count == 5:
            positions.extend(["LWB", "CB", "CB", "CB", "RWB"])
        
        # Add midfielders
        mid_positions = ["CM", "CDM", "CAM"]
        positions.extend(random.choices(mid_positions, k=mid_count))
        
        # Add forwards
        fwd_positions = ["ST", "CF", "LW", "RW"]
        positions.extend(random.choices(fwd_positions, k=fwd_count))
        
        return positions
    
    def _initialize_tactics(self):
        """Initialize tactics with some randomization for exploration."""
        return {
            "offensive": random.randint(40, 60),
            "defensive": random.randint(40, 60),
            "pressure": random.randint(40, 60)
        }
        
    def _select_formation(self):
        """Select formation using weighted probability based on past success."""
        if random.random() < self.exploration_rate:
            return random.choice(self.formations)  # Explore
        else:
            # Use softmax selection based on formation weights
            weights = np.array(list(self.formation_weights.values()))
            weights = np.exp(weights - np.max(weights))  # Numerical stability
            weights = weights / weights.sum()
            return np.random.choice(self.formations, p=weights)
    
    def get_state(self):
        """Get current state representation for learning."""
        if not self.team:
            return None
            
        state = {
            "formation": self.formation,
            "tactics": self.tactics.copy(),
            "squad_size": len(self.team.players),
            "team_strength": self.team.get_squad_strength(),
            "budget": self.team.budget,
            "recent_performance": self._get_recent_performance()
        }
        return state
    
    def _get_recent_performance(self):
        """Calculate recent performance metrics."""
        if not self.match_history:
            return {"wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}
        
        recent_matches = self.match_history[-5:]
        performance = defaultdict(int)
        for match in recent_matches:
            if match["result"]["winner"]:
                performance["wins"] += 1
            elif match["result"]["draw"]:
                performance["draws"] += 1
            else:
                performance["losses"] += 1
        return performance
    
    def learn_from_experience(self, old_state, action, reward, new_state):
        """Update Q-values based on experience."""
        if not old_state or not new_state:
            return
            
        # Q-learning update
        if action["type"] == "formation":
            current_q = self.formation_weights[action["value"]]
            max_future_q = max(self.formation_weights.values())
            new_q = current_q + self.learning_rate * (reward + self.gamma * max_future_q - current_q)
            self.formation_weights[action["value"]] = new_q
            
        elif action["type"] == "tactics":
            formation = old_state["formation"]
            if self.tactics_memory[formation]:
                success_rate = sum(1 for t in self.tactics_memory[formation] 
                                 if self._similar_tactics(t, action["value"]))
                success_rate /= len(self.tactics_memory[formation])
                if success_rate < reward:  # New tactics performed better
                    self.tactics_memory[formation].append(action["value"])
        
        elif action["type"] == "transfer":
            player = action["player"]
            price = action["price"]
            self.transfer_value_estimates[player.name] = (
                self.transfer_value_estimates[player.name] * 0.9 +
                0.1 * (price * (1 + reward))  # Adjust value estimate based on performance
            )
    
    def _similar_tactics(self, tactics1, tactics2):
        """Check if two tactical setups are similar."""
        return all(abs(tactics1[k] - tactics2[k]) < 10 for k in tactics1)
    
    def select_lineup(self, available_players, formation=None):
        """Select optimal lineup using learned player performances."""
        state = self.get_state()
        
        # Exploration vs exploitation
        if random.random() < self.exploration_rate:
            formation = random.choice(self.formations)  # Explore
        else:
            formation = max(self.formation_weights.items(), key=lambda x: x[1])[0]  # Exploit
        
        self.formation = formation
        positions_needed = self._get_positions_for_formation(formation)
        lineup = []
        assigned_positions = []
        
        # Select players using learned position ratings and chemistry
        for position in positions_needed:
            best_player = None
            best_rating = -1
            
            for player in available_players:
                if player in lineup:
                    continue
                
                # Calculate total rating including chemistry
                base_rating = self.player_position_ratings[player.name][position]
                chemistry_bonus = sum(self.player_chemistry[player.name][p.name] 
                                   for p in lineup) / (len(lineup) + 1) if lineup else 1.0
                
                final_rating = base_rating * chemistry_bonus
                
                if final_rating > best_rating:
                    best_rating = final_rating
                    best_player = player
            
            if best_player:
                lineup.append(best_player)
                assigned_positions.append(position)
                
                # Record action for learning
                self.lineup_history.append({
                    "state": state,
                    "action": {"player": best_player.name, "position": position},
                    "rating": best_rating
                })
        
        return lineup, assigned_positions
    
    def make_transfer_decision(self, transfer_market):
        """Make transfer decisions using reinforcement learning."""
        state = self.get_state()
        actions = []
        
        # Consider selling players
        squad_size = len(self.team.players)
        for player in self.team.players:
            rating = self.player_position_ratings[player.name][player.position]
            value_estimate = self.transfer_value_estimates[player.name]
            
            # Decide to sell if:
            # 1. Squad is too large, or
            # 2. Player consistently underperforms, or
            # 3. Good profit opportunity
            if (squad_size > 18 and rating < 0.6) or value_estimate > transfer_market.calculate_player_value(player) * 1.5:
                actions.append(("list", player, value_estimate * 1.2))
        
        # Consider buying players
        if self.team.budget > 1000000:
            available = transfer_market.get_available_players(max_price=self.team.budget)
            needs = self.team.get_squad_needs()
            
            for listing in available:
                if random.random() < self.exploration_rate:  # Exploration
                    if squad_size < 23:
                        actions.append(("buy", listing, listing.asking_price * 0.9))
                else:  # Exploitation
                    score = self.analyze_transfer_target(listing.player, listing.asking_price)
                    position_group = self._get_position_group(listing.player.position)
                    
                    # Higher chance to buy if position needed
                    if position_group in [need[0] for need in needs["needs"]]:
                        score *= 1.2
                    
                    if score > 0.6:
                        actions.append(("buy", listing, listing.asking_price * 0.9))
        
        # Record decisions for learning
        for action in actions:
            self.transfer_history.append({
                "state": state,
                "action": {"type": action[0], "player": action[1].name if action[0] == "list" else action[1].player.name,
                          "price": action[2]},
                "timestamp": len(self.transfer_history)
            })
        
        return actions
    
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
    
    def adapt_to_match_state(self, match_state):
        """Adapt tactics based on current match state."""
        state = self.get_state()
        
        # Calculate optimal tactical adjustments
        if match_state["losing"]:
            self.tactics["offensive"] = min(100, self.tactics["offensive"] + 10)
            self.tactics["pressure"] = min(100, self.tactics["pressure"] + 10)
        elif match_state["winning"]:
            self.tactics["defensive"] = min(100, self.tactics["defensive"] + 10)
        
        # Record adaptation for learning
        self.performance_history.append({
            "state": state,
            "action": {"type": "tactics_adjustment", "new_tactics": self.tactics.copy()},
            "match_state": match_state
        })
    
    def update_from_match_result(self, result, lineup, positions):
        """Learn from match results."""
        reward = 1.0 if result["winner"] else 0.5 if result["draw"] else 0.0
        self.total_rewards += reward
        self.episode_rewards.append(reward)
        
        # Update formation weights
        self.formation_weights[self.formation] += self.learning_rate * (reward - 0.5)
        
        # Update player ratings
        for player, position in zip(lineup, positions):
            current_rating = self.player_position_ratings[player.name][position]
            self.player_position_ratings[player.name][position] += (
                self.learning_rate * (reward - current_rating)
            )
        
        # Update chemistry ratings
        for i, player1 in enumerate(lineup):
            for j, player2 in enumerate(lineup):
                if i != j:
                    current_chemistry = self.player_chemistry[player1.name][player2.name]
                    self.player_chemistry[player1.name][player2.name] += (
                        self.learning_rate * (reward - current_chemistry)
                    )
        
        # Adjust exploration rate based on performance
        if len(self.episode_rewards) >= 5:
            avg_reward = sum(self.episode_rewards[-5:]) / 5
            if avg_reward < 0.4:
                self.exploration_rate = min(0.5, self.exploration_rate + 0.1)
            elif avg_reward > 0.6:
                self.exploration_rate = max(0.1, self.exploration_rate - 0.05)
    
    def get_learning_stats(self):
        """Get current learning statistics."""
        matches_played = len(self.match_history)
        if matches_played == 0:
            return {
                "total_rewards": 0,
                "win_rate": 0,
                "exploration_rate": self.exploration_rate,
                "learning_rate": self.learning_rate,
                "formation_preferences": sorted(self.formation_weights.items(), key=lambda x: x[1], reverse=True),
                "matches_played": 0
            }
        
        wins = sum(1 for match in self.match_history if match["result"]["winner"])
        draws = sum(1 for match in self.match_history if match["result"]["draw"])
        
        return {
            "total_rewards": self.total_rewards,
            "win_rate": (wins / matches_played) * 100,
            "draw_rate": (draws / matches_played) * 100,
            "exploration_rate": self.exploration_rate,
            "learning_rate": self.learning_rate,
            "formation_preferences": sorted(self.formation_weights.items(), key=lambda x: x[1], reverse=True),
            "matches_played": matches_played,
            "wins": wins,
            "draws": draws,
            "losses": matches_played - wins - draws
        }
    
    
    def getstats(self):
        """Get current learning statistics."""

        return {
            "total_rewards": self.total_rewards,
            "win_rate": (self.wins / self.matches_played) * 100,
            "draw_rate": (self.draws / self.matches_played) * 100,
            "exploration_rate": self.exploration_rate,
            "learning_rate": self.learning_rate,
            "formation_preferences": sorted(self.formation_weights.items(), key=lambda x: x[1], reverse=True),
            "matches_played": self.matches_played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses
        }