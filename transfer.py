from dataclasses import dataclass
import os
from typing import List, Dict, Optional
import random
from datetime import datetime

from player import FootballPlayer
from team import Team

@dataclass
class TransferListing:
    player: 'FootballPlayer'
    asking_price: float
    selling_team: 'Team'
    listed_date: int  # Transfer window day
    expires_in: int = 30  # Days until listing expires

class TransferMarket:
    def __init__(self):
        self.transfer_list: List[TransferListing] = []
        self.current_day = 0
        self.transfer_history: List[Dict] = []
        self.season_year = datetime.now().year
        
        # Create transfer logs directory
        os.makedirs("transfer_logs", exist_ok=True)
        self.current_log = None
        self._init_transfer_log()
        
        # Value multipliers based on attributes and age
        self.value_modifiers = {
            "potential": 1.5,  # High potential increases value
            "age_discount": 0.95,  # Value decreases per year over 30
            "age_premium": 1.1,  # Value increases per year of prime (23-27)
            "position_premium": {
                "ST": 1.3, "CF": 1.3, "RW": 1.2, "LW": 1.2,  # Attackers premium
                "CAM": 1.2, "CM": 1.1, "CDM": 1.0,  # Midfielders standard
                "CB": 1.1, "LB": 1.0, "RB": 1.0,  # Defenders standard
                "GK": 1.15  # Goalkeeper slight premium
            }
        }
        
    def _init_transfer_log(self):
        """Initialize log file for current season"""
        log_path = f"transfer_logs/season_{self.season_year}_transfers.txt"
        self.current_log = open(log_path, "w", encoding="utf-8")
        self.current_log.write(f"Transfer Activity for Season {self.season_year}\n")
        self.current_log.write("=" * 80 + "\n\n")
        
    def _log_transfer_attempt(self, action: str, details: Dict):
        """Log transfer activity"""
        if not self.current_log:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_log.write(f"[{timestamp}] {action}\n")
        for key, value in details.items():
            self.current_log.write(f"  {key}: {value}\n")
        self.current_log.write("-" * 40 + "\n")
        self.current_log.flush()  # Ensure log is written immediately
        
    def _init_transfer_log(self):
        """Initialize log file for current season"""
        log_path = f"transfer_logs/season_{self.season_year}_transfers.txt"
        self.current_log = open(log_path, "w", encoding="utf-8")
        self.current_log.write(f"Transfer Activity for Season {self.season_year}\n")
        self.current_log.write("=" * 80 + "\n\n")
        
    def _log_transfer_attempt(self, action: str, details: Dict):
        """Log transfer activity"""
        if not self.current_log:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_log.write(f"[{timestamp}] {action}\n")
        for key, value in details.items():
            self.current_log.write(f"  {key}: {value}\n")
        self.current_log.write("-" * 40 + "\n")
        self.current_log.flush()  # Ensure log is written immediately

    
    def calculate_player_value(self, player) -> float:
        """Calculate a player's market value based on attributes, age, and position."""
        # Base value from attributes
        base_value = 0
        for category in player.attributes.values():
            base_value += sum(category.values())
        base_value = base_value * 10000  # Convert to currency
        
        # Age modifier
        if player.age > 30:
            age_discount = (player.age - 30) * self.value_modifiers["age_discount"]
            base_value *= (1 - age_discount)
        elif 23 <= player.age <= 27:
            age_premium = (27 - player.age) * self.value_modifiers["age_premium"]
            base_value *= (1 + age_premium)
        
        # Potential modifier
        potential_boost = (player.potential / 50) * self.value_modifiers["potential"]
        base_value *= potential_boost
        
        # Position modifier
        position_mod = self.value_modifiers["position_premium"].get(player.position, 1.0)
        base_value *= position_mod
        
        return round(base_value)
    
    def list_player(self, player, team, asking_price=None):
        """List a player on the transfer market."""
        if asking_price is None:
            # Set default asking price based on calculated value
            base_value = self.calculate_player_value(player)
            asking_price = base_value * random.uniform(1.1, 1.3)  # Add 10-30% markup
        
        listing = TransferListing(
            player=player,
            asking_price=asking_price,
            selling_team=team,
            listed_date=self.current_day
        )
        self.transfer_list.append(listing)
        return listing
    
    def get_available_players(self, max_price=None, position=None, max_age=None):
        """Get list of available players matching criteria."""
        available = []
        for listing in self.transfer_list:
            if max_price and listing.asking_price > max_price:
                continue
            if position and listing.player.position != position:
                continue
            if max_age and listing.player.age > max_age:
                continue
            available.append(listing)
            print(listing.player.name, listing.asking_price)
        return available
    
    def make_transfer_offer(self, buying_team, listing, offer_amount):
        """Attempt to buy a player from the transfer list."""
        if buying_team.budget < offer_amount:
            return False, "Insufficient funds"
        
        # Check if offer is acceptable
        min_acceptable = listing.asking_price * 0.8  # Will accept 20% below asking
        if offer_amount < min_acceptable:
            return False, "Offer too low"
        
        # Check if buying team can afford transfer
        if not buying_team.can_afford_transfer(offer_amount):
            return False, "Cannot afford transfer fee and wages"
            
        # Complete transfer
        transfer_success = listing.selling_team.handle_transfer(listing.player, offer_amount, is_selling=True)
        if not transfer_success:
            return False, "Selling team transfer failed"
            
        transfer_success = buying_team.handle_transfer(listing.player, offer_amount, is_selling=False)
        if not transfer_success:
            # Rollback selling team's transfer if buying fails
            listing.selling_team.handle_transfer(listing.player, offer_amount, is_selling=False)
            return False, "Buying team transfer failed"
        
        # Record transfer
        transfer_record = {
            "player": listing.player.name,
            "from_team": listing.selling_team.name,
            "to_team": buying_team.name,
            "amount": offer_amount,
            "day": self.current_day
        }
        self.transfer_history.append(transfer_record)
        
        # Remove listing
        self.transfer_list.remove(listing)
        
        return True, "Transfer completed successfully"
    
    def simulate_ai_transfers(self, all_teams):
        """Simulate AI teams making transfer decisions using Q-learning."""
        for team in all_teams:
            if not team.manager:
                continue
                
            # Get manager's decisions using Q-learning
            actions = team.manager.make_transfer_decision(self)
            # Process each action with feedback
            for action_type, *params in actions:
                if action_type == "list":
                    player, price = params
                    if len(team.players) > 18:  # Keep minimum squad size
                        listing = self.list_player(player, team, price)
                        if listing:
                            # Provide feedback for learning
                            result = {
                                "type": "list",
                                "player": player,
                                "price": price,
                                "value_ratio": price / self.calculate_player_value(player),
                                "need_satisfaction": 0.0,  # Listing doesn't satisfy needs
                                "month": (self.current_day % 30) + 1,
                                "market": self
                            }
                            team.manager.learn_from_transfer(result)
                            
                elif action_type == "buy":
                    listing, offer = params
                    if team.budget >= offer:
                        success, message = self.make_transfer_offer(team, listing, offer)
                        
                        # Always record attempt, success or failure
                        team.manager.transfer_attempts.append(success)
                        
                        # Provide feedback for learning
                        result = {
                            "type": "buy",
                            "player": listing.player,
                            "price": offer,
                            "value_ratio": self.calculate_player_value(listing.player) / offer,
                            "need_satisfaction": 1.0 if success else 0.0,
                            "age_impact": (27 - listing.player.age) / 27 if listing.player.age <= 27 else 0,
                            "month": (self.current_day % 30) + 1,
                            "market": self,
                            "success": success,
                            "reason": message
                        }
                        team.manager.learn_from_transfer(result)
    
    def advance_day(self):
        """Advance the transfer market by one day."""
        self.current_day += 1
        
        # Remove expired listings
        self.transfer_list = [
            listing for listing in self.transfer_list
            if (self.current_day - listing.listed_date) <= listing.expires_in
        ]

    def get_market_analysis(self):
        """Get current market statistics."""
        total_listings = len(self.transfer_list)
        total_value = sum(listing.asking_price for listing in self.transfer_list)
        avg_value = total_value / total_listings if total_listings > 0 else 0
        
        positions = {}
        for listing in self.transfer_list:
            pos = listing.player.position
            if pos not in positions:
                positions[pos] = {"count": 0, "total_value": 0}
            positions[pos]["count"] += 1
            positions[pos]["total_value"] += listing.asking_price
        
        return {
            "total_listings": total_listings,
            "total_market_value": total_value,
            "average_player_value": avg_value,
            "positions": {
                pos: {
                    "count": data["count"],
                    "average_value": data["total_value"] / data["count"]
                }
                for pos, data in positions.items()
            }
        }