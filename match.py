import random
import math
from dataclasses import dataclass
from typing import Any, List, Dict, Tuple
from match_db import save_match_to_db

@dataclass
class MatchEvent:
    minute: int
    type: str
    player: str
    team: str
    details: str = ""

@dataclass
class Substitution:
    minute: int
    team: str
    player_out: str
    player_in: str
    reason: str = "tactical"

class Match:
    def __init__(self, home_team, away_team):
        """
        Initialize a match between two teams.
        
        Args:
            home_team (Team): Home team
            away_team (Team): Away team
        """
        self.home_team = home_team
        self.away_team = away_team
        self.score = [0, 0]  # [home, away]
        self.possession = [0, 0]  # Possession time in minutes
        self.shots = [0, 0]  # [home shots, away shots]
        self.shots_on_target = [0, 0]
        self.passes_attempted = [0, 0]  # [home, away]
        self.passes_completed = [0, 0]
        self.fouls = [0, 0]
        self.corners = [0, 0]
        self.offsides = [0, 0]
        self.player_stats = {}  # {player_id: {stat_name: value}}
        self.events: List[MatchEvent] = []
        self.substitutions: List[Substitution] = []
        self.minute = 0
        self.current_possession = "home"  # Who has the ball
        self.fatigue_factor = 0.88  # Player stamina reduction per action
        
        # Enhanced match attributes
        self.home_advantage = 1.1  # 10% boost for home team
        self.intensity = random.uniform(0.8, 1.2)
        self.weather = random.choice(["sunny", "rainy", "windy", "snowy"])
        
        # Substitution tracking
        self.home_substitutions_made = 0
        self.away_substitutions_made = 0
        self.max_substitutions = 5  # Modern football allows 5 subs
        
        # Cards and disciplinary
        self.home_players_sent_off = []
        self.away_players_sent_off = []
        
        # Initialize lineups
        self.home_lineup = []
        self.home_positions = []
        self.home_bench = []
        self.away_lineup = []
        self.away_positions = []
        self.away_bench = []
        
        # Updated weather effects (more balanced)
        self.weather_effects = {
            "sunny": {"passing": 1.0, "shooting": 1.0, "dribbling": 1.0},
            "rainy": {"passing": 0.9, "shooting": 0.95, "dribbling": 0.85},
            "windy": {"passing": 0.85, "shooting": 0.9, "dribbling": 0.95},
            "snowy": {"passing": 0.8, "shooting": 0.85, "dribbling": 0.8}
        }
    
    def _calculate_position_penalty(self, player, assigned_position):
        """Calculate performance penalty for playing out of position."""
        # Position groups
        defenders = ["CB", "LB", "RB", "SW", "LWB", "RWB"]
        midfielders = ["CM", "CDM", "CAM", "LM", "RM", "DM"]
        forwards = ["ST", "CF", "SS", "LW", "RW"]
        
        # No penalty for playing in natural position
        if player.position == assigned_position:
            return 1.0
            
        # Calculate penalty based on position groups
        if player.position in defenders:
            if assigned_position in defenders:
                return 0.9  # Small penalty for different defensive position
            elif assigned_position in midfielders:
                return 0.7  # Larger penalty for playing midfield
            else:
                return 0.5  # Major penalty for playing forward
        elif player.position in midfielders:
            if assigned_position in midfielders:
                return 0.9
            else:
                return 0.7  # Same penalty for playing defense or forward
        elif player.position in forwards:
            if assigned_position in forwards:
                return 0.9
            elif assigned_position in midfielders:
                return 0.7
            else:
                return 0.5
        elif player.position == "GK":
            return 0.3  # Severe penalty for goalkeeper playing outfield
        else:
            return 0.7  # Default penalty
    
    def _get_team_stats(self, team, opposition_tactics):
        """Calculate team stats considering formations, tactics, weather, and player development."""
        # Get lineup based on team
        lineup = self.home_lineup if team == self.home_team else self.away_lineup
        positions = self.home_positions if team == self.home_team else self.away_positions
        
        # Filter out sent off players
        sent_off = self.home_players_sent_off if team == self.home_team else self.away_players_sent_off
        active_lineup = [p for p in lineup if p not in sent_off]
        
        # Calculate average team rating from current player attributes
        total_rating = 0
        player_count = 0
        for i, player in enumerate(lineup):
            if player in sent_off:
                continue  # Skip sent off players
                
            # Calculate player's current effectiveness
            attribute_avg = sum(
                sum(cat.values()) for cat in player.attributes.values()
            ) / sum(len(cat) for cat in player.attributes.values())
            
            # Apply position penalty
            position = positions[i] if i < len(positions) else player.position
            position_factor = self._calculate_position_penalty(player, position)
            
            # Apply fitness factor
            fitness_factor = player.stats["fitness"] / 100
            
            # Apply form factor
            form_factor = player.get_form_rating()
            
            # Calculate final player rating
            player_rating = attribute_avg * position_factor * fitness_factor * form_factor
            total_rating += player_rating
            player_count += 1
        
        team_rating = total_rating / player_count if player_count > 0 else 30
        
        # Apply home advantage
        if team == self.home_team:
            team_rating *= self.home_advantage
        
        # Apply formation bonuses
        formation_bonus = {
            "4-3-3": {"attack": 1.1, "defense": 0.95},
            "4-4-2": {"attack": 1.0, "defense": 1.0},
            "5-3-2": {"attack": 0.85, "defense": 1.15},
            "3-5-2": {"attack": 1.05, "defense": 0.9},
            "4-2-3-1": {"attack": 1.05, "defense": 1.05}
        }
        
        # Manager's influence
        if team.manager:
            formation = team.manager.formation
            formation_mod = formation_bonus.get(formation, {"attack": 1.0, "defense": 1.0})
            tactics = team.manager.tactics
            
            # Tactical advantage calculation
            if tactics["offensive"] > opposition_tactics.get("defensive", 50):
                team_rating *= 1.05
            if tactics["defensive"] < opposition_tactics.get("offensive", 50):
                team_rating *= 0.98
            
            # Formation influence
            team_rating *= (formation_mod["attack"] + formation_mod["defense"]) / 2
        
        # Weather influence (reduced impact)
        weather_mod = sum(self.weather_effects[self.weather].values()) / 3
        team_rating *= weather_mod
        
        # Penalty for being down to 10 or fewer players
        if len(active_lineup) < 11:
            penalty = 0.9 ** (11 - len(active_lineup))  # 10% penalty per missing player
            team_rating *= penalty
        
        return team_rating
    
    def _calculate_card_probability(self, player, action_type, tackle_success=True):
        """Calculate probability of receiving a card based on action and player attributes"""
        base_prob = 0.0
        
        if action_type == "tackle":
            # Higher aggression = higher card probability
            aggression = player.attributes.get("physical", {}).get("aggression", 50)
            base_prob = 0.02 + (aggression / 100) * 0.03
            
            # Failed tackles more likely to get cards
            if not tackle_success:
                base_prob *= 2.0
                
        elif action_type == "foul":
            aggression = player.attributes.get("physical", {}).get("aggression", 50)
            base_prob = 0.05 + (aggression / 100) * 0.05
            
        # Red card probability (much lower)
        red_prob = base_prob * 0.1
        
        return min(0.15, base_prob), min(0.02, red_prob)
    
    def _attempt_substitution(self, team, minute):
        """Attempt to make a substitution for tired or injured players"""
        is_home = team == self.home_team
        lineup = self.home_lineup if is_home else self.away_lineup
        bench = self.home_bench if is_home else self.away_bench
        subs_made = self.home_substitutions_made if is_home else self.away_substitutions_made
        sent_off = self.home_players_sent_off if is_home else self.away_players_sent_off
        
        if subs_made >= self.max_substitutions or not bench:
            return False
            
        # Find players who need substitution
        candidates_out = []
        for player in lineup:
            if player in sent_off:
                continue
                
            # Substitute if injured
            if player.is_injured:
                candidates_out.append((player, "injury", 1.0))
                continue
                
            # Substitute if very tired
            if player.stats["fitness"] < 30:
                candidates_out.append((player, "fatigue", 0.8))
                continue
                
            # Tactical substitution for poor form
            if player.get_form_rating() < 0.4 and minute > 60:
                candidates_out.append((player, "poor_form", 0.3))
                
        if not candidates_out:
            return False
            
        # Sort by priority and pick the most urgent
        candidates_out.sort(key=lambda x: x[2], reverse=True)
        player_out, reason, priority = candidates_out[0]
        
        # Only make substitution if priority is high enough or it's late in game
        if priority < 0.6 and minute < 70:
            return False
        
        # Find best replacement from bench
        best_sub = None
        best_rating = 0
        
        for sub_player in bench:
            if not sub_player.is_available_for_selection():
                continue
                
            # Calculate sub player rating for the position
            sub_rating = sub_player.get_overall_rating()
            position_factor = self._calculate_position_penalty(sub_player, player_out.position)
            fitness_factor = sub_player.stats["fitness"] / 100
            
            total_rating = sub_rating * position_factor * fitness_factor
            
            if total_rating > best_rating:
                best_rating = total_rating
                best_sub = sub_player
        
        if best_sub:
            # Make the substitution
            substitution = Substitution(
                minute=minute,
                team="home" if is_home else "away",
                player_out=player_out.name,
                player_in=best_sub.name,
                reason=reason
            )
            self.substitutions.append(substitution)
            
            # Update lineups
            lineup_index = lineup.index(player_out)
            lineup[lineup_index] = best_sub
            bench.remove(best_sub)
            bench.append(player_out)
            
            # Update substitution count
            if is_home:
                self.home_substitutions_made += 1
            else:
                self.away_substitutions_made += 1
                
            # Add event
            self.events.append(MatchEvent(
                minute,
                "substitution",
                best_sub.name,
                "home" if is_home else "away",
                f"{player_out.name} replaced by {best_sub.name} ({reason})"
            ))
            
            return True
            
        return False
    
    def _calculate_action_success(self, attacking_team, defending_team, action_type):
        """Calculate probability of successful action."""
        if attacking_team == self.home_team:
            att_idx, def_idx = 0, 1
        else:
            att_idx, def_idx = 1, 0
            
        # Get relevant player for the action
        if action_type == "shot":
            attacking_lineup = self.home_lineup if attacking_team == self.home_team else self.away_lineup
            defending_lineup = self.home_lineup if defending_team == self.home_team else self.away_lineup
            
            sent_off_att = self.home_players_sent_off if attacking_team == self.home_team else self.away_players_sent_off
            sent_off_def = self.home_players_sent_off if defending_team == self.home_team else self.away_players_sent_off
            
            attackers = [p for p in attacking_lineup if p.position in ["ST", "CF", "SS", "RW", "LW"] and p not in sent_off_att]
            if not attackers:
                return False
            attacker = random.choice(attackers)
            
            # Goalkeeper save chance
            defenders = [p for p in defending_lineup if p.position == "GK" and p not in sent_off_def]
            if not defenders:
                return True
            goalkeeper = defenders[0]
            
            shot_power = attacker.attributes["shooting"]["shot_power"]
            finishing = attacker.attributes["shooting"]["finishing"]
            goalkeeper_skill = sum(goalkeeper.attributes["goalkeeping"].values()) / 4
            
            # Consider fatigue and form
            stamina_factor = attacker.stats["fitness"] / 100
            form_factor = attacker.get_form_rating()
            
            # Calculate shot success probability
            shot_rating = (shot_power + finishing) / 2 * stamina_factor * form_factor
            save_rating = goalkeeper_skill * (goalkeeper.stats["fitness"] / 100) * goalkeeper.get_form_rating()
            
            # Weather impact on shooting
            weather_mod = self.weather_effects[self.weather]["shooting"]
            shot_rating *= weather_mod
            
            # Position penalty impact
            shot_position_mod = self._calculate_position_penalty(attacker, "ST")
            shot_rating *= shot_position_mod
            
            # Final probability calculation
            success_chance = (shot_rating - save_rating + 50) / 150  # Normalized to 0-1 range
            return random.random() < success_chance
            
        elif action_type == "pass":
            base_chance = 0.75  # Base 75% pass success rate
            
            attacking_lineup = self.home_lineup if attacking_team == self.home_team else self.away_lineup
            defending_lineup = self.home_lineup if defending_team == self.home_team else self.away_lineup
            
            sent_off_att = self.home_players_sent_off if attacking_team == self.home_team else self.away_players_sent_off
            sent_off_def = self.home_players_sent_off if defending_team == self.home_team else self.away_players_sent_off
            
            active_attackers = [p for p in attacking_lineup if p not in sent_off_att]
            active_defenders = [p for p in defending_lineup if p not in sent_off_def]
            
            if not active_attackers or not active_defenders:
                return base_chance > 0.5
            
            # Team passing ability vs opposition pressing
            pass_skill = sum(p.attributes["passing"]["vision"] for p in active_attackers) / len(active_attackers)
            defense_pressure = sum(p.attributes["defending"]["marking"] for p in active_defenders) / len(active_defenders)
            
            # Weather effect
            weather_mod = self.weather_effects[self.weather]["passing"]
            
            final_chance = base_chance * (pass_skill / max(1, defense_pressure)) * weather_mod
            return random.random() < min(0.95, final_chance)
            
        elif action_type == "tackle":
            attacking_lineup = self.home_lineup if attacking_team == self.home_team else self.away_lineup
            defending_lineup = self.home_lineup if defending_team == self.home_team else self.away_lineup
            
            sent_off_att = self.home_players_sent_off if attacking_team == self.home_team else self.away_players_sent_off
            sent_off_def = self.home_players_sent_off if defending_team == self.home_team else self.away_players_sent_off
            
            active_attackers = [p for p in attacking_lineup if p not in sent_off_att]
            active_defenders = [p for p in defending_lineup if p not in sent_off_def]
            
            if not active_attackers or not active_defenders:
                return False
                
            attacker = random.choice(active_attackers)
            defender = random.choice(active_defenders)
            
            dribble_skill = (attacker.attributes["dribbling"]["ball_control"] + 
                           attacker.attributes["dribbling"]["agility"]) / 2
            tackle_skill = (defender.attributes["defending"]["standing_tackle"] + 
                          defender.attributes["defending"]["sliding_tackle"]) / 2
            
            # Fitness and form factors
            att_condition = (attacker.stats["fitness"] / 100) * attacker.get_form_rating()
            def_condition = (defender.stats["fitness"] / 100) * defender.get_form_rating()
            
            success_chance = tackle_skill * def_condition / (dribble_skill * att_condition + tackle_skill * def_condition)
            
            # Check for cards if tackle fails
            tackle_success = random.random() < success_chance
            if not tackle_success:
                yellow_prob, red_prob = self._calculate_card_probability(defender, "tackle", False)
                
                if random.random() < red_prob:
                    card_result = defender.receive_card("red")
                    if card_result == "red":
                        self._send_off_player(defender, defending_team)
                        self.events.append(MatchEvent(
                            self.minute, "red_card", defender.name,
                            "home" if defending_team == self.home_team else "away",
                            f"{defender.name} receives a red card for a dangerous tackle!"
                        ))
                elif random.random() < yellow_prob:
                    card_result = defender.receive_card("yellow")
                    self.events.append(MatchEvent(
                        self.minute, "yellow_card", defender.name,
                        "home" if defending_team == self.home_team else "away",
                        f"{defender.name} receives a yellow card"
                    ))
                    if card_result == "red":  # Second yellow
                        self._send_off_player(defender, defending_team)
                        self.events.append(MatchEvent(
                            self.minute, "red_card", defender.name,
                            "home" if defending_team == self.home_team else "away",
                            f"{defender.name} sent off for second yellow card!"
                        ))
            
            return tackle_success
            
        return False
    
    def _send_off_player(self, player, team):
        """Send off a player (red card)"""
        if team == self.home_team:
            if player not in self.home_players_sent_off:
                self.home_players_sent_off.append(player)
        else:
            if player not in self.away_players_sent_off:
                self.away_players_sent_off.append(player)
    
    def _update_player_stats(self, player, action_type, success):
        """Update player statistics based on match actions."""
        # Fatigue calculation (reduced for realism)
        energy_cost = {
            "shot": 1.5,
            "pass": 0.5,
            "dribble": 1.0,
            "tackle": 1.5,
            "sprint": 2.0
        }
        
        # Apply fatigue
        base_cost = energy_cost.get(action_type, 0.8)
        intensity_cost = base_cost * self.intensity * 0.5  # Reduced fatigue
        player.stats["fitness"] = max(0, player.stats["fitness"] - intensity_cost)
        
        # Update other stats based on action success
        if action_type == "shot" and success:
            player.stats["goals"] += 1
        elif action_type == "tackle":
            if not success:
                player.stats["fouls_committed"] += 1

    def _maybe_injure_player(self, player):
        """Randomly injure a player based on fatigue, age, and match intensity."""
        if player.is_injured:
            return
            
        # Much more realistic injury rates
        base_chance = 0.00005  # Very low base chance per minute
        
        # Risk factors
        fatigue_factor = max(0, (100 - player.stats["fitness"]) / 200)  # 0-0.5
        age_factor = max(0, (player.age - 25) / 50) if player.age > 25 else 0  # 0-0.2
        intensity_factor = (self.intensity - 0.8) / 0.8  # 0-0.5
        
        # Physical position players slightly higher risk
        position_factor = 1.2 if player.position in ["CB", "CDM", "ST"] else 1.0
        
        total_chance = base_chance * (1 + fatigue_factor + age_factor + intensity_factor) * position_factor
        
        if random.random() < total_chance:
            # Determine injury severity
            severity_roll = random.random()
            if severity_roll < 0.7:
                injury_type = "minor"
            elif severity_roll < 0.9:
                injury_type = "moderate"
            elif severity_roll < 0.98:
                injury_type = "major"
            else:
                injury_type = "severe"
                
            player.apply_injury(injury_type)
            
            self.events.append(MatchEvent(
                self.minute,
                "injury",
                player.name,
                "home" if player in self.home_lineup else "away",
                f"{player.name} suffers a {injury_type} injury and may need to be substituted"
            ))

    def simulate_minute(self):
        """Simulate one minute of the match with enhanced realism."""
        # Determine action type based on possession and game state
        action_weights = [0.25, 0.55, 0.2]  # [attack, midfield, defense]
        
        # Adjust weights based on score and time
        if self.minute > 75:
            goal_diff = self.score[0] - self.score[1]
            if self.current_possession == "home":
                if goal_diff < 0:  # Home team behind, more attacking
                    action_weights = [0.4, 0.45, 0.15]
                elif goal_diff > 1:  # Home team well ahead, more defensive
                    action_weights = [0.15, 0.45, 0.4]
            else:  # Away possession
                if goal_diff > 0:  # Away team behind, more attacking
                    action_weights = [0.4, 0.45, 0.15]
                elif goal_diff < -1:  # Away team well ahead, more defensive
                    action_weights = [0.15, 0.45, 0.4]
        
        action = random.choices(
            ["attack", "midfield", "defense"],
            weights=action_weights
        )[0]
        
        if self.current_possession == "home":
            attacking_team = self.home_team
            defending_team = self.away_team
            score_idx = 0
        else:
            attacking_team = self.away_team
            defending_team = self.home_team
            score_idx = 1
        
        # Simulate action
        if action == "attack":
            # Attempt to create scoring opportunity
            self.passes_attempted[score_idx] += 1
            pass_success = self._calculate_action_success(attacking_team, defending_team, "pass")
            if pass_success:
                self.passes_completed[score_idx] += 1
                self.shots[score_idx] += 1
                if random.random() < 0.1:  # 10% chance for a corner
                    self.corners[score_idx] += 1
                if random.random() < 0.07:  # 7% chance for offside
                    self.offsides[score_idx] += 1
                if self._calculate_action_success(attacking_team, defending_team, "shot"):
                    self.score[score_idx] += 1
                    self.shots_on_target[score_idx] += 1
                    
                    # Find scorer and assister
                    attacking_lineup = self.home_lineup if attacking_team == self.home_team else self.away_lineup
                    sent_off = self.home_players_sent_off if attacking_team == self.home_team else self.away_players_sent_off
                    
                    active_players = [p for p in attacking_lineup if p not in sent_off]
                    
                    forwards = [p for p in active_players if p.position in ["ST", "CF", "SS"]]
                    midfielders = [p for p in active_players if p.position in ["CM", "CAM", "LM", "RM", "LW", "RW"]]
                    
                    if forwards:
                        scorer = random.choice(forwards)
                    elif midfielders:
                        scorer = random.choice(midfielders)
                    else:
                        scorer = random.choice(active_players) if active_players else None
                    
                    if scorer:
                        scorer.stats["goals"] += 1
                        
                        # Potential assist
                        potential_assisters = [p for p in active_players if p != scorer]
                        if potential_assisters and random.random() < 0.6:
                            assister = random.choice(potential_assisters)
                            assister.stats["assists"] += 1
                            event_details = f"Goal! {scorer.name} scores! Assisted by {assister.name}."
                        else:
                            event_details = f"Goal! {scorer.name} scores!"
                        
                        self.events.append(MatchEvent(
                            self.minute,
                            "goal",
                            scorer.name,
                            "home" if attacking_team == self.home_team else "away",
                            event_details
                        ))
                
                # Switch possession after attack
                if random.random() < 0.65:
                    self.current_possession = "away" if self.current_possession == "home" else "home"
            else:
                # Failed attack, possession changes
                self.fouls[score_idx] += 1 if random.random() < 0.15 else 0  # 15% chance for foul
                self.current_possession = "away" if self.current_possession == "home" else "home"
                
        elif action == "midfield":
            # Midfield battle
            if self._calculate_action_success(attacking_team, defending_team, "pass"):
                # Successful buildup
                if random.random() < 0.3:  # 30% chance to lose possession anyway
                    self.current_possession = "away" if self.current_possession == "home" else "home"
            else:
                # Lost possession
                self.current_possession = "away" if self.current_possession == "home" else "home"
                
        elif action == "defense":
            # Defensive action - attempt to win ball back
            if self._calculate_action_success(defending_team, attacking_team, "tackle"):
                # Successful tackle, defending team gets possession
                self.current_possession = "away" if self.current_possession == "home" else "home"
        
        # Update possession stats
        if self.current_possession == "home":
            self.possession[0] += 1
        else:
            self.possession[1] += 1
        
        # Update player fatigue and apply age decline
        for team in [self.home_team, self.away_team]:
            lineup = self.home_lineup if team == self.home_team else self.away_lineup
            for player in lineup:
                # Reduced fatigue per minute for realism
                fatigue = random.uniform(0.02, 0.05) * self.intensity
                player.stats["fitness"] = max(0, player.stats["fitness"] - fatigue)

                # Injury check (only for active players)
                self._maybe_injure_player(player)
                
                # Apply age decline (very gradually during matches)
                if random.random() < 0.001:  # Very rare during individual matches
                    player.apply_age_decline()
        
        # Attempt substitutions for both teams
        if self.minute > 45 and random.random() < 0.1:  # 10% chance per minute after halftime
            self._attempt_substitution(self.home_team, self.minute)
            self._attempt_substitution(self.away_team, self.minute)
        
        self.minute += 1
    
    def play_match(self):
        """
        Simulate the entire match with enhanced features.
        
        Returns:
            dict: Match statistics and events
        """
        # Select lineups using improved selection
        if self.home_team.manager:
            self.home_lineup, self.home_positions = self.home_team.manager.select_lineup(
                self.home_team.players,
                opponent=self.away_team
            )
        else:
            self.home_lineup, self.home_positions = self._select_default_lineup(self.home_team)

        if self.away_team.manager:
            self.away_lineup, self.away_positions = self.away_team.manager.select_lineup(
                self.away_team.players,
                opponent=self.home_team
            )
        else:
            self.away_lineup, self.away_positions = self._select_default_lineup(self.away_team)

        # Create bench (remaining players)
        self.home_bench = [p for p in self.home_team.players if p not in self.home_lineup and p.is_available_for_selection()]
        self.away_bench = [p for p in self.away_team.players if p not in self.away_lineup and p.is_available_for_selection()]

        # Validate lineups
        self.home_lineup, self.home_positions = self._validate_lineup(self.home_lineup, self.home_positions, self.home_team)
        self.away_lineup, self.away_positions = self._validate_lineup(self.away_lineup, self.away_positions, self.away_team)
        
        # Simulate 90 minutes + injury time
        injury_time = random.randint(1, 5)
        total_minutes = 90 + injury_time
        
        for minute in range(total_minutes):
            self.simulate_minute()
            
        # Update player appearances and minutes
        for player in self.home_lineup:
            player.stats["appearances"] += 1
            player.stats["minutes_played"] += total_minutes
        for player in self.away_lineup:
            player.stats["appearances"] += 1
            player.stats["minutes_played"] += total_minutes
            
        # Post-match fitness recovery
        for team in [self.home_team, self.away_team]:
            for player in team.players:
                # Recovery based on whether they played
                if player in self.home_lineup or player in self.away_lineup:
                    recovery = random.randint(20, 40)  # Starters recover less
                else:
                    recovery = random.randint(40, 60)  # Bench players recover more
                
                player.stats["fitness"] = min(100, player.stats["fitness"] + recovery)
                
                # Process injury recovery
                player.recover_from_injury(1)
        
        # Calculate match ratings for form updates
        for player in self.home_lineup + self.away_lineup:
            # Base rating influenced by team performance and individual contributions
            team_performance = 0.7 if (player in self.home_lineup and self.score[0] >= self.score[1]) or \
                                   (player in self.away_lineup and self.score[1] >= self.score[0]) else 0.4
            
            individual_performance = random.uniform(0.3, 0.9)
            fitness_factor = player.stats["fitness"] / 100
            
            match_rating = (team_performance + individual_performance) * fitness_factor
            player.update_form(match_rating)
        
        from datetime import datetime
        # Enhanced match summary
        summary = {
            "date": datetime.now().isoformat(),
            "home_team_id": self.home_team.team_id,
            "away_team_id": self.away_team.team_id,
            "score": self.score,
            "possession": [p/total_minutes*100 for p in self.possession],
            "shots": self.shots,
            "shots_on_target": self.shots_on_target,
            "passes_attempted": self.passes_attempted,
            "passes_completed": self.passes_completed,
            "fouls": self.fouls,
            "corners": self.corners,
            "offsides": self.offsides,
            "weather": self.weather,
            "events": self.events,
            "substitutions": self.substitutions,
            "cards": {
                "home_yellows": sum(p.stats["yellow_cards"] for p in self.home_lineup),
                "away_yellows": sum(p.stats["yellow_cards"] for p in self.away_lineup),
                "home_reds": sum(p.stats["red_cards"] for p in self.home_lineup),
                "away_reds": sum(p.stats["red_cards"] for p in self.away_lineup)
            },
            "injuries": len([e for e in self.events if e.type == "injury"]),
            "total_minutes": total_minutes
        }
        
        # Provide enhanced feedback to managers for learning
        if self.home_team.manager:
            home_result = {
                "winner": self.score[0] > self.score[1],
                "draw": self.score[0] == self.score[1],
                "goals_for": self.score[0],
                "goals_against": self.score[1],
                "possession": self.possession[0],
                "shots": self.shots[0],
                "shots_on_target": self.shots_on_target[0],
                "cards": summary["cards"]["home_yellows"] + summary["cards"]["home_reds"],
                "injuries": len([e for e in self.events if e.type == "injury" and e.team == "home"]),
                "substitutions_used": self.home_substitutions_made,
                "youth_minutes": self._calculate_youth_minutes(self.home_lineup),
                "player_development": self._calculate_player_development(self.home_lineup),
                "tactical_success": self._calculate_tactical_success(self.home_team, self.away_team),
                "formation_effectiveness": self._calculate_formation_effectiveness(self.home_team)
            }
            self.home_team.manager.learn_from_match(home_result)
            
        if self.away_team.manager:
            away_result = {
                "winner": self.score[1] > self.score[0],
                "draw": self.score[0] == self.score[1],
                "goals_for": self.score[1],
                "goals_against": self.score[0],
                "possession": self.possession[1],
                "shots": self.shots[1],
                "shots_on_target": self.shots_on_target[1],
                "cards": summary["cards"]["away_yellows"] + summary["cards"]["away_reds"],
                "injuries": len([e for e in self.events if e.type == "injury" and e.team == "away"]),
                "substitutions_used": self.away_substitutions_made,
                "youth_minutes": self._calculate_youth_minutes(self.away_lineup),
                "player_development": self._calculate_player_development(self.away_lineup),
                "tactical_success": self._calculate_tactical_success(self.away_team, self.home_team),
                "formation_effectiveness": self._calculate_formation_effectiveness(self.away_team)
            }
            self.away_team.manager.learn_from_match(away_result)
        
        return summary

    def _calculate_youth_minutes(self, lineup: List[Any]) -> float:
        """Calculate total minutes played by youth players (under 23)."""
        return sum(90 for player in lineup if player.age < 23)

    def _calculate_player_development(self, lineup: List[Any]) -> float:
        """Calculate average development potential for squad."""
        if not lineup:
            return 0.0
        
        total_potential = 0
        for player in lineup:
            current = player.get_overall_rating()
            potential = player.potential
            room_for_growth = (potential - current) / potential if potential > 0 else 0
            total_potential += room_for_growth
            
        return total_potential / len(lineup)

    def _calculate_tactical_success(self, team: Any, opponent: Any) -> float:
        """Calculate how well tactics countered the opponent."""
        if not (team.manager and opponent.manager):
            return 0.5
            
        team_tactics = team.manager.tactics
        opp_tactics = opponent.manager.tactics
        
        # Calculate tactical advantage
        offensive_success = team_tactics["offensive"] / max(1, opp_tactics["defensive"])
        defensive_success = team_tactics["defensive"] / max(1, opp_tactics["offensive"])
        pressure_success = team_tactics["pressure"] / max(1, opp_tactics["pressure"])
        
        # Weight and normalize the success rates
        return (offensive_success + defensive_success + pressure_success) / 6

    def _calculate_formation_effectiveness(self, team: Any) -> float:
        """Calculate how well the formation worked with available players."""
        if not team.manager:
            return 0.5
            
        lineup = self.home_lineup if team == self.home_team else self.away_lineup
        positions = self.home_positions if team == self.home_team else self.away_positions
        
        # Calculate average position suitability
        total_suitability = 0
        for player, position in zip(lineup, positions):
            suitability = self._calculate_position_penalty(player, position)
            total_suitability += suitability
            
        return total_suitability / len(lineup) if lineup else 0

    def _select_default_lineup(self, team: Any) -> Tuple[List[Any], List[str]]:
        """Select a default lineup when no manager is present, considering injuries and fitness."""
        available_players = [p for p in team.players if p.is_available_for_selection()]
        
        goalkeepers = [p for p in available_players if p.position == "GK"]
        defenders = [p for p in available_players if p.position in ["CB", "LB", "RB", "SW", "LWB", "RWB"]]
        midfielders = [p for p in available_players if p.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]]
        forwards = [p for p in available_players if p.position in ["ST", "CF", "SS", "LW", "RW"]]
        
        # Sort by overall rating and fitness
        for group in [goalkeepers, defenders, midfielders, forwards]:
            group.sort(key=lambda p: p.get_overall_rating() * (p.stats["fitness"]/100), reverse=True)
        
        lineup = []
        positions = []
        
        # Default 4-4-2 formation
        if goalkeepers:
            lineup.append(goalkeepers[0])
            positions.append("GK")
        
        # Add 4 defenders
        needed_defenders = min(4, len(defenders))
        lineup.extend(defenders[:needed_defenders])
        def_positions = ["CB", "CB", "LB", "RB"][:needed_defenders]
        positions.extend(def_positions)
        
        # Add 4 midfielders
        needed_midfielders = min(4, len(midfielders))
        lineup.extend(midfielders[:needed_midfielders])
        mid_positions = ["CM", "CM", "LM", "RM"][:needed_midfielders]
        positions.extend(mid_positions)
        
        # Add 2 forwards
        needed_forwards = min(2, len(forwards))
        lineup.extend(forwards[:needed_forwards])
        fwd_positions = ["ST", "ST"][:needed_forwards]
        positions.extend(fwd_positions)
        
        return lineup[:11], positions[:11]

    def _validate_lineup(self, lineup: List[Any], positions: List[str], team: Any) -> Tuple[List[Any], List[str]]:
        """Ensure lineup meets minimum requirements and all players are available."""
        # Filter out unavailable players
        available_lineup = []
        available_positions = []
        
        for player, position in zip(lineup, positions):
            if player.is_available_for_selection():
                available_lineup.append(player)
                available_positions.append(position)
        
        # Must have at least 1 goalkeeper
        gk_count = sum(1 for pos in available_positions if pos == "GK")
        if gk_count < 1:
            available_gks = [p for p in team.players if p.position == "GK" and p.is_available_for_selection()]
            if available_gks:
                # Replace a non-GK with a GK
                if available_lineup:
                    available_lineup[0] = available_gks[0]
                    available_positions[0] = "GK"
                else:
                    available_lineup.append(available_gks[0])
                    available_positions.append("GK")
                
        # Ensure exactly 11 players (or as many as available)
        if len(available_lineup) > 11:
            available_lineup = available_lineup[:11]
            available_positions = available_positions[:11]
        elif len(available_lineup) < 7:  # FIFA minimum
            # Try to fill with any available players
            remaining_players = [p for p in team.players 
                               if p not in available_lineup and p.is_available_for_selection()]
            for player in remaining_players:
                if len(available_lineup) >= 11:
                    break
                available_lineup.append(player)
                available_positions.append(player.position)
            
            if len(available_lineup) < 7:
                raise ValueError(f"Insufficient players available for {team.name}: only {len(available_lineup)} available")
                
        return available_lineup, available_positions
