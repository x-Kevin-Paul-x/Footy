import random
import numpy as np
import names
from coach_db import create_coach, update_coach

from collections import defaultdict

class Coach:
    def __init__(self, name=None, specialty=None, experience_level=None):
        """
        Initialize a coach with specialization and learning capabilities.
        
        Args:
            name (str): Coach's name
            specialty (str): Specialization area (e.g., "Attack", "Defense", "Fitness", "Goalkeeping", "Youth")
            experience_level (int): Initial experience level (1-10)
        """
        specialties = ["Attack", "Defense", "Fitness", "Goalkeeping", "Youth"]
        self.name = names.get_full_name() if not name else name
        self.specialty = random.choice(specialties) if not specialty else specialty
        self.experience_level = min(10, max(1, random.randint(1, 10) if not experience_level else experience_level))
        self.team = None
        
        # Learning parameters
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        self.improvement_history = defaultdict(list)
        self.training_effectiveness = defaultdict(float)
        
        # Initialize training methods with weights
        self.training_methods = {
            "Attack": {
                "Shooting Drills": 1.0,
                "Movement Practice": 1.0,
                "Set Pieces": 1.0,
                "Counter-Attack": 1.0,
                "Ball Control": 1.0
            },
            "Defense": {
                "Marking": 1.0,
                "Positioning": 1.0,
                "Tackling": 1.0,
                "Zonal Defense": 1.0,
                "Aerial Duels": 1.0
            },
            "Fitness": {
                "Endurance": 1.0,
                "Speed": 1.0,
                "Strength": 1.0,
                "Agility": 1.0,
                "Recovery": 1.0
            },
            "Goalkeeping": {
                "Shot Stopping": 1.0,
                "Cross Collection": 1.0,
                "Footwork": 1.0,
                "Distribution": 1.0,
                "Positioning": 1.0
            },
            "Youth": {
                "Technical Skills": 1.0,
                "Tactical Understanding": 1.0,
                "Physical Development": 1.0,
                "Mental Training": 1.0,
                "Game Intelligence": 1.0
            }
        }
        
        # Performance tracking
        self.session_results = []
        self.player_progress = defaultdict(lambda: defaultdict(list))
        self.coach_id = None
    
    def select_training_method(self):
        """
        Select training method using reinforcement learning approach.
        
        Returns:
            str: Selected training method
        """
        if self.specialty not in self.training_methods:
            return None
            
        methods = self.training_methods[self.specialty]
        
        if random.random() < self.exploration_rate:
            # Exploration: try random method
            return random.choice(list(methods.keys()))
        else:
            # Exploitation: choose best performing method
            return max(methods.items(), key=lambda x: x[1])[0]
    
    def conduct_training_session(self, players, focus_attribute):
        """
        Conduct a training session and update learning parameters.
        
        Args:
            players (list): List of players participating in training
            focus_attribute (str): Specific attribute to focus on
        
        Returns:
            dict: Training session results
        """
        method = self.select_training_method()
        if not method:
            return {"error": "Invalid specialty"}
            
        results = {
            "method": method,
            "improvements": defaultdict(float),
            "experience_gained": 0
        }
        
        for player in players:
            # Calculate base improvement chance
            improvement_chance = (
                self.experience_level * 0.1 +  # Coach experience factor
                random.random() * 0.2  # Random factor
            )
            
            # Apply improvement if successful
            if random.random() < improvement_chance:
                improvement = random.uniform(0.1, 0.5)
                
                # Track improvement for learning
                self.player_progress[player.name][focus_attribute].append(improvement)
                results["improvements"][player.name] = improvement
                
                # Update player attributes based on specialty
                if self.specialty == "Attack" and "shooting" in player.attributes:
                    player.attributes["shooting"][focus_attribute] = min(
                        99, player.attributes["shooting"][focus_attribute] + improvement
                    )
                # Add similar updates for other specialties
        
        # Update training method weights based on results
        avg_improvement = np.mean(list(results["improvements"].values())) if results["improvements"] else 0
        self.training_methods[self.specialty][method] += self.learning_rate * avg_improvement
        
        # Store session results
        self.session_results.append({
            "method": method,
            "average_improvement": avg_improvement,
            "players_improved": len(results["improvements"])
        })
        
        self.save_to_database()
        return results
    
    def adapt_training_approach(self):
        """
        Adapt training approach based on recent results.
        """
        if len(self.session_results) < 5:
            return
            
        recent_sessions = self.session_results[-5:]
        avg_improvement = np.mean([s["average_improvement"] for s in recent_sessions])
        
        # Adjust exploration rate based on performance
        if avg_improvement < 0.2:
            self.exploration_rate = min(0.5, self.exploration_rate + 0.05)  # Explore more
        elif avg_improvement > 0.4:
            self.exploration_rate = max(0.1, self.exploration_rate - 0.05)  # Exploit more
        
        # Adjust learning rate based on experience
        self.learning_rate = max(0.05, min(0.2, self.learning_rate * (1 + avg_improvement)))
        self.save_to_database()
    
    def save_to_database(self):
        """Save coach to database and return coach_id"""
        if self.coach_id is None:
            # Create new coach
            self.coach_id = create_coach(
                name=self.name,
                specialty=self.specialty,
                experience_level=self.experience_level,
                team_id=self.team.team_id if self.team else None,
                learning_rate=self.learning_rate,
                exploration_rate=self.exploration_rate,
                improvement_history=dict(self.improvement_history),
                training_effectiveness=dict(self.training_effectiveness),
                training_methods=self.training_methods,
                session_results=self.session_results,
                player_progress={k: dict(v) for k, v in self.player_progress.items()}
            )
        else:
            # Update existing coach
            update_coach(
                coach_id=self.coach_id,
                name=self.name,
                specialty=self.specialty,
                experience_level=self.experience_level,
                team_id=self.team.team_id if self.team else None,
                learning_rate=self.learning_rate,
                exploration_rate=self.exploration_rate,
                improvement_history=dict(self.improvement_history),
                training_effectiveness=dict(self.training_effectiveness),
                training_methods=self.training_methods,
                session_results=self.session_results,
                player_progress={k: dict(v) for k, v in self.player_progress.items()}
            )
        return self.coach_id

    def analyze_progress(self, timeframe=10):
        """
        Analyze training effectiveness over recent sessions.
        
        Args:
            timeframe (int): Number of recent sessions to analyze
            
        Returns:
            dict: Analysis results
        """
        if not self.session_results:
            return {"status": "No training sessions recorded"}
            
        recent = self.session_results[-timeframe:]
        
        analysis = {
            "average_improvement": np.mean([s["average_improvement"] for s in recent]),
            "most_effective_method": max(
                self.training_methods[self.specialty].items(),
                key=lambda x: x[1]
            )[0],
            "learning_rate": self.learning_rate,
            "exploration_rate": self.exploration_rate,
            "experience_level": self.experience_level
        }
        
        # Update experience based on performance
        if analysis["average_improvement"] > 0.3:
            self.experience_level = min(10, self.experience_level + 0.1)
        
        self.save_to_database()
        return analysis