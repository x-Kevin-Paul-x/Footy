from player import FootballPlayer
from manager import Manager
from team_db import create_team, get_team, update_team, delete_team
import random

class Team:
    def __init__(self, name, budget):
        """
        Initialize a team with comprehensive financial and operational attributes.
        
        Args:
            name (str): Team name
            budget (float): Team's initial budget for the season
        """
        self.name = name
        self.budget = budget
        self.initial_budget = budget  # Track original budget
        
        # Enhanced financial structure
        self.weekly_budget = budget / 52
        self.transfer_budget = budget * 0.3  # 30% for transfers
        self.wage_budget = budget * 0.5  # 50% for wages
        self.operational_budget = budget * 0.2  # 20% for operations
        
        # Stadium and infrastructure
        self.stadium_capacity = self._generate_stadium_capacity()
        self.stadium_name = f"{name} Stadium"
        self.average_attendance = 0
        self.ticket_prices = self._generate_ticket_prices()
        
        # Revenue streams
        self.sponsorship_deals = []
        self.tv_revenue = 0
        self.commercial_revenue = 0
        self.matchday_revenue = 0
        
        # Historical financial data
        self.revenue_history = []
        self.expense_history = []
        
        self.players = []
        self.manager = None
        self.coaches = []
        self.squad_roles_requirements = {
            "STARTER": 11,
            "BENCH": 7,
            "YOUTH": 5
        }
        self.youth_academy = []
        
        # Enhanced statistics
        self.statistics = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "transfer_history": [],
            "financial_history": [],
            "league_position": None,
            "points": 0
        }
        
        # Database attributes
        self.team_id = None
        
        # Generate initial sponsorship deals and TV revenue
        self._generate_initial_revenue_streams()

    def _generate_stadium_capacity(self):
        """Generate realistic stadium capacity based on team budget"""
        if self.budget > 400000000:  # Big clubs
            return random.randint(50000, 80000)
        elif self.budget > 200000000:  # Medium-large clubs
            return random.randint(30000, 50000)
        elif self.budget > 100000000:  # Medium clubs
            return random.randint(20000, 35000)
        else:  # Smaller clubs
            return random.randint(10000, 25000)

    def _generate_ticket_prices(self):
        """Generate ticket pricing structure"""
        base_price = 25 + (self.budget / 10000000)  # £25-75 base price
        return {
            "season_ticket": base_price * 19 * 0.8,  # 20% discount for season tickets
            "premium": base_price * 2.5,
            "standard": base_price,
            "concession": base_price * 0.6
        }

    def _generate_initial_revenue_streams(self):
        """Generate initial sponsorship deals and revenue streams"""
        # TV Revenue based on league status and budget
        base_tv = 30000000 + (self.budget / 20)  # £30M base + scaling
        self.tv_revenue = random.uniform(base_tv * 0.8, base_tv * 1.2)
        
        # Sponsorship deals
        shirt_sponsor_value = self.budget * random.uniform(0.05, 0.15)
        stadium_naming_value = self.budget * random.uniform(0.02, 0.08)
        
        self.sponsorship_deals = [
            {
                "type": "shirt_sponsor",
                "company": f"{random.choice(['Tech Corp', 'Global Bank', 'Energy Ltd', 'Airlines Inc'])}",
                "value": shirt_sponsor_value,
                "duration": random.randint(3, 5),
                "remaining_years": random.randint(1, 3)
            },
            {
                "type": "stadium_naming",
                "company": f"{random.choice(['Stadium Corp', 'Arena Holdings', 'Sports Ltd'])}",
                "value": stadium_naming_value,
                "duration": random.randint(5, 10),
                "remaining_years": random.randint(2, 8)
            }
        ]
        
        # Commercial revenue (merchandise, etc.)
        self.commercial_revenue = self.budget * random.uniform(0.1, 0.25)

    def save_to_database(self):
        """Save team to database"""
        if self.team_id is None:
            # Create new team
            manager_id = self.manager.manager_id if self.manager else None
            self.team_id = create_team(
                name=self.name,
                budget=self.budget,
                weekly_budget=self.weekly_budget,
                transfer_budget=self.transfer_budget,
                wage_budget=self.wage_budget,
                manager_id=manager_id
            )
        else:
            # Update existing team
            manager_id = self.manager.manager_id if self.manager else None
            update_team(
                team_id=self.team_id,
                name=self.name,
                budget=self.budget,
                weekly_budget=self.weekly_budget,
                transfer_budget=self.transfer_budget,
                wage_budget=self.wage_budget,
                manager_id=manager_id
            )
        return self.team_id

    @classmethod
    def load_from_database(cls, team_id):
        """Load team from database by ID"""
        data = get_team(team_id)
        if not data:
            return None
            
        team = cls(
            name=data["name"],
            budget=data["budget"]
        )
        team.team_id = data["team_id"]
        team.weekly_budget = data["weekly_budget"]
        team.transfer_budget = data["transfer_budget"]
        team.wage_budget = data["wage_budget"]
        return team

    def generate_youth_player(self):
        """Generate a new youth player and add to the academy."""
        age = random.randint(15, 18)
        potential = random.randint(60, 90)
        player = FootballPlayer.create_player(age=age, potential=potential)
        player.squad_role = "YOUTH"
        player.wage = random.randint(500, 2000)  # Youth wages
        self.youth_academy.append(player)
        return player

    def promote_youth_player(self, player):
        """Promote a youth player to the senior squad."""
        if player in self.youth_academy:
            self.youth_academy.remove(player)
            player.squad_role = "RESERVE"
            player.age = max(player.age, 17)
            player.wage *= random.uniform(2.0, 4.0)  # Significant wage increase
            self.add_player(player)
            return True
        return False

    def calculate_matchday_revenue(self, attendance_factor=1.0, importance_multiplier=1.0):
        """Calculate revenue from a single match"""
        # Base attendance (affected by team performance, weather, opposition)
        base_attendance = min(self.stadium_capacity, 
                             self.stadium_capacity * random.uniform(0.6, 0.95) * attendance_factor)
        
        # Calculate ticket revenue
        ticket_distribution = {
            "premium": 0.1,
            "standard": 0.7,
            "concession": 0.2
        }
        
        revenue = 0
        for ticket_type, percentage in ticket_distribution.items():
            tickets_sold = base_attendance * percentage
            revenue += tickets_sold * self.ticket_prices[ticket_type]
        
        # Add concessions, parking, merchandise (typically 25-30% of ticket revenue)
        additional_revenue = revenue * random.uniform(0.25, 0.35)
        total_revenue = (revenue + additional_revenue) * importance_multiplier
        
        # Update average attendance
        if self.average_attendance == 0:
            self.average_attendance = base_attendance
        else:
            self.average_attendance = (self.average_attendance * 0.9) + (base_attendance * 0.1)
        
        self.matchday_revenue += total_revenue
        return total_revenue

    def process_weekly_finances(self):
        """Process weekly financial operations"""
        # Calculate weekly revenue
        weekly_revenue = 0
        
        # TV revenue (distributed weekly)
        weekly_revenue += self.tv_revenue / 52
        
        # Commercial revenue (distributed weekly) 
        weekly_revenue += self.commercial_revenue / 52
        
        # Sponsorship revenue (distributed weekly)
        for deal in self.sponsorship_deals:
            weekly_revenue += deal["value"] / 52
        
        # Calculate weekly expenses
        expenses = self.calculate_weekly_expenses()
        weekly_expenses = expenses["total"]
        
        # Update budget
        net_weekly = weekly_revenue - weekly_expenses
        self.budget += net_weekly
        
        # Update financial history
        self.statistics["financial_history"].append({
            "week": len(self.statistics["financial_history"]) + 1,
            "revenue": weekly_revenue,
            "expenses": weekly_expenses,
            "net": net_weekly,
            "budget": self.budget
        })
        
        return {
            "revenue": weekly_revenue,
            "expenses": weekly_expenses,
            "net": net_weekly,
            "new_budget": self.budget
        }

    def negotiate_sponsorship_deal(self, deal_type, offer_value, duration):
        """Negotiate a new sponsorship deal"""
        # Calculate minimum acceptable value based on team performance and status
        current_performance_modifier = 1.0
        if self.statistics.get("league_position"):
            # Better league position = higher sponsorship value
            position_factor = max(0.5, (21 - self.statistics["league_position"]) / 20)
            current_performance_modifier = position_factor
        
        min_acceptable = self._get_market_value_for_sponsorship(deal_type) * current_performance_modifier
        
        if offer_value >= min_acceptable:
            # Remove existing deal of same type
            self.sponsorship_deals = [d for d in self.sponsorship_deals if d["type"] != deal_type]
            
            # Add new deal
            new_deal = {
                "type": deal_type,
                "company": f"New {deal_type.replace('_', ' ').title()} Sponsor",
                "value": offer_value,
                "duration": duration,
                "remaining_years": duration
            }
            self.sponsorship_deals.append(new_deal)
            return True, f"Sponsorship deal signed: £{offer_value:,.0f} per year for {duration} years"
        
        return False, f"Offer too low. Minimum acceptable: £{min_acceptable:,.0f}"

    def _get_market_value_for_sponsorship(self, deal_type):
        """Calculate market value for different sponsorship types"""
        base_values = {
            "shirt_sponsor": self.budget * 0.08,
            "stadium_naming": self.budget * 0.04,
            "training_ground": self.budget * 0.02,
            "kit_supplier": self.budget * 0.06
        }
        return base_values.get(deal_type, self.budget * 0.03)

    def upgrade_stadium(self, upgrade_type, cost):
        """Upgrade stadium facilities"""
        upgrades = {
            "capacity_expansion": {
                "cost_multiplier": 1000,  # £1000 per new seat
                "effect": "capacity"
            },
            "premium_seating": {
                "cost_multiplier": 2000,  # £2000 per premium seat
                "effect": "revenue_per_seat"
            },
            "facilities": {
                "cost_multiplier": 5000000,  # £5M base cost
                "effect": "attendance_boost"
            }
        }
        
        if upgrade_type not in upgrades:
            return False, "Invalid upgrade type"
        
        if cost > self.budget:
            return False, "Insufficient funds"
        
        # Process upgrade
        self.budget -= cost
        
        if upgrade_type == "capacity_expansion":
            new_seats = cost / upgrades[upgrade_type]["cost_multiplier"]
            self.stadium_capacity += int(new_seats)
            
        elif upgrade_type == "premium_seating":
            # Increase premium ticket ratio and prices
            self.ticket_prices["premium"] *= 1.1
            
        elif upgrade_type == "facilities":
            # Boost attendance by improving stadium experience
            self.average_attendance *= 1.05
        
        return True, f"Stadium upgrade completed: {upgrade_type}"

    def get_players_by_position(self, position):
        """Get all players in a specific position"""
        return [p for p in self.players if p.position == position]

    def get_squad_data(self):
        """Get enhanced squad composition data"""
        current_roles = {
            "STARTER": sum(1 for p in self.players if p.squad_role == "STARTER"),
            "BENCH": sum(1 for p in self.players if p.squad_role == "BENCH"),
            "YOUTH": sum(1 for p in self.players if p.squad_role == "YOUTH")
        }
        
        # Calculate squad value
        total_value = sum(self._calculate_player_market_value(p) for p in self.players)
        
        return {
            "total_players": len(self.players),
            "squad_value": total_value,
            "average_age": sum(p.age for p in self.players)/len(self.players) if self.players else 0,
            "average_rating": sum(p.get_overall_rating() for p in self.players)/len(self.players) if self.players else 0,
            "positions": {pos: len(self.get_players_by_position(pos))
                        for pos in ["GK", "CB", "LB", "RB", "CM", "CAM", "CDM", "LW", "RW", "ST"]},
            "squad_roles": {
                "current": current_roles,
                "requirements": self.squad_roles_requirements
            },
            "injured_players": sum(1 for p in self.players if p.is_injured),
            "youth_academy_size": len(self.youth_academy)
        }

    def _calculate_player_market_value(self, player):
        """Simple market value calculation for squad valuation"""
        base_value = player.get_overall_rating() * 1000
        age_factor = 1.2 if 23 <= player.age <= 28 else 0.8 if player.age > 30 else 1.0
        potential_factor = 1 + (max(0, player.potential - player.get_overall_rating()) / 100)
        return base_value * age_factor * potential_factor

    def get_financials(self):
        """Get comprehensive financial data"""
        # Calculate current wage bill
        total_wages = sum(p.wage for p in self.players)
        manager_cost = self.weekly_budget * 0.10 * 52 if self.manager else 0
        coach_cost = len(self.coaches) * (self.weekly_budget * 0.05) * 52
        
        # Calculate annual revenue
        annual_revenue = (
            self.tv_revenue +
            self.commercial_revenue +
            sum(deal["value"] for deal in self.sponsorship_deals) +
            self.matchday_revenue
        )
        
        return {
            "budget": self.budget,
            "transfer_budget": self.transfer_budget,
            "wage_budget": self.wage_budget,
            "operational_budget": self.operational_budget,
            "annual_revenue": annual_revenue,
            "revenue_breakdown": {
                "tv": self.tv_revenue,
                "commercial": self.commercial_revenue,
                "sponsorship": sum(deal["value"] for deal in self.sponsorship_deals),
                "matchday": self.matchday_revenue
            },
            "annual_expenses": total_wages * 52 + manager_cost + coach_cost,
            "wage_utilization": total_wages / (self.wage_budget / 52) if self.wage_budget > 0 else 0,
            "financial_health": "Good" if annual_revenue > total_wages * 52 else "Concerning",
            "net_position": annual_revenue - (total_wages * 52 + manager_cost + coach_cost)
        }

    def add_player(self, player):
        """Add a player to the team with financial validation."""
        if len(self.players) >= 40:
            raise ValueError("Squad size cannot exceed 40 players")
        
        # Check wage budget
        current_wages = sum(p.wage for p in self.players)
        weekly_wage_budget = self.wage_budget / 52
        
        if current_wages + player.wage > weekly_wage_budget:
            raise ValueError("Adding player would exceed wage budget")
        
        self.players.append(player)
        player.team = self.name

    def remove_player(self, player):
        """Remove a player from the team."""
        if player in self.players:
            self.players.remove(player)
            player.team = None

    def set_manager(self, manager):
        """Assign a manager to the team with salary negotiation."""
        self.manager = manager
        manager.team = self
        
        # Calculate manager salary based on team budget and experience
        base_salary = self.weekly_budget * 0.08  # 8-12% of weekly budget
        experience_multiplier = 1 + (manager.experience_level / 100)
        manager.salary = base_salary * experience_multiplier

    def add_coach(self, coach):
        """Add a coach to the team with salary calculation."""
        if len(self.coaches) >= 5:
            raise ValueError("Team cannot have more than 5 coaches")
        
        # Calculate coach salary
        coach.salary = self.weekly_budget * 0.03  # 3% of weekly budget per coach
        
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
        """Calculate overall team strength based on player attributes and fitness."""
        if not self.players:
            return 0
        
        total_rating = 0
        active_players = 0
        
        for player in self.players:
            if not player.is_available_for_selection():
                continue  # Skip injured/suspended players
                
            # Calculate position-specific rating
            if player.position == "GK":
                rating = sum(player.attributes["goalkeeping"].values()) / len(player.attributes["goalkeeping"])
            elif player.position in ["CB", "LB", "RB", "LWB", "RWB"]:
                rating = (sum(player.attributes["defending"].values()) + 
                         sum(player.attributes["physical"].values())) / (
                    len(player.attributes["defending"]) + len(player.attributes["physical"]))
            elif player.position in ["CM", "CDM", "CAM", "LM", "RM"]:
                rating = (sum(player.attributes["passing"].values()) + 
                         sum(player.attributes["dribbling"].values())) / (
                    len(player.attributes["passing"]) + len(player.attributes["dribbling"]))
            else:  # Forwards
                rating = (sum(player.attributes["shooting"].values()) + 
                         sum(player.attributes["pace"].values())) / (
                    len(player.attributes["shooting"]) + len(player.attributes["pace"]))
            
            # Apply fitness and form factors
            fitness_factor = player.stats["fitness"] / 100
            form_factor = player.get_form_rating()
            
            total_rating += rating * fitness_factor * form_factor
            active_players += 1
        
        return round(total_rating / active_players, 2) if active_players > 0 else 0

    def handle_transfer(self, player, fee, is_selling=True, day_of_window=None):
        """
        Enhanced transfer processing with financial validation.
        
        Args:
            player: Player being transferred
            fee: Transfer fee
            is_selling: True if selling, False if buying
            day_of_window: Day of transfer window
            
        Returns:
            bool: Whether transfer was successful
        """
        if is_selling:
            if player in self.players:
                self.players.remove(player)
                
                # Add transfer fee to budget
                self.budget += fee
                
                # Distribute fee across budgets
                transfer_portion = fee * 0.4
                wage_portion = fee * 0.3
                operational_portion = fee * 0.3
                
                self.transfer_budget += transfer_portion
                self.wage_budget += wage_portion
                self.operational_budget += operational_portion
                
                # Record transaction
                self.statistics["transfer_history"].append({
                    "type": "sale",
                    "player_name": player.name,
                    "price": fee,
                    "success": True,
                    "day_of_window": day_of_window,
                    "wage_saved": player.wage * 52,
                    "net_benefit": fee + (player.wage * 52)
                })
                return True
            return False
        else:  # Buying
            # Check if can afford transfer fee and wages
            if fee > self.transfer_budget:
                return False
            
            annual_wage_cost = player.wage * 52
            if annual_wage_cost > (self.wage_budget - sum(p.wage * 52 for p in self.players)):
                return False
            
            # Process purchase
            self.players.append(player)
            self.budget -= fee
            self.transfer_budget -= fee
            
            # Record transaction
            self.statistics["transfer_history"].append({
                "type": "purchase",
                "player_name": player.name,
                "price": fee,
                "success": True,
                "day_of_window": day_of_window,
                "annual_wage_cost": annual_wage_cost,
                "total_cost": fee + annual_wage_cost
            })
            return True

    def can_afford_transfer(self, fee, player_wage=None, include_wages=True):
        """Enhanced affordability check including long-term wage implications."""
        if fee > self.transfer_budget:
            return False
        
        if include_wages and player_wage:
            current_annual_wages = sum(p.wage * 52 for p in self.players)
            new_annual_wage = player_wage * 52
            
            if current_annual_wages + new_annual_wage > self.wage_budget:
                return False
        
        return True

    def get_transfer_budget_info(self):
        """Get comprehensive transfer budget information."""
        return {
            "total_budget": self.budget,
            "transfer_budget": self.transfer_budget,
            "wage_budget": self.wage_budget,
            "available_weekly_wages": (self.wage_budget - sum(p.wage * 52 for p in self.players)) / 52,
            "squad_size": len(self.players),
            "squad_value": sum(self._calculate_player_market_value(p) for p in self.players),
            "average_squad_age": sum(p.age for p in self.players) / len(self.players) if self.players else 0,
            "recent_transfers": self.statistics["transfer_history"][-5:],
            "can_buy_players": len(self.players) < 25,
            "needs_players": len(self.players) < 18,
            "financial_health": self.get_financials()["financial_health"]
        }

    def get_squad_needs(self):
        """Enhanced squad analysis with quality assessment."""
        position_analysis = {
            "GK": {"current": 0, "ideal": 2, "quality": 0},
            "DEF": {"current": 0, "ideal": 8, "quality": 0}, 
            "MID": {"current": 0, "ideal": 8, "quality": 0},
            "FWD": {"current": 0, "ideal": 5, "quality": 0}
        }
        
        # Analyze current squad
        for player in self.players:
            category = "GK" if player.position == "GK" else \
                      "DEF" if player.position in ["CB", "LB", "RB", "LWB", "RWB", "SW"] else \
                      "MID" if player.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"] else "FWD"
            
            position_analysis[category]["current"] += 1
            position_analysis[category]["quality"] += player.get_overall_rating()
        
        # Calculate average quality
        for pos_data in position_analysis.values():
            if pos_data["current"] > 0:
                pos_data["quality"] = pos_data["quality"] / pos_data["current"]
        
        # Determine needs
        needs = []
        for pos, data in position_analysis.items():
            shortage = data["ideal"] - data["current"]
            if shortage > 0:
                priority = "Critical" if pos == "GK" and data["current"] < 1 else \
                          "High" if shortage >= data["ideal"] * 0.5 else "Medium"
                needs.append({
                    "position": pos,
                    "shortage": shortage,
                    "priority": priority,
                    "quality": data["quality"]
                })
        
        return {
            "position_analysis": position_analysis,
            "needs": needs,
            "squad_balance": "Excellent" if not needs else "Good" if len(needs) <= 2 else "Needs Work",
            "recommended_signings": len(needs)
        }

    def calculate_weekly_expenses(self):
        """Calculate comprehensive weekly expenses."""
        expenses = {
            "player_wages": sum(p.wage for p in self.players),
            "manager_salary": self.weekly_budget * 0.10 if self.manager else 0,
            "coach_salaries": len(self.coaches) * (self.weekly_budget * 0.03),
            "youth_academy": len(self.youth_academy) * 200,  # £200 per youth player
            "stadium_maintenance": self.stadium_capacity * 0.1,  # £0.10 per seat per week
            "utilities": self.weekly_budget * 0.02,  # 2% for utilities
            "medical_staff": self.weekly_budget * 0.03,  # 3% for medical
            "travel_accommodation": self.weekly_budget * 0.02,  # 2% for travel
            "other_operational": self.weekly_budget * 0.05  # 5% other costs
        }
        
        total = sum(expenses.values())
        
        return {
            "total": round(total, 2),
            "breakdown": {k: round(v, 2) for k, v in expenses.items()},
            "as_percentage_of_budget": round((total / self.weekly_budget) * 100, 1)
        }
