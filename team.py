from player import FootballPlayer
from manager import Manager
class Team:
    def __init__(self, name, budget):
        """
        Initialize a team with basic attributes.
        
        Args:
            name (str): Team name
            budget (float): Team's total budget for the season
        """
        self.name = name
        self.budget = budget
        self.weekly_budget = budget / 52  # Weekly budget based on annual budget
        self.transfer_budget = budget * 0.4  # 40% of budget for transfers
        self.wage_budget = budget * 0.6  # 60% of budget for wages
        self.players = []
        self.manager = None
        self.coaches = []  # Maximum 5 coaches
        self.statistics = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "transfer_history": []  # Track transfers
        }
    
    def add_player(self, player):
        """Add a player to the team."""
        if len(self.players) >= 23:
            raise ValueError("Squad size cannot exceed 23 players")
        self.players.append(player)
        player.team = self.name
    
    def remove_player(self, player):
        """Remove a player from the team."""
        if player in self.players:
            self.players.remove(player)
            player.team = None
    
    def set_manager(self, manager):
        """Assign a manager to the team."""
        self.manager = manager
        manager.team = self
    
    def add_coach(self, coach):
        """Add a coach to the team."""
        if len(self.coaches) >= 5:
            raise ValueError("Team cannot have more than 5 coaches")
        self.coaches.append(coach)
        coach.team = self
    
    def remove_coach(self, coach):
        """Remove a coach from the team."""
        if coach in self.coaches:
            self.coaches.remove(coach)
            coach.team = None
    
    def get_formation(self):
        """Get team formation from manager."""
        return self.manager.formation if self.manager else "4-4-2"
    
    def get_tactics(self):
        """Get team tactics from manager."""
        return self.manager.tactics if self.manager else {
            "offensive": 50,
            "defensive": 50,
            "pressure": 50
        }
    
    def get_squad_strength(self):
        """Calculate overall team strength based on player attributes."""
        if not self.players:
            return 0
        
        total_rating = 0
        for player in self.players:
            # Calculate average of key attributes based on position
            if player.position == "GK":
                rating = sum(player.attributes["goalkeeping"].values()) / len(player.attributes["goalkeeping"])
            elif player.position in ["CB", "LB", "RB"]:
                rating = sum(player.attributes["defending"].values()) / len(player.attributes["defending"])
            elif player.position in ["CM", "CDM"]:
                rating = (sum(player.attributes["passing"].values()) + sum(player.attributes["physical"].values())) / (
                    len(player.attributes["passing"]) + len(player.attributes["physical"]))
            else:  # Attacking players
                rating = (sum(player.attributes["shooting"].values()) + sum(player.attributes["pace"].values())) / (
                    len(player.attributes["shooting"]) + len(player.attributes["pace"]))
            total_rating += rating
        
        return round(total_rating / len(self.players), 2)
    
    def handle_transfer(self, player, fee, is_selling=True):
        """
        Process a transfer transaction (buying or selling a player).
        
        Args:
            player: Player being transferred
            fee: Transfer fee
            is_selling: True if selling, False if buying
            
        Returns:
            bool: Whether transfer was successful
        """
        if is_selling:
            if player in self.players:
                self.players.remove(player)
                self.budget += fee
                self.transfer_budget += fee * 0.4  # 40% of fee goes to transfer budget
                self.wage_budget += fee * 0.6  # 60% of fee goes to wage budget
                
                self.statistics["transfer_history"].append({
                    "type": "sale",
                    "player": player.name,
                    "fee": fee,
                    "position": player.position
                })
                return True
            return False
        else:
            if fee <= self.transfer_budget:
                self.players.append(player)
                self.budget -= fee
                self.transfer_budget -= fee
                
                self.statistics["transfer_history"].append({
                    "type": "purchase",
                    "player": player.name,
                    "fee": fee,
                    "position": player.position
                })
                return True
            return False
    
    def can_afford_transfer(self, fee, include_wages=True):
        """Check if team can afford a transfer fee and wages."""
        if fee > self.transfer_budget:
            return False
        if include_wages:
            estimated_weekly_wage = fee * 0.02 / 52  # Estimate 2% of transfer fee as annual salary
            if estimated_weekly_wage > self.wage_budget / len(self.players):
                return False
        return True
    
    def get_transfer_budget_info(self):
        """Get detailed information about team's transfer capabilities."""
        return {
            "total_budget": self.budget,
            "transfer_budget": self.transfer_budget,
            "wage_budget": self.wage_budget,
            "squad_size": len(self.players),
            "average_squad_age": sum(p.age for p in self.players) / len(self.players) if self.players else 0,
            "recent_transfers": self.statistics["transfer_history"][-5:],
            "can_buy_players": len(self.players) < 25,  # Maximum squad size
            "needs_players": len(self.players) < 18  # Minimum recommended squad size
        }
    
    def get_squad_needs(self):
        """Analyze squad and determine positions that need strengthening."""
        position_counts = {
            "GK": 0, "DEF": 0, "MID": 0, "FWD": 0
        }
        
        for player in self.players:
            if player.position == "GK":
                position_counts["GK"] += 1
            elif player.position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]:
                position_counts["DEF"] += 1
            elif player.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]:
                position_counts["MID"] += 1
            else:
                position_counts["FWD"] += 1
        
        needs = []
        if position_counts["GK"] < 2:
            needs.append(("GK", "Critical"))
        if position_counts["DEF"] < 6:
            needs.append(("DEF", "High" if position_counts["DEF"] < 4 else "Medium"))
        if position_counts["MID"] < 6:
            needs.append(("MID", "High" if position_counts["MID"] < 4 else "Medium"))
        if position_counts["FWD"] < 4:
            needs.append(("FWD", "High" if position_counts["FWD"] < 2 else "Medium"))
        
        return {
            "current_distribution": position_counts,
            "needs": needs,
            "squad_balance": "Good" if min(position_counts.values()) >= 2 else "Needs Improvement"
        }
    
    def calculate_weekly_expenses(self):
        """Calculate total weekly expenses including staff and player wages."""
        total_expenses = 0
        
        # Manager salary (assumed to be 10% of weekly budget)
        if self.manager:
            total_expenses += self.weekly_budget * 0.10
        
        # Coach salaries (assumed to be 5% of weekly budget each)
        total_expenses += len(self.coaches) * (self.weekly_budget * 0.05)
        
        # Player wages (assumed to be remaining budget divided equally)
        remaining_budget = self.weekly_budget - total_expenses
        player_budget = remaining_budget * 0.8  # 80% of remaining budget for players
        
        return {
            "total": round(total_expenses + player_budget, 2),
            "breakdown": {
                "manager": round(self.weekly_budget * 0.10 if self.manager else 0, 2),
                "coaches": round(len(self.coaches) * (self.weekly_budget * 0.05), 2),
                "players": round(player_budget, 2)
            }
        }