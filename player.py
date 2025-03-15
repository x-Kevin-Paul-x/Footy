from os import name
import random
import names  # Requires: pip install names

class FootballPlayer:
    

    def __init__(self, name, age, position, potential=70):
        """
        Initialize a football player with basic attributes.
        
        Args:
            name (str): Player's name
            age (int): Player's age
            position (str): Player's position on the field
            potential (int): Player's overall potential, defaults to 70
        """
        self.name = name
        self.age = age
        self.position = position
        self.team = None  # Team will be set separately
        self.potential = potential
        self.stats = {
            "goals": 0,
            "assists": 0,
            "appearances": 0,
            "fitness": 100,
            "clean_sheets": 0,
            "yellow_cards": 0,
            "red_cards": 0
        }
        # Detailed football attributes
        self.attributes = {
            "pace": {
            "acceleration": 1, 
            "sprint_speed": 1
            },
            "shooting": {
            "finishing": 1,
            "shot_power": 1,
            "long_shots": 1
            },
            "passing": {
            "vision": 1,
            "crossing": 1,
            "free_kick": 1
            },
            "dribbling": {
            "agility": 1,
            "balance": 1,
            "ball_control": 1
            },
            "defending": {
            "marking": 1,
            "standing_tackle": 1,
            "sliding_tackle": 1
            },
            "physical": {
            "strength": 1,
            "stamina": 1,
            "aggression": 1
            },
            "goalkeeping": {
            "diving": 1,
            "handling": 1,
            "reflexes": 1,
            "positioning": 1
            }
        }

    @classmethod
    def create_player(cls, name=None, age=None, position=None):
        """
        Factory method to create a player with randomized attributes.
        
        Args:
            name (str, optional): Player's name, randomized if None
            age (int, optional): Player's age, randomized between 16-20 if None
            position (str, optional): Player's position on the field, randomized if None
        
        Returns:
            A new FootballPlayer instance with randomized stats
        """
        # Generate random name if not provided
        if name is None:
            name = names.get_full_name()
            
        # Generate random age between 16-20 if not provided
        if age is None:
            age = random.randint(16, 20)
            
        # Generate random position if not provided
        if position is None:
            positions = [
                "GK",  # Goalkeeper
                "CB", "LB", "RB", "LWB", "RWB", "SW",  # Defenders
                "CDM", "CM", "CAM", "LM", "RM", "DM",  # Midfielders
                "LW", "RW", "CF", "ST", "SS"  # Forwards
            ]
            position = random.choice(positions)
            
        # Generate random potential between 50-99
        potential = random.randint(50, 99)
        
        # Create the player
        player = cls(name, age, position, potential)
        
        # Set attribute ranges based on position
        position_boosts = {
            "GK": {"goalkeeping": (50, 90)},
            "DEF": {"defending": (60, 90), "physical": (55, 85)},
            "MID": {"passing": (60, 90), "dribbling": (55, 85)},
            "FWD": {"shooting": (60, 90), "pace": (60, 90)}
        }
        
        # Position category mapping
        position_category = "MID"  # Default
        if position.upper() in ["GK", "GOALKEEPER"]:
            position_category = "GK"
        elif position.upper() in ("CB", "LB", "RB", "LWB", "RWB", "SW", "DEFENDER"):
            position_category = "DEF"
        elif position.upper() in ["ST", "CF", "LW", "RW", "STRIKER", "FORWARD"]:
            position_category = "FWD"
        
        # Scale attribute generation based on potential
        potential_factor = player.potential / 99.0
        
        # Generate random attributes based on position
        for attr_type in player.attributes:
            # Determine the base range
            if attr_type in position_boosts.get(position_category, {}):
                min_val, max_val = position_boosts[position_category][attr_type]
            else:
                min_val, max_val = 40, 70  # Default range for non-specialized attributes
            
            # Set each sub-attribute
            for sub_attr in player.attributes[attr_type]:
                # Add some randomness within the range, scaled by potential
                base_value = random.randint(min_val, max_val)
                variation = random.randint(-5, 5)
                final_value = min(99, max(1, (base_value + variation) * potential_factor))
                player.attributes[attr_type][sub_attr] = round(final_value, 1)
        
        #print(f"Created new player: {name}, {age} years, {position}")
        #print(f"Potential: {player.potential}")
        return player

    def train_player(self, intensity, focus_area=None, training_days=1, coach_bonus=0):
        """
        Improve player's attributes based on training intensity and coach influence.
        
        Args:
            intensity (str): 'low', 'medium', or 'high'
            focus_area (str): Specific attribute to focus training on
            training_days (int): Number of days to train
        
        Returns:
            dict: Summary of training results
        """
        results = {
            "initial_attributes": {k: {sk: v for sk, v in sv.items()} for k, sv in self.attributes.items()},
            "training_days": training_days,
            "focused_area": focus_area,
            "fitness_impact": 0
        }
        
        # Set improvement and fitness cost based on intensity and coach influence
        if intensity == "low":
            improvement = 0.1 + (coach_bonus * 0.05)
            fitness_cost = max(1, 3 - coach_bonus)
        elif intensity == "medium":
            improvement = 0.2 + (coach_bonus * 0.08)
            fitness_cost = max(2, 5 - coach_bonus)
        elif intensity == "high":
            improvement = 0.3 + (coach_bonus * 0.1)
            fitness_cost = max(3, 7 - coach_bonus)
        else:
            print("Invalid intensity level. Use 'low', 'medium', or 'high'")
            return None
        
        # Apply training over multiple days
        for day in range(training_days):
            # Check if player has enough fitness
            if self.stats["fitness"] < fitness_cost:
                print(f"Training stopped: {self.name} is too tired to continue after {day} days")
                break
            
            # Apply focused improvement if specified
            if focus_area and focus_area in self.attributes:
                for attribute in self.attributes[focus_area]:
                    self.attributes[focus_area][attribute] += improvement * 2
            
            # Apply small improvement to all attributes
            for attr_type in self.attributes:
                weight = 2 if attr_type == focus_area else 0.5
                for sub_attr in self.attributes[attr_type]:
                    # Base improvement with coach and potential influence
                    base_improvement = improvement * weight * 1.5  # Increased multiplier
                    potential_factor = self.potential / 100.0
                    
                    # Apply improvement with potential scaling
                    self.attributes[attr_type][sub_attr] += base_improvement * (1 + potential_factor)
                    
                    # Random chance for bonus improvement based on potential
                    if random.random() < 0.15 * (1 + coach_bonus/10):
                        bonus = random.uniform(0.1, 0.3) * (1 + coach_bonus * 0.1)
                        self.attributes[attr_type][sub_attr] += bonus
                    
                    # Track initial ratings
                    initial_overall = sum(sum(cat.values()) for cat in self.attributes.values()) / \
                                   (len(self.attributes) * len(next(iter(self.attributes.values()))))
                    
                    # Potential progression system
                    if random.random() < 0.15 * (1 + coach_bonus/10):
                        potential_gain = random.uniform(0.1, 0.5) * (improvement * 2)
                        old_potential = self.potential
                        self.potential = min(99, self.potential + potential_gain)
                        
                        # Calculate final ratings after all improvements
                        final_overall = sum(sum(cat.values()) for cat in self.attributes.values()) / \
                                      (len(self.attributes) * len(next(iter(self.attributes.values()))))
                        
                        # Only show significant improvements
                        if final_overall - initial_overall > 0.5:
                            print(f"{self.name} improved from {initial_overall:.1f} to {final_overall:.1f} rating!")

                    # Cap at 95.0 and track development
                    old_value = self.attributes[attr_type][sub_attr]
                    new_value = min(95.0, self.attributes[attr_type][sub_attr])
                    self.attributes[attr_type][sub_attr] = new_value
                    
                    # Update development tracking
                    if "development" not in self.stats:
                        self.stats["development"] = []
                    if new_value > old_value:
                        self.stats["development"].append({
                            "attribute": f"{attr_type}.{sub_attr}",
                            "from": old_value,
                            "to": new_value,
                            "age": self.age
                        })
            
            # Update fitness with age factor
            age_factor = 1.0 if self.age < 30 else 1.2  # Older players tire faster
            self.stats["fitness"] -= fitness_cost * age_factor
            results["fitness_impact"] += fitness_cost * age_factor
        
        # Ensure fitness is within bounds
        self.stats["fitness"] = max(0, min(100, self.stats["fitness"]))
        
        # Complete results
        results["final_attributes"] = {k: {sk: v for sk, v in sv.items()} for k, sv in self.attributes.items()}
        
        # Calculate overall improvement
        initial_avg = sum(sum(results["initial_attributes"][cat].values()) for cat in results["initial_attributes"]) / \
                     (len(self.attributes) * len(next(iter(self.attributes.values()))))
        final_avg = sum(sum(results["final_attributes"][cat].values()) for cat in results["final_attributes"]) / \
                   (len(self.attributes) * len(next(iter(self.attributes.values()))))
        
        if final_avg - initial_avg > 0.5:  # Only show significant improvements
            print(f"{self.name} completed {training_days} days of {intensity} intensity training:")
            print(f"Overall Rating: {initial_avg:.1f} → {final_avg:.1f}")
            print(f"Fitness: {self.stats['fitness']:.1f}%")
            if focus_area:
                print(f"Focused on: {focus_area}")
        
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
            "potential": self.potential
        }
        
        if detail_level == "basic":
            return basic_info
            
        elif detail_level == "stats":
            return {**basic_info, "stats": self.stats}
            
        elif detail_level == "full":
            return {
            **basic_info,
            "stats": self.stats,
            "attributes": self.attributes
            }
        
        else:
            print("Invalid detail level. Using 'basic'")
            return basic_info
