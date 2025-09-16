from dataclasses import dataclass, field
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
    listing_id: int = field(default_factory=lambda: TransferListing.next_id(), init=False)

    _next_id = 1

    @classmethod
    def next_id(cls):
        result = cls._next_id
        cls._next_id += 1
        return result

@dataclass
class LoanListing:
    player: 'FootballPlayer'
    loan_fee: float
    wage_contribution: float  # Percentage of wages parent club pays
    selling_team: 'Team'
    duration: int  # Months
    buy_back_clause: Optional[float]  # Optional buy-back price
    listed_date: int
    expires_in: int = 30

class TransferMarket:
    def __init__(self, log_path=None):
        self.transfer_list: List[TransferListing] = []
        self.loan_list: List[LoanListing] = []
        self.current_day = 0
        self.transfer_history: List[Dict] = []
        self.loan_history: List[Dict] = []
        self.season_year = datetime.now().year

        # Enhanced transfer windows
        self.transfer_windows = {
            "summer": {"start": 1, "end": 61, "active": True},  # 61 days (2 months)
            "january": {"start": 183, "end": 214, "active": False}  # 31 days (1 month)
        }
        
        self.current_window = None
        self.free_agents: List[FootballPlayer] = []  # Players with expired contracts

        # Create transfer logs directory
        os.makedirs("transfer_logs", exist_ok=True)

        log_path = f'transfer_logs/season_{self.season_year}_transfers.txt' if log_path is None else log_path

        self.current_log = None
        if log_path:
            self.current_log = open(log_path, "a", encoding="utf-8")
        else:
            self._init_transfer_log()

        # Enhanced value multipliers
        self.value_modifiers = {
            "potential": 1.8,  # Higher weight for potential
            "age_discount": 0.95,
            "age_premium": 1.15,  # Higher premium for peak age
            "form_bonus": 1.2,  # Good form increases value
            "contract_discount": 0.8,  # Short contracts reduce value
            "position_premium": {
                "ST": 1.4, "CF": 1.4, "RW": 1.3, "LW": 1.3,  # Higher striker premium
                "CAM": 1.25, "CM": 1.1, "CDM": 1.05,
                "CB": 1.15, "LB": 1.05, "RB": 1.05,
                "GK": 1.2
            }
        }

    def get_current_window(self):
        """Determine which transfer window is currently active"""
        for window_name, window_info in self.transfer_windows.items():
            if window_info["start"] <= self.current_day <= window_info["end"]:
                return window_name
        return None

    def is_transfer_window_open(self):
        """Check if any transfer window is currently open"""
        return self.get_current_window() is not None

    def get_transfer_rumors(self, teams):
        """Generate enhanced transfer rumors including loan rumors"""
        rumors = []
        for team in teams:
            for player in team.players:
                if getattr(player, "transfer_interest", False) and random.random() < 0.3:
                    rumor = f"Rumor: {player.name} ({team.name}) is seeking a move this window."
                    rumors.append(rumor)
                    
                # Contract expiry rumors
                if player.contract_length <= 1 and random.random() < 0.4:
                    rumors.append(f"Contract Watch: {player.name}'s deal with {team.name} expires soon.")
                    
                # Loan rumors for young players
                if player.age < 23 and player.squad_role in ["RESERVE", "YOUTH"] and random.random() < 0.2:
                    rumors.append(f"Loan Watch: {player.name} could be available on loan from {team.name}.")
        
        # Add some general market rumors
        if random.random() < 0.15:
            rumors.append("Market News: Several clubs are reportedly preparing significant bids.")
        if random.random() < 0.1:
            rumors.append("Loan Market: Expect increased loan activity as clubs look to develop young talent.")
            
        return rumors

    def _init_transfer_log(self):
        """Initialize log file for current season"""
        log_path = f"transfer_logs/season_{self.season_year}_transfers.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Transfer Activity for Season {self.season_year}\n")
            f.write("=" * 80 + "\n\n")
        self.current_log = open(log_path, "a", encoding="utf-8")

    def close_log(self):
        """Ensure proper file closure"""
        if self.current_log and not self.current_log.closed:
            self.current_log.close()

    def _log_transfer_attempt(self, action: str, details: Dict):
        """Enhanced transfer logging"""
        if not self.current_log or self.current_log.closed:
            self._init_transfer_log()

        details["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        details["day"] = self.current_day
        details["window"] = self.get_current_window()
        
        if "player" in details and isinstance(details["player"], FootballPlayer):
            details["value"] = self.calculate_player_value(details["player"])
            details["player"] = details["player"].name
            
        self.current_log.write(f"{action}: {str(details)}\n")
        self.current_log.flush()

    def calculate_player_value(self, player) -> float:
        """Enhanced player valuation with more factors"""
        # Base value from attributes and overall rating
        overall_rating = player.get_overall_rating()
        # Increase base scaling for realism (e.g. 69.9 rating = £6.99M base)
        base_value = overall_rating * 100000

        # Age modifier (peak at 25-28)
        if player.age <= 20:
            age_factor = 0.7 + (player.potential / 200)  # Young with potential
        elif 21 <= player.age <= 24:
            age_factor = 0.9 + (player.potential / 300)  # Developing
        elif 25 <= player.age <= 28:
            age_factor = 1.2  # Peak years
        elif 29 <= player.age <= 31:
            age_factor = 1.0  # Still good
        elif 32 <= player.age <= 34:
            age_factor = 0.7  # Declining
        else:
            age_factor = 0.4  # Veteran

        # Potential modifier
        potential_gap = max(0, player.potential - overall_rating)
        potential_factor = 1 + (potential_gap / 100) * self.value_modifiers["potential"]

        # Form modifier
        form_rating = player.get_form_rating()
        form_factor = 0.8 + (form_rating * 0.4)  # 0.8 to 1.2 range

        # Contract length modifier
        if player.contract_length <= 1:
            contract_factor = self.value_modifiers["contract_discount"]
        elif player.contract_length >= 4:
            contract_factor = 1.1  # Long contracts increase value
        else:
            contract_factor = 1.0

        # Position modifier
        position_mod = self.value_modifiers["position_premium"].get(player.position, 1.0)

        # Squad role modifier (reduce youth penalty, boost for high potential youth)
        role_modifier = {
            "STARTER": 1.2,
            "RESERVE": 1.0,
            "YOUTH": 0.95 if player.potential > 70 else 0.85,
            "BENCH": 0.9
        }.get(player.squad_role, 1.0)

        # Injury history modifier
        recent_injuries = len([inj for inj in player.injury_history if inj.get("start_age", 0) >= player.age - 2])
        injury_factor = max(0.7, 1.0 - (recent_injuries * 0.1))

        # Calculate final value
        final_value = (base_value * age_factor * potential_factor * 
                      form_factor * contract_factor * position_mod * 
                      role_modifier * injury_factor)

        # Set minimum value to £500k for realism
        return max(500000, round(final_value))

    def list_player(self, player, team, asking_price=None):
        """Enhanced player listing with window checks"""
        if not self.is_transfer_window_open():
            return None, "Transfer window is closed"

        if asking_price is None:
            base_value = self.calculate_player_value(player)
            asking_price = base_value * random.uniform(0.8, 1.2)  # 80-120% of value

        self._log_transfer_attempt("LIST", {
            "player": player.name,
            "team": team.name,
            "price": asking_price,
            "value": self.calculate_player_value(player),
            "contract_length": player.contract_length
        })

        listing = TransferListing(
            player=player,
            asking_price=asking_price,
            selling_team=team,
            listed_date=self.current_day,
        )
        self.transfer_list.append(listing)
        return listing, "Player listed successfully"

    def list_player_for_loan(self, player, team, loan_fee=None, wage_contribution=0.5, 
                           duration=6, buy_back_clause=None):
        """List a player for loan"""
        if not self.is_transfer_window_open():
            return None, "Transfer window is closed"

        if loan_fee is None:
            loan_fee = player.wage * duration * 0.1  # Small loan fee

        listing = LoanListing(
            player=player,
            loan_fee=loan_fee,
            wage_contribution=wage_contribution,
            selling_team=team,
            duration=duration,
            buy_back_clause=buy_back_clause,
            listed_date=self.current_day
        )
        self.loan_list.append(listing)
        
        self._log_transfer_attempt("LOAN_LIST", {
            "player": player.name,
            "team": team.name,
            "loan_fee": loan_fee,
            "duration": duration,
            "wage_contribution": wage_contribution
        })
        
        return listing, "Player listed for loan"

    def get_available_players(self, max_price=None, position=None, max_age=None, min_potential=None):
        """Enhanced player search with more filters"""
        available = []
        for listing in self.transfer_list:
            if max_price and listing.asking_price > max_price:
                continue
            if position and listing.player.position != position:
                continue
            if max_age and listing.player.age > max_age:
                continue
            if min_potential and listing.player.potential < min_potential:
                continue
            available.append(listing)
        return available

    def get_available_loans(self, position=None, max_age=None, max_duration=None):
        """Get available loan players"""
        available = []
        for listing in self.loan_list:
            if position and listing.player.position != position:
                continue
            if max_age and listing.player.age > max_age:
                continue
            if max_duration and listing.duration > max_duration:
                continue
            available.append(listing)
        return available

    def get_free_agents(self, position=None, max_age=None):
        """Get available free agents"""
        available = []
        for player in self.free_agents:
            if position and player.position != position:
                continue
            if max_age and player.age > max_age:
                continue
            available.append(player)
        return available

    def get_listing_for_player(self, player: 'FootballPlayer') -> Optional['TransferListing']:
        """Find the current transfer listing for a specific player."""
        if player.player_id is None:
            # Cannot reliably find a player without an ID.
            # This can happen if a player object is created but not saved to the DB.
            # Fallback to name and age, though this is not guaranteed to be unique.
            for listing in self.transfer_list:
                if listing.player.name == player.name and listing.player.age == player.age:
                    return listing
            return None

        for listing in self.transfer_list:
            # player_id is the most reliable way to identify a player.
            if listing.player.player_id and listing.player.player_id == player.player_id:
                return listing
        return None

    def make_transfer_offer(self, buying_team, listing, offer_amount):
        """Enhanced transfer system with agent fees and installments"""
        if not self.is_transfer_window_open():
            return False, "Transfer window is closed"

        if buying_team.budget < offer_amount:
            return False, "Insufficient funds"

        # Agent fees (5-10% of transfer fee)
        agent_fee = offer_amount * random.uniform(0.05, 0.10)
        total_cost = offer_amount + agent_fee

        if buying_team.budget < total_cost:
            return False, "Cannot afford transfer fee plus agent fees"

        # Check if offer is acceptable
        min_acceptable = listing.asking_price * 0.75  # Will accept 25% below asking
        if offer_amount < min_acceptable:
            return False, "Offer too low"

        # Enhanced contract negotiation
        player = listing.player
        
        # Player wage demands based on new club and performance
        base_wage_demand = player.desired_wage
        
        # Adjust based on buying team's budget and league status
        team_wage_factor = min(2.0, buying_team.budget / 100000000)  # Up to 2x for rich clubs
        wage_demand = base_wage_demand * team_wage_factor * random.uniform(0.9, 1.3)

        # Check if team can afford wages
        if wage_demand > buying_team.wage_budget / max(1, len(buying_team.players)):
            return False, f"Player wage demands too high: £{wage_demand:,.0f}/week"

        # Contract length negotiation
        if player.age < 25:
            contract_length = random.randint(3, 5)  # Young players longer contracts
        elif player.age < 30:
            contract_length = random.randint(2, 4)
        else:
            contract_length = random.randint(1, 3)  # Older players shorter

        # Complete transfer
        player.wage = wage_demand
        player.contract_length = contract_length
        player.transfer_interest = False
        player.team = buying_team.name

        # Handle team finances
        if not buying_team.handle_transfer(player, total_cost, is_selling=False, day_of_window=self.current_day):
            return False, "Buying team financial failure"

        if not listing.selling_team.handle_transfer(player, offer_amount, is_selling=True, day_of_window=self.current_day):
            # Rollback if selling team transaction fails
            buying_team.handle_transfer(player, total_cost, is_selling=True, day_of_window=self.current_day)
            return False, "Selling team financial failure"

        # Record transfer
        transfer_record = {
            "player": player.name,
            "from_team": listing.selling_team.name,
            "to_team": buying_team.name,
            "amount": offer_amount,
            "agent_fee": agent_fee,
            "total_cost": total_cost,
            "wage": wage_demand,
            "contract_length": contract_length,
            "day": self.current_day,
            "window": self.get_current_window()
        }
        self.transfer_history.append(transfer_record)

        self._log_transfer_attempt("COMPLETED", transfer_record)

        # Remove listing
        self.transfer_list.remove(listing)

        return True, f"Transfer completed! {player.name} signs {contract_length}-year deal worth £{wage_demand:,.0f}/week"

    def make_loan_offer(self, borrowing_team, listing):
        """Handle loan transfers"""
        if not self.is_transfer_window_open():
            return False, "Transfer window is closed"

        player = listing.player
        loan_fee = listing.loan_fee
        
        if borrowing_team.budget < loan_fee:
            return False, "Cannot afford loan fee"

        # Calculate wage split
        weekly_wage_cost = player.wage * (1 - listing.wage_contribution)
        
        if weekly_wage_cost * 4 > borrowing_team.wage_budget / max(1, len(borrowing_team.players)):
            return False, "Cannot afford wage contribution"

        # Complete loan
        player.team = f"{borrowing_team.name} (on loan)"
        
        # Handle finances
        borrowing_team.budget -= loan_fee
        listing.selling_team.budget += loan_fee

        # Record loan
        loan_record = {
            "player": player.name,
            "from_team": listing.selling_team.name,
            "to_team": borrowing_team.name,
            "loan_fee": loan_fee,
            "duration": listing.duration,
            "wage_contribution": listing.wage_contribution,
            "buy_back_clause": listing.buy_back_clause,
            "day": self.current_day
        }
        self.loan_history.append(loan_record)

        self._log_transfer_attempt("LOAN_COMPLETED", loan_record)
        
        # Remove listing
        self.loan_list.remove(listing)
        
        return True, f"Loan completed! {player.name} joins on {listing.duration}-month loan"

    def sign_free_agent(self, team, player):
        """Sign a free agent player (no transfer window restriction, emergency override for thin squads)"""
        if player not in self.free_agents:
            return False, "Player not available as free agent"

        # Emergency override if squad is critically low
        emergency_override = len(team.players) < 16

        # Lower signing bonus for emergencies
        if emergency_override:
            signing_bonus = player.desired_wage * random.randint(5, 10)  # 5-10 weeks wages
        else:
            signing_bonus = player.desired_wage * random.randint(10, 26)  # 10-26 weeks wages

        # Override budget check if emergency
        if not emergency_override and team.budget < signing_bonus:
            return False, "Cannot afford signing bonus"

        # Contract negotiation
        wage_demand = player.desired_wage * (random.uniform(1.1, 1.4) if not emergency_override else random.uniform(1.0, 1.2))

        # Override wage budget check if emergency
        if not emergency_override and wage_demand > team.wage_budget / max(1, len(team.players)):
            return False, "Wage demands too high"

        # Contract length (longer contracts to reduce free agent frequency)
        if player.age < 30:
            contract_length = random.randint(3, 5)
        else:
            contract_length = random.randint(2, 4)

        # Complete signing
        player.wage = wage_demand
        player.contract_length = contract_length
        player.team = team.name
        team.budget -= signing_bonus
        team.add_player(player)

        # Record signing
        signing_record = {
            "player": player.name,
            "team": team.name,
            "signing_bonus": signing_bonus,
            "wage": wage_demand,
            "contract_length": contract_length,
            "day": self.current_day
        }

        self._log_transfer_attempt("FREE_AGENT", signing_record)
        self.free_agents.remove(player)

        return True, f"Free agent signed! {player.name} joins on {contract_length}-year deal"

    def process_contract_expiries(self, all_teams):
        """Process contract expiries at end of season with renewal logic"""
        expired_count = 0
        renewed_count = 0

        for team in all_teams:
            # Renew contracts for key players first
            for player in team.players[:]:
                player.contract_length -= 1
                
                # Attempt to renew contracts for important players
                if 0 < player.contract_length <= 1:
                    if self._should_renew_contract(player, team):
                        # Renew contract for 2-5 years (longer renewals)
                        player.contract_length += random.randint(2, 5)
                        renewed_count += 1
                        
                        self._log_transfer_attempt("CONTRACT_RENEWED", {
                            "player": player.name,
                            "team": team.name,
                            "new_length": player.contract_length
                        })

            # Process expiries for players who were not renewed
            for player in team.players[:]:
                if player.contract_length <= 0:
                    team.remove_player(player)
                    player.team = None
                    self.free_agents.append(player)
                    expired_count += 1
                    
                    self._log_transfer_attempt("CONTRACT_EXPIRED", {
                        "player": player.name,
                        "team": team.name,
                        "age": player.age
                    })
        
        print(f"\n{renewed_count} players had their contracts renewed.")
        return expired_count

    def _should_renew_contract(self, player, team):
        """Determine if a player's contract should be renewed."""
        # High-rated players are always renewed
        if player.get_overall_rating() > 80:
            return True
        
        # Young, high-potential players are renewed
        if player.age < 25 and player.potential > 85:
            return True
            
        # Key starters are usually renewed
        if player.squad_role == "STARTER" and player.age < 32:
            return True
            
        # Don't renew if squad is bloated
        if len(team.players) > 25:
            return False
            
        # Renew if player is still valuable and not too old
        if player.age < 34 and player.get_overall_rating() > 75:
            return True
            
        return False

    def simulate_ai_transfers(self, all_teams):
        """Enhanced AI transfer simulation"""
        if not self.is_transfer_window_open():
            return

        for team in all_teams:
            if not team.manager:
                continue

            # Get manager's transfer decisions
            actions = team.manager.make_transfer_decision(self)
            
            for action_type, *params in actions:
                if action_type == "list":
                    player, price = params
                    if len(team.players) > 18:  # Maintain minimum squad
                        listing, message = self.list_player(player, team, price)
                        if listing:
                            result = {
                                "type": "list",
                                "player": player,
                                "price": price,
                                "value_ratio": price / self.calculate_player_value(player),
                                "success": True,
                                "window": self.get_current_window(),
                                "market": self
                            }
                            team.manager.learn_from_transfer(result)

                elif action_type == "buy":
                    listing_id, offer = params
                    # Convert listing_id to TransferListing object
                    listing_obj = next((l for l in self.transfer_list if l.listing_id == listing_id), None)
                    if listing_obj is None:
                        print(f"Warning: TransferListing with ID {listing_id} not found.")
                        continue
                    success, message = self.make_transfer_offer(team, listing_obj, offer)
                    team.manager.transfer_attempts.append(success)

                    result = {
                        "type": "buy",
                        "player": listing_obj.player,
                        "price": offer,
                        "value_ratio": self.calculate_player_value(listing_obj.player) / offer,
                        "success": success,
                        "window": self.get_current_window(),
                        "reason": message,
                        "market": self
                    }
                    team.manager.learn_from_transfer(result)

                elif action_type == "loan_out":
                    player = params[0]
                    if player.age < 23 and player.squad_role in ["RESERVE", "YOUTH"]:
                        listing, message = self.list_player_for_loan(player, team)

                elif action_type == "loan_in":
                    listing = params[0]
                    success, message = self.make_loan_offer(team, listing)

                elif action_type == "free_agent":
                    player = params[0]
                    success, message = self.sign_free_agent(team, player)

    def advance_day(self):
        """Advance transfer market by one day"""
        self.current_day += 1

        # Remove expired listings
        self.transfer_list = [
            listing for listing in self.transfer_list
            if (self.current_day - listing.listed_date) <= listing.expires_in
        ]
        
        self.loan_list = [
            listing for listing in self.loan_list
            if (self.current_day - listing.listed_date) <= listing.expires_in
        ]

        # Update transfer window status
        current_window = self.get_current_window()
        if current_window != self.current_window:
            if current_window:
                self._log_transfer_attempt("WINDOW_OPEN", {"window": current_window, "day": self.current_day})
            else:
                self._log_transfer_attempt("WINDOW_CLOSED", {"previous_window": self.current_window, "day": self.current_day})
            self.current_window = current_window

    def get_market_analysis(self):
        """Enhanced market analysis"""
        total_listings = len(self.transfer_list)
        loan_listings = len(self.loan_list)
        free_agents_count = len(self.free_agents)
        
        total_value = sum(listing.asking_price for listing in self.transfer_list)
        avg_value = total_value / total_listings if total_listings > 0 else 0

        # Position analysis
        positions = {}
        for listing in self.transfer_list:
            pos = listing.player.position
            if pos not in positions:
                positions[pos] = {"count": 0, "total_value": 0, "avg_age": 0}
            positions[pos]["count"] += 1
            positions[pos]["total_value"] += listing.asking_price
            positions[pos]["avg_age"] += listing.player.age

        for pos_data in positions.values():
            if pos_data["count"] > 0:
                pos_data["average_value"] = pos_data["total_value"] / pos_data["count"]
                pos_data["avg_age"] = pos_data["avg_age"] / pos_data["count"]

        return {
            "current_day": self.current_day,
            "current_window": self.get_current_window(),
            "window_open": self.is_transfer_window_open(),
            "total_listings": total_listings,
            "loan_listings": loan_listings,
            "free_agents": free_agents_count,
            "total_market_value": total_value,
            "average_player_value": avg_value,
            "positions": positions,
            "transfers_completed": len(self.transfer_history),
            "loans_completed": len(self.loan_history)
        }
