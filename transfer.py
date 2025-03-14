from dataclasses import dataclass
from typing import List, Dict, Optional
import random

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
        return available
    
    def make_transfer_offer(self, buying_team, listing, offer_amount):
        """Attempt to buy a player from the transfer list."""
        if buying_team.budget < offer_amount:
            return False, "Insufficient funds"
        
        # Check if offer is acceptable
        min_acceptable = listing.asking_price * 0.8  # Will accept 20% below asking
        if offer_amount < min_acceptable:
            return False, "Offer too low"
        
        # Complete transfer
        buying_team.budget -= offer_amount
        listing.selling_team.budget += offer_amount
        
        # Update player's team
        listing.selling_team.remove_player(listing.player)
        buying_team.add_player(listing.player)
        
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
        """Simulate AI teams making transfer decisions."""
        for team in all_teams:
            if not team.manager:
                continue
                
            # AI team might list players
            for player in team.players:
                if len(team.players) > 18:  # Keep squad size reasonable
                    if random.random() < 0.3:  # 30% chance to list excess players
                        self.list_player(player, team)
            
            # AI team might buy players
            if team.budget > 1000000:  # Only if they have sufficient budget
                available = self.get_available_players(max_price=team.budget * 0.8)
                for listing in available:
                    if random.random() < 0.2:  # 20% chance to make offer
                        offer = listing.asking_price * random.uniform(0.8, 1.0)
                        self.make_transfer_offer(team, listing, offer)
    
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