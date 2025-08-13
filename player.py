import random
import names  # Requires: pip install names
from player_db import create_player, get_player, update_player, delete_player

import sqlite3

class FootballPlayer:
    
    def __init__(self, name, age, position, potential=70, wage=1000):
        """
        Initialize a football player with basic attributes.
        
        Args:
            name (str): Player's name
            age (int): Player's age
            position (str): Player's position on the field
            potential (int): Player's overall potential, defaults to 70
            wage (float): Player's weekly wage, defaults to 1000
        """
        self.name = name
        self.age = age
        self.position = position
        self.team = None  # Team will be set separately
        self.potential = potential
        self.wage = wage
        self.contract_length = 3  # Years remaining
        self.form = [0.7] * 10  # Last 10 match ratings (0-1 scale)
        self.is_injured = False
        self.injury_type = None
        self.recovery_time = 0
        self.injury_history = []  # List of dicts: {"type": ..., "duration": ..., "start_age": ...}
        self.squad_role = "RESERVE"  # STARTER/BENCH/YOUTH

        # Transfer/contract negotiation attributes
        self.desired_wage = self.wage * random.uniform(1.05, 1.25)
        self.contract_offer = None
        self.negotiation_state = None  # e.g., "open", "accepted", "rejected"
        self.transfer_interest = False  # Willingness to move
        
        # Database attributes
        self.player_id = None  # Will be set when saved to database
        
        # Enhanced attributes structure
        self.attributes = {
            "pace": {"acceleration": 1, "sprint_speed": 1},
            "shooting": {"finishing": 1, "shot_power": 1, "long_shots": 1},
            "passing": {"vision": 1, "crossing": 1, "free_kick": 1},
            "dribbling": {"agility": 1, "balance": 1, "ball_control": 1},
            "defending": {"marking": 1, "standing_tackle": 1, "sliding_tackle": 1},
            "physical": {"strength": 1, "stamina": 1, "aggression": 1},
            "goalkeeping": {"diving": 1, "handling": 1, "reflexes": 1, "positioning": 1}
        }
        
        # Enhanced stats with cards
        self.stats = {
            "goals": 0,
            "assists": 0,
            "appearances": 0,
            "fitness": 100,
            "clean_sheets": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "minutes_played": 0,
            "fouls_committed": 0,
            "fouls_suffered": 0
        }
        
        # Contract and wage history
        self.contract_history = []
        self.peak_rating = None  # Track peak performance for decline curve
        
    def _generate_unique_name(self):
        """Generate a unique player name not present in the database."""
        db_file = "football_sim.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        while True:
            candidate = names.get_full_name()
            cursor.execute("SELECT 1 FROM Player WHERE name = ?", (candidate,))
            if not cursor.fetchone():
                conn.close()
                return candidate

    def save_to_database(self, team_id=None):
        """Save player to database and return player_id, ensuring unique name."""
        if self.player_id is None:
            # Ensure unique name before saving
            db_file = "football_sim.db"
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM Player WHERE name = ?", (self.name,))
            if cursor.fetchone():
                # Name exists, generate a new one
                self.name = self._generate_unique_name()
            conn.close()
            # Create new player
            self.player_id = create_player(
                name=self.name,
                age=self.age,
                position=self.position,
                team_id=team_id,
                potential=self.potential,
                wage=self.wage,
                contract_length=self.contract_length,
                squad_role=self.squad_role,
                attributes=self.attributes
            )
        else:
            # Update existing player
            update_player(
                player_id=self.player_id,
                name=self.name,
                age=self.age,
                position=self.position,
                team_id=team_id,
                potential=self.potential,
                wage=self.wage,
                contract_length=self.contract_length,
                squad_role=self.squad_role,
                attributes=self.attributes
            )
        return self.player_id
    
    @classmethod
    def load_from_database(cls, player_id):
        """Load player from database by ID"""
        data = get_player(player_id)
        if not data:
            return None
            
        player = cls(
            name=data["name"],
            age=data["age"],
            position=data["position"],
            potential=data["potential"],
            wage=data["wage"]
        )
        player.player_id = data["player_id"]
        player.contract_length = data["contract_length"]
        player.squad_role = data["squad_role"]
        player.attributes = data["attributes"]
        return player
    
    def apply_age_decline(self):
        """Apply realistic age decline curve (peak at 27-29, decline after 30)"""
        if self.age < 23:
            # Young players still developing
            development_factor = 1.02
        elif 23 <= self.age <= 27:
            # Peak years - maintain or slight improvement
            development_factor = 1.001
        elif 28 <= self.age <= 29:
            # Peak maintained
            development_factor = 1.0
        elif 30 <= self.age <= 32:
            # Gradual decline
            development_factor = 0.998
        elif 33 <= self.age <= 35:
            # Noticeable decline
            development_factor = 0.995
        else:
            # Significant decline after 35
            development_factor = 0.99
        
        # Track peak rating for comparison
        current_rating = self.get_overall_rating()
        if self.peak_rating is None or current_rating > self.peak_rating:
            self.peak_rating = current_rating
        
        # Apply decline to attributes based on age
        for attr_type in self.attributes:
            # Physical attributes decline faster
            if attr_type in ["pace", "physical"]:
                decline_factor = development_factor * 0.998 if self.age > 30 else development_factor
            else:
                decline_factor = development_factor
                
            for sub_attr in self.attributes[attr_type]:
                old_value = self.attributes[attr_type][sub_attr]
                new_value = max(1.0, old_value * decline_factor)
                self.attributes[attr_type][sub_attr] = new_value

        # Save changes to the database
        if self.player_id is not None:
            update_player(self.player_id, attributes=self.attributes)
    
    def get_overall_rating(self):
        """Calculate overall player rating"""
        total = sum(sum(cat.values()) for cat in self.attributes.values())
        count = sum(len(cat) for cat in self.attributes.values())
        return total / count if count > 0 else 50
    
    def update_form(self, match_rating):
        """Update player form with new match rating (0-1 scale)"""
        self.form = self.form[1:] + [max(0, min(1, match_rating))]
    
    def get_form_rating(self):
        """Get current form as average of last 10 matches"""
        return sum(self.form) / len(self.form) if self.form else 0.7
    
    def receive_card(self, card_type="yellow"):
        """Player receives a yellow or red card"""
        if card_type == "yellow":
            self.stats["yellow_cards"] += 1
            # Two yellows = red card
            if self.stats["yellow_cards"] >= 2:
                self.stats["red_cards"] += 1
                return "red"  # Sent off
        elif card_type == "red":
            self.stats["red_cards"] += 1
            if self.player_id is not None:
                update_player(self.player_id, stats=self.stats)
            return "red"  # Sent off

        if self.player_id is not None:
            update_player(self.player_id, stats=self.stats)
        return card_type
    
    def get_suspension_games(self):
        """Calculate suspension based on cards"""
        # Simple suspension system
        if self.stats["red_cards"] > 0:
            return min(3, self.stats["red_cards"])  # 1-3 game suspension
        elif self.stats["yellow_cards"] >= 5:
            return 1  # 1 game suspension for 5 yellows
        return 0
    
    def apply_injury(self, injury_type="minor", severity_modifier=1.0):
        """Apply injury to player"""
        if self.is_injured:
            return  # Already injured
            
        # Injury duration based on type and severity
        injury_durations = {
            "minor": (1, 7),      # 1-7 days
            "moderate": (8, 21),   # 1-3 weeks  
            "major": (22, 60),     # 3-8 weeks
            "severe": (61, 120)    # 2-4 months
        }
        
        min_days, max_days = injury_durations.get(injury_type, (1, 7))
        duration = random.randint(min_days, max_days)
        duration = int(duration * severity_modifier)
        
        self.is_injured = True
        self.injury_type = injury_type
        self.recovery_time = duration
        
        # Add to injury history
        self.injury_history.append({
            "type": injury_type,
            "duration": duration,
            "start_age": self.age,
            "fitness_impact": min(20, duration * 0.5)
        })
        
        # Immediate fitness impact
        fitness_loss = min(30, duration * 2)
        self.stats["fitness"] = max(0, self.stats["fitness"] - fitness_loss)

        if self.player_id is not None:
            update_player(self.player_id, stats=self.stats)
    
    def recover_from_injury(self, days=1):
        """Process injury recovery"""
        if not self.is_injured:
            return
            
        self.recovery_time = max(0, self.recovery_time - days)
        
        if self.recovery_time <= 0:
            self.is_injured = False
            self.injury_type = None
            # Gradual fitness recovery
            self.stats["fitness"] = min(100, self.stats["fitness"] + 10)

        if self.player_id is not None:
            update_player(self.player_id, stats=self.stats)
    
    def is_available_for_selection(self):
        """Check if player is available for match selection"""
        return (not self.is_injured and 
                self.stats["fitness"] > 30 and 
                self.get_suspension_games() == 0)

    @classmethod
    def create_player(cls, name=None, age=None, position=None, potential=None):
        """
        Factory method to create a player with randomized attributes.
        
        Args:
            name (str, optional): Player's name, randomized if None
            age (int, optional): Player's age, randomized between 16-35 if None
            position (str, optional): Player's position on the field, randomized if None
            potential (int, optional): Player's potential, randomized if None
        
        Returns:
            A new FootballPlayer instance with randomized stats
        """
        # Generate random name if not provided
        if name is None:
            name = names.get_full_name()
            
        # Generate random age with realistic distribution if not provided
        if age is None:
            # Weighted: 15% (16-19), 40% (20-25), 30% (26-30), 15% (31-35)
            r = random.random()
            if r < 0.15:
                age = random.randint(16, 19)
            elif r < 0.55:
                age = random.randint(20, 25)
            elif r < 0.85:
                age = random.randint(26, 30)
            else:
                age = random.randint(31, 35)
            
        # Generate random position if not provided
        if position is None:
            positions = [
                "GK",  # Goalkeeper
                "CB", "LB", "RB", "LWB", "RWB", "SW",  # Defenders
                "CDM", "CM", "CAM", "LM", "RM", "DM",  # Midfielders
                "LW", "RW", "CF", "ST", "SS"  # Forwards
            ]
            position = random.choice(positions)
            
        # Generate random potential based on age
        if potential is None:
            if age < 21:
                potential = random.randint(60, 95)  # Young players higher potential
            elif age < 25:
                potential = random.randint(55, 90)
            elif age < 30:
                potential = random.randint(50, 85)
            else:
                potential = random.randint(45, 80)  # Older players lower potential
        
        # Calculate base wage based on potential and age
        base_wage = 500 + (potential * 50)  # Higher potential = higher wage
        
        # Age modifier: peak years get premium wages
        if 25 <= age <= 29:
            age_modifier = 1.3  # Peak years premium
        elif age < 23:
            age_modifier = 0.8  # Young players lower wages
        elif age > 32:
            age_modifier = 0.9  # Older players slight discount
        else:
            age_modifier = 1.0
        
        # Create the player with calculated wage
        player = cls(name, age, position, potential, wage=base_wage * age_modifier)
        
        # Set attribute ranges based on position
        position_boosts = {
            "GK": {"goalkeeping": (40, 85)},
            "DEF": {"defending": (30, 80), "physical": (35, 85)},
            "MID": {"passing": (30, 85), "dribbling": (25, 80)},
            "FWD": {"shooting": (30, 85), "pace": (30, 85)}
        }
        
        # Position category mapping
        position_category = "MID"  # Default
        if position.upper() in ["GK", "GOALKEEPER"]:
            position_category = "GK"
        elif position.upper() in ("CB", "LB", "RB", "LWB", "RWB", "SW", "DEFENDER"):
            position_category = "DEF"
        elif position.upper() in ["ST", "CF", "LW", "RW", "SS", "STRIKER", "FORWARD"]:
            position_category = "FWD"
        
        # Scale attribute generation based on potential and age
        potential_factor = player.potential / 99.0
        
        # Age factor for current ability vs potential
        if age < 21:
            ability_factor = 0.6  # Young players far from potential
        elif age < 25:
            ability_factor = 0.8  # Developing players
        elif age < 30:
            ability_factor = 0.95  # Peak players near potential
        else:
            ability_factor = 0.9  # Experienced but potentially declining
        
        # Generate random attributes based on position
        for attr_type in player.attributes:
            # Determine the base range
            if attr_type in position_boosts.get(position_category, {}):
                min_val, max_val = position_boosts[position_category][attr_type]
            else:
                min_val, max_val = 30, 65  # Default range for non-specialized attributes
            
            # Set each sub-attribute
            for sub_attr in player.attributes[attr_type]:
                # Add some randomness within the range, scaled by potential and age
                base_value = random.randint(min_val, max_val)
                variation = random.randint(-8, 8)
                
                # Apply potential and age factors
                final_value = (base_value + variation) * potential_factor * ability_factor
                final_value = min(95, max(10, final_value))
                player.attributes[attr_type][sub_attr] = round(final_value, 1)
        
        return player

    def train_player(self, intensity, focus_area=None, training_days=1, coach_bonus=0):
        """
        Improved training system with realistic, slower development.
        
        Args:
            intensity (str): 'low', 'medium', or 'high'
            focus_area (str): Specific attribute to focus training on
            training_days (int): Number of days to train
            coach_bonus (float): Coach effectiveness bonus (0-1)
        
        Returns:
            dict: Summary of training results
        """
        results = {
            "initial_attributes": {k: {sk: v for sk, v in sv.items()} for k, sv in self.attributes.items()},
            "training_days": training_days,
            "focused_area": focus_area,
            "fitness_impact": 0,
            "improvements": []
        }
        
        # Much more realistic improvement rates
        if intensity == "low":
            improvement = 0.02 + (coach_bonus * 0.01)
            fitness_cost = max(0.3, 1.0 - coach_bonus * 0.2)
        elif intensity == "medium":
            improvement = 0.04 + (coach_bonus * 0.02)
            fitness_cost = max(0.8, 2.0 - coach_bonus * 0.3)
        elif intensity == "high":
            improvement = 0.06 + (coach_bonus * 0.03)
            fitness_cost = max(1.5, 3.5 - coach_bonus * 0.5)
        else:
            return None
        
        # Age affects training effectiveness
        age_factor = 1.0
        if self.age < 21:
            age_factor = 1.4  # Young players develop faster
        elif self.age < 25:
            age_factor = 1.2
        elif self.age < 30:
            age_factor = 1.0
        elif self.age < 33:
            age_factor = 0.7  # Older players develop slower
        else:
            age_factor = 0.4
        
        # Apply training over multiple days
        for day in range(training_days):
            # Skip training if player is too tired or injured
            if self.stats["fitness"] < 20 or self.is_injured:
                break
            
            # Apply focused improvement if specified
            if focus_area and focus_area in self.attributes:
                for attribute in self.attributes[focus_area]:
                    current_val = self.attributes[focus_area][attribute]
                    
                    # Harder to improve higher ratings
                    difficulty_factor = 1.0
                    if current_val > 80:
                        difficulty_factor = 0.5
                    elif current_val > 90:
                        difficulty_factor = 0.2
                    
                    # Calculate improvement
                    actual_improvement = improvement * 2 * age_factor * difficulty_factor
                    
                    # Don't exceed potential
                    potential_limit = min(self.potential, 95)
                    if current_val + actual_improvement > potential_limit:
                        actual_improvement = max(0, potential_limit - current_val)
                    
                    if actual_improvement > 0:
                        self.attributes[focus_area][attribute] += actual_improvement
                        results["improvements"].append({
                            "attribute": f"{focus_area}.{attribute}",
                            "improvement": actual_improvement
                        })
            
            # Apply small improvement to all attributes
            for attr_type in self.attributes:
                weight = 0.5 if attr_type != focus_area else 0.2  # Reduced general improvement
                for sub_attr in self.attributes[attr_type]:
                    current_val = self.attributes[attr_type][sub_attr]
                    
                    # Difficulty factor
                    difficulty_factor = 1.0
                    if current_val > 80:
                        difficulty_factor = 0.3
                    elif current_val > 90:
                        difficulty_factor = 0.1
                    
                    # Base improvement with age and potential influence
                    base_improvement = improvement * weight * age_factor * difficulty_factor
                    potential_factor = self.potential / 100.0
                    
                    actual_improvement = base_improvement * potential_factor
                    
                    # Random chance for bonus improvement
                    if random.random() < 0.02 * (1 + coach_bonus):
                        bonus = random.uniform(0.005, 0.015) * age_factor
                        actual_improvement += bonus
                    
                    # Don't exceed potential
                    potential_limit = min(self.potential, 95)
                    if current_val + actual_improvement > potential_limit:
                        actual_improvement = max(0, potential_limit - current_val)
                    
                    if actual_improvement > 0.01:  # Only apply meaningful improvements
                        self.attributes[attr_type][sub_attr] += actual_improvement
            
            # Update fitness with age factor
            age_fitness_factor = 1.0 if self.age < 30 else 1.3  # Older players tire faster
            fitness_loss = fitness_cost * age_fitness_factor
            self.stats["fitness"] = max(0, self.stats["fitness"] - fitness_loss)
            results["fitness_impact"] += fitness_loss
        
        # Ensure fitness is within bounds
        self.stats["fitness"] = max(0, min(100, self.stats["fitness"]))
        
        # Complete results
        results["final_attributes"] = {k: {sk: v for sk, v in sv.items()} for k, sv in self.attributes.items()}
        
        # Save changes to the database
        if self.player_id is not None:
            update_player(self.player_id, attributes=self.attributes, stats=self.stats)

        return results

    def get_player_info(self, detail_level="basic"):
        """
        Returns player information with adjustable detail level.
        
        Args:
            detail_level (str): 'basic', 'stats', or 'full' for different levels of detail
        
        Returns:
            dict: Player's attributes and stats based on requested detail level
        """
        basic_info = {
            "name": self.name,
            "age": self.age,
            "position": self.position,
            "team": self.team,
            "potential": self.potential,
            "wage": self.wage,
            "contract_length": self.contract_length,
            "squad_role": self.squad_role,
            "overall_rating": self.get_overall_rating(),
            "is_injured": self.is_injured,
            "injury_type": self.injury_type,
            "recovery_time": self.recovery_time,
            "available": self.is_available_for_selection()
        }
        
        if detail_level == "basic":
            return basic_info
            
        elif detail_level == "stats":
            return {**basic_info, "stats": self.stats, "form": self.get_form_rating()}
            
        elif detail_level == "full":
            return {
                **basic_info,
                "stats": self.stats,
                "attributes": self.attributes,
                "form": self.form,
                "injury_history": self.injury_history,
                "peak_rating": self.peak_rating
            }
        
        else:
            print("Invalid detail level. Using 'basic'")
            return basic_info

if __name__ == "__main__":
    player = FootballPlayer.create_player()
    print(player.get_player_info(detail_level="full"))
    player.train_player('high', focus_area=None, training_days=7, coach_bonus=0)
    print("+=" * 40)
    print(player.get_player_info(detail_level="full"))
