import random
import math
from dataclasses import dataclass
from typing import Any, List, Dict, Tuple

@dataclass
class MatchEvent:
    minute: int
    type: str
    player: str
    team: str
    details: str = ""

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
        self.events: List[MatchEvent] = []
        self.minute = 0
        self.current_possession = "home"  # Who has the ball
        self.fatigue_factor = 0.98  # Player stamina reduction per action
        
        # Match intensity affects player fatigue
        self.intensity = random.uniform(0.8, 1.2)
        
        # Weather conditions affect play style
        self.weather = random.choice(["sunny", "rainy", "windy", "snowy"])
        
        # Initialize lineups
        self.home_lineup = []
        self.home_positions = []
        self.away_lineup = []
        self.away_positions = []
        
        self.weather_effects = {
            "sunny": {"passing": 1.0, "shooting": 1.0, "dribbling": 1.0},
            "rainy": {"passing": 0.8, "shooting": 0.9, "dribbling": 0.7},
            "windy": {"passing": 0.7, "shooting": 0.8, "dribbling": 0.9},
            "snowy": {"passing": 0.6, "shooting": 0.7, "dribbling": 0.6}
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
        
        # Calculate average team rating from current player attributes
        total_rating = 0
        player_count = 0
        for player, position in zip(lineup, positions):
            # Calculate player's current effectiveness
            attribute_avg = sum(
                sum(cat.values()) for cat in player.attributes.values()
            ) / sum(len(cat) for cat in player.attributes.values())
            
            # Apply position penalty
            position_factor = self._calculate_position_penalty(player, position)
            
            # Apply fitness factor
            fitness_factor = player.stats["fitness"] / 100
            
            # Calculate final player rating
            player_rating = attribute_avg * position_factor * fitness_factor
            total_rating += player_rating
            player_count += 1
        
        team_rating = total_rating / player_count if player_count > 0 else 50
        
        # Apply formation bonuses
        formation_bonus = {
            "4-3-3": {"attack": 1.1, "defense": 0.9},
            "4-4-2": {"attack": 1.0, "defense": 1.0},
            "5-3-2": {"attack": 0.8, "defense": 1.2},
            "3-5-2": {"attack": 1.1, "defense": 0.9}
        }
        
        # Get current lineup and positions
        if team == self.home_team:
            formation = team.manager.formation if team.manager else "4-4-2"
            required_positions = []
            # Add required positions based on formation
            required_positions.append("GK")  # Always need a goalkeeper
            def_count = int(formation[0])
            mid_count = int(formation[2])
            fwd_count = int(formation[4])
            required_positions.extend(["CB"] * def_count)
            required_positions.extend(["CM"] * mid_count)
            required_positions.extend(["ST"] * fwd_count)
            
            # Calculate average performance with position penalties
            total_performance = 0
            players_used = 0
            for player, position in zip(team.players[:11], required_positions):
                position_factor = self._calculate_position_penalty(player, position)
                player_rating = team.get_squad_strength()  # Individual player rating
                total_performance += player_rating * position_factor
                players_used += 1
            
            # Base stats from average performance
            stats = total_performance / players_used if players_used > 0 else team.get_squad_strength()
        
        # Manager's influence
        if team.manager:
            formation_mod = formation_bonus.get(team.manager.formation, {"attack": 1.0, "defense": 1.0})
            tactics = team.manager.tactics
            
            # Tactical advantage calculation
            if tactics["offensive"] > opposition_tactics["defensive"]:
                stats *= 1.1
            if tactics["defensive"] < opposition_tactics["offensive"]:
                stats *= 0.9
            
            # Formation influence
            stats *= (formation_mod["attack"] + formation_mod["defense"]) / 2
        
        # Weather influence
        weather_mod = sum(self.weather_effects[self.weather].values()) / 3
        stats *= weather_mod
        
        return stats
    
    def _calculate_action_success(self, attacking_team, defending_team, action_type):
        """Calculate probability of successful action."""
        if attacking_team == self.home_team:
            att_idx, def_idx = 0, 1
        else:
            att_idx, def_idx = 1, 0
            
        # Get relevant player for the action
        if action_type == "shot":
            attackers = [p for p in attacking_team.players if p.position in ["ST", "CF", "SS", "RW", "LW"]]
            if not attackers:
                return False
            attacker = random.choice(attackers)
            
            # Goalkeeper save chance
            defenders = [p for p in defending_team.players if p.position == "GK"]
            if not defenders:
                return True
            goalkeeper = defenders[0]
            
            shot_power = attacker.attributes["shooting"]["shot_power"]
            finishing = attacker.attributes["shooting"]["finishing"]
            goalkeeper_skill = sum(goalkeeper.attributes["goalkeeping"].values()) / 4
            
            # Consider fatigue
            stamina_factor = attacker.stats["fitness"] / 100
            
            # Calculate shot success probability
            shot_rating = (shot_power + finishing) / 2 * stamina_factor * 2  # Double the base chance
            save_rating = goalkeeper_skill * (goalkeeper.stats["fitness"] / 100)
            
            # Weather impact on shooting
            weather_mod = self.weather_effects[self.weather]["shooting"]
            shot_rating *= weather_mod
            
            # Position penalty impact
            shot_position_mod = self._calculate_position_penalty(attacker, "ST")
            shot_rating *= shot_position_mod
            
            # Final probability calculation
            success_chance = (shot_rating - save_rating + 100) / 200  # Normalize to 0-1 range
            return random.random() < success_chance
            
        elif action_type == "pass":
            base_chance = 0.7  # Base 70% pass success rate
            passing_team = attacking_team.players
            defending_team = defending_team.players
            
            # Team passing ability vs opposition pressing
            pass_skill = sum(p.attributes["passing"]["vision"] for p in passing_team) / len(passing_team)
            defense_pressure = sum(p.attributes["defending"]["marking"] for p in defending_team) / len(defending_team)
            
            # Weather effect
            weather_mod = self.weather_effects[self.weather]["passing"]
            
            final_chance = base_chance * (pass_skill / defense_pressure) * weather_mod
            return random.random() < final_chance
            
        elif action_type == "dribble":
            dribblers = [p for p in attacking_team.players if p.position not in ["GK", "CB"]]
            if not dribblers:
                return False
            dribbler = random.choice(dribblers)
            
            dribble_skill = (dribbler.attributes["dribbling"]["ball_control"] + 
                           dribbler.attributes["dribbling"]["agility"]) / 2
            stamina_factor = dribbler.stats["fitness"] / 100
            weather_mod = self.weather_effects[self.weather]["dribbling"]
            
            return random.random() < (dribble_skill * stamina_factor * weather_mod / 100)
    
    def _update_player_stats(self, player, action_type, success):
        """Update player statistics based on match actions."""
        # Fatigue calculation
        energy_cost = {
            "shot": 2,
            "pass": 1,
            "dribble": 1.5,
            "tackle": 2,
            "sprint": 2.5
        }
        
        # Apply fatigue
        base_cost = energy_cost.get(action_type, 1)
        intensity_cost = base_cost * self.intensity
        player.stats["fitness"] = max(0, player.stats["fitness"] - intensity_cost)
        
        # Update other stats based on action success
        if action_type == "shot" and success:
            player.stats["goals"] += 1
        elif action_type == "tackle":
            if not success and random.random() < 0.3:  # 30% chance of yellow card on failed tackle
                player.stats["yellow_cards"] += 1
    
    def simulate_minute(self):
        """Simulate one minute of the match."""
        # Determine action type
        action = random.choices(
            ["attack", "midfield", "defense"],
            weights=[0.3, 0.5, 0.2]
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
            if self._calculate_action_success(attacking_team, defending_team, "pass"):
                self.shots[score_idx] += 1
                if self._calculate_action_success(attacking_team, defending_team, "shot"):
                    self.score[score_idx] += 1
                    self.shots_on_target[score_idx] += 1
                    
                    # Find scorer
                    scorers = [p for p in attacking_team.players if p.position in ["ST", "CF", "SS", "RW", "LW"]]
                    if scorers:
                        scorer = random.choice(scorers)
                        self._update_player_stats(scorer, "shot", True)
                        self.events.append(MatchEvent(
                            self.minute,
                            "goal",
                            scorer.name,
                            "home" if attacking_team == self.home_team else "away",
                            f"Goal! {scorer.name} scores!"
                        ))
            
            # Switch possession with 60% probability
            if random.random() < 0.6:
                self.current_possession = "away" if self.current_possession == "home" else "home"
                
        elif action == "midfield":
            # Midfield battle
            if self._calculate_action_success(attacking_team, defending_team, "pass"):
                # Successful buildup
                if self._calculate_action_success(attacking_team, defending_team, "dribble"):
                    # Created advantage
                    pass
                else:
                    # Lost possession
                    self.current_possession = "away" if self.current_possession == "home" else "home"
            else:
                # Lost possession
                self.current_possession = "away" if self.current_possession == "home" else "home"
        
        # Update possession stats
        if self.current_possession == "home":
            self.possession[0] += 1
        else:
            self.possession[1] += 1
        
        # Update player fatigue and development
        for team in [self.home_team, self.away_team]:
            for player in team.players:
                # Calculate match intensity impact
                fatigue = random.uniform(0.1, 0.3) * self.intensity
                player.stats["fitness"] = max(0, player.stats["fitness"] - fatigue)
                
                # Development from match experience
                if player in self.home_lineup or player in self.away_lineup:
                    player.stats["appearances"] += 1
                    
                    # Calculate development chance based on age
                    development_chance = 0.15 if player.age < 21 else \
                                       0.10 if player.age < 23 else \
                                       0.05 if player.age < 27 else \
                                       0.02  # Very small chance for older players
                    
                    # Development bonus decreases with age
                    development_bonus = 1.2 if player.age < 21 else \
                                      1.0 if player.age < 23 else \
                                      0.8 if player.age < 27 else \
                                      0.5
                    
                    # Apply development based on match experience
                    if random.random() < development_chance:
                        # Choose random attribute category to improve
                        category = random.choice(list(player.attributes.keys()))
                        for attr in player.attributes[category]:
                            # Smaller base improvement values
                            improvement = random.uniform(0.01, 0.05) * development_bonus * (player.potential / 100)
                            current_value = player.attributes[category][attr]
                            
                            # Harder to improve as rating gets higher
                            if current_value > 80:
                                improvement *= 0.5
                            elif current_value > 90:
                                improvement *= 0.25
                            
                            # Apply improvement with cap
                            player.attributes[category][attr] = min(95.0, current_value + improvement)
                            
                            if improvement > 0.2:  # Only show significant improvements
                                self.events.append(MatchEvent(
                                    self.minute,
                                    "development",
                                    player.name,
                                    "home" if team == self.home_team else "away",
                                    f"{player.name} shows improvement in {attr}"
                                ))
                
                # Fatigue events
                if player.stats["fitness"] < 20 and random.random() < 0.3:
                    self.events.append(MatchEvent(
                        self.minute,
                        "fatigue",
                        player.name,
                        "home" if team == self.home_team else "away",
                        f"{player.name} is showing signs of fatigue"
                    ))
        
        self.minute += 1
    
    def play_match(self):
        """
        Simulate the entire match.
        
        Returns:
            dict: Match statistics and events
        """
        #print(f"\nMatch: {self.home_team.name} vs {self.away_team.name}")
        
        # Select lineups using Q-learning managers
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

        # Validate and adjust lineups if needed
        self.home_lineup, self.home_positions = self._validate_lineup(self.home_lineup, self.home_positions, self.home_team)
        self.away_lineup, self.away_positions = self._validate_lineup(self.away_lineup, self.away_positions, self.away_team)
        
        # Simulate match
        for _ in range(90):  # 90 minutes
            self.simulate_minute()
            
            # Print significant events in debug mode
            if self.events and self.events[-1].minute == self.minute:
                event = self.events[-1]
                if hasattr(self.home_team.manager, '_debug') and self.home_team.manager._debug:
                    if event.type == "goal":
                        print(f"\n{event.minute}' - GOAL! {self.home_team.name} {self.score[0]}-{self.score[1]} {self.away_team.name}")
                    elif event.type == "fatigue" and event.minute % 15 == 0:
                        print(f"\n{event.minute}' - {event.details}")
            
            # Print match updates every 15 minutes in debug mode
            if self.minute % 15 == 0 and hasattr(self.home_team.manager, '_debug') and self.home_team.manager._debug:
                print(f"\n{self.minute}' Match Update:")
                print(f"{self.home_team.name} {self.score[0]}-{self.score[1]} {self.away_team.name}")
                print(f"Possession: {self.possession[0]/self.minute*100:.1f}% - {self.possession[1]/self.minute*100:.1f}%")
                print(f"Shots (On Target): {self.shots[0]} ({self.shots_on_target[0]}) - {self.shots[1]} ({self.shots_on_target[1]})")
        
        # Match summary
        summary = {
            "score": self.score,
            "possession": [p/90*100 for p in self.possession],  # Convert to percentage
            "shots": self.shots,
            "shots_on_target": self.shots_on_target,
            "weather": self.weather,
            "events": self.events
        }
        
        #print("\nFull Time Summary:")
        ##print(f"Score: {self.home_team.name} {self.score[0]} - {self.score[1]} {self.away_team.name}")
        #print(f"Possession: {summary['possession'][0]:.1f}% - {summary['possession'][1]:.1f}%")
        #print(f"Shots (On Target): {self.shots[0]} ({self.shots_on_target[0]}) - {self.shots[1]} ({self.shots_on_target[1]})")
        
        # Provide detailed feedback to managers for learning
        if self.home_team.manager:
            home_result = {
                "winner": self.score[0] > self.score[1],
                "draw": self.score[0] == self.score[1],
                "goals_for": self.score[0],
                "goals_against": self.score[1],
                "possession": self.possession[0],
                "shots": self.shots[0],
                "shots_on_target": self.shots_on_target[0],
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
                "youth_minutes": self._calculate_youth_minutes(self.away_lineup),
                "player_development": self._calculate_player_development(self.away_lineup),
                "tactical_success": self._calculate_tactical_success(self.away_team, self.home_team),
                "formation_effectiveness": self._calculate_formation_effectiveness(self.away_team)
            }
            self.away_team.manager.learn_from_match(away_result)
        
        # Reset player fitness by 50% after match
        for team in [self.home_team, self.away_team]:
            for player in team.players:
                player.stats["fitness"] = min(100, player.stats["fitness"] + 50)
        
        return summary

    def _calculate_youth_minutes(self, lineup: List[Any]) -> float:
        """Calculate total minutes played by youth players (under 23)."""
        youth_minutes = 0
        for player in lineup:
            if player.age < 23:
                youth_minutes += 90  # Assume full match for simplicity
        return youth_minutes

    def _calculate_player_development(self, lineup: List[Any]) -> float:
        """Calculate average development potential for squad."""
        if not lineup:
            return 0.0
        
        total_potential = 0
        for player in lineup:
            current = sum(sum(cat.values()) for cat in player.attributes.values()) / \
                     (len(player.attributes) * len(next(iter(player.attributes.values()))))
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
        return (offensive_success + defensive_success + pressure_success) / 6  # Normalized to 0-1

    def _calculate_formation_effectiveness(self, team: Any) -> float:
        """Calculate how well the formation worked with available players."""
        if not team.manager:
            return 0.5
            
        formation = team.manager.formation
        lineup = self.home_lineup if team == self.home_team else self.away_lineup
        positions = self.home_positions if team == self.home_team else self.away_positions
        
        # Calculate average position suitability
        total_suitability = 0
        for player, position in zip(lineup, positions):
            suitability = self._calculate_position_penalty(player, position)
            total_suitability += suitability
            
        return total_suitability / len(lineup) if lineup else 0

    def _select_default_lineup(self, team: Any) -> Tuple[List[Any], List[str]]:
        """Select a default lineup when no manager is present."""
        goalkeepers = [p for p in team.players if p.position == "GK"]
        defenders = [p for p in team.players if p.position in ["CB", "LB", "RB", "SW", "LWB", "RWB"]]
        midfielders = [p for p in team.players if p.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]]
        forwards = [p for p in team.players if p.position in ["ST", "CF", "SS", "LW", "RW"]]
        
        lineup = []
        positions = []
        
        # Default 4-4-2 formation
        if goalkeepers:
            lineup.append(goalkeepers[0])
            positions.append("GK")
        
        # Add 4 defenders
        lineup.extend(defenders[:4])
        positions.extend(["CB", "CB", "LB", "RB"][:len(defenders[:4])])
        
        # Add 4 midfielders
        lineup.extend(midfielders[:4])
        positions.extend(["CM", "CM", "LM", "RM"][:len(midfielders[:4])])
        
        # Add 2 forwards
        lineup.extend(forwards[:2])
        positions.extend(["ST", "ST"][:len(forwards[:2])])
        
        return lineup[:11], positions[:11]

    def _validate_lineup(self, lineup: List[Any], positions: List[str], team: Any) -> Tuple[List[Any], List[str]]:
        """Ensure lineup meets minimum requirements."""
        # Must have at least 1 goalkeeper
        gk_count = sum(1 for pos in positions if pos == "GK")
        if gk_count < 1:
            goalkeepers = [p for p in team.players if p.position == "GK"]
            if goalkeepers:
                lineup.insert(0, goalkeepers[0])
                positions.insert(0, "GK")
                
        # Ensure exactly 11 players
        if len(lineup) > 11:
            lineup = lineup[:11]
            positions = positions[:11]
        elif len(lineup) < 7:  # Absolute minimum players
            raise ValueError("Insufficient players to form lineup")
            
        return lineup, positions