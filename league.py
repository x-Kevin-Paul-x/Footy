import os
import json
from datetime import datetime
from match import Match
from team import Team
from manager import Manager
from coach import Coach

class League:
    def __init__(self, name, num_teams=20):
        self.name = name
        self.teams = [Team(f"Team {i+1}", budget=100000000) for i in range(num_teams)]
        self.matches = []
        self.standings = {}
        self.match_reports_dir = "match_reports"
        self.season_year = datetime.now().year
        
        # Initialize managers and coaches for all teams
        for team in self.teams:
            team.manager = Manager()
            for _ in range(3):  # Add 3 coaches per team
                team.add_coach(Coach())
        
        # Create directory for match reports
        os.makedirs(self.match_reports_dir, exist_ok=True)

    def generate_schedule(self):
        """Create a double round-robin schedule"""
        fixtures = []
        for _ in range(2):  # Home and away matches
            for i in range(len(self.teams)):
                for j in range(len(self.teams)):
                    if i != j:
                        fixtures.append((self.teams[i], self.teams[j]))
        self.matches = fixtures

    def play_season(self):
        """Play all matches in the season"""
        match_day = 1
        
        for idx, (home, away) in enumerate(self.matches):
            # Weekly training and development for both teams
            for team in [home, away]:
                self._weekly_team_training(team)
            
            # Play the match
            print(f"\nMatch Day {match_day}")
            match = Match(home, away)
            result = match.play_match()
            
            # Update manager's record based on match result
            if home.manager and away.manager:
                home.manager.matches_played += 1
                away.manager.matches_played += 1
                
                if result["score"][0] > result["score"][1]:
                    home.manager.wins += 1
                    away.manager.losses += 1
                elif result["score"][0] < result["score"][1]:
                    away.manager.wins += 1
                    home.manager.losses += 1
                else:
                    home.manager.draws += 1
                    away.manager.draws += 1
            
            # Save match report
            self.save_match_report(match, result, idx+1)
            
            # Update standings
            self.update_standings(home, away, result)
            
            # Every 7 matches is considered a new week
            if idx % 7 == 6:
                match_day += 1
                if match_day in [13, 26]:  # Transfer windows
                    print(f"\nTransfer Window Opens!")
                    self._run_transfer_window(days=7)

    def save_match_report(self, match, result, match_number):
        """Save match details to JSON file"""
        report = {
            "match_number": match_number,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "home_team": match.home_team.name,
            "away_team": match.away_team.name,
            "score": result["score"],
            "possession": result.get("possession", [50, 50]),
            "shots": result.get("shots", {"total": [0, 0], "on_target": [0, 0]}),
            "weather": match.weather,
            "intensity": match.intensity
        }
        
        filename = f"{self.season_year}_Match_{match_number:04d}.json"
        path = os.path.join(self.match_reports_dir, filename)
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)

    def update_standings(self, home, away, result):
        """Update league standings based on match result"""
        # Initialize team standings if not exists
        for team in [home, away]:
            if team.name not in self.standings:
                self.standings[team.name] = {
                    "points": 0,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "gf": 0,
                    "ga": 0,
                    "gd": 0
                }
        
        # Update match stats
        home_goals = result["score"][0]
        away_goals = result["score"][1]
        
        # Home team
        self.standings[home.name]["played"] += 1
        self.standings[home.name]["gf"] += home_goals
        self.standings[home.name]["ga"] += away_goals
        self.standings[home.name]["gd"] = self.standings[home.name]["gf"] - self.standings[home.name]["ga"]
        
        # Away team
        self.standings[away.name]["played"] += 1
        self.standings[away.name]["gf"] += away_goals
        self.standings[away.name]["ga"] += home_goals
        self.standings[away.name]["gd"] = self.standings[away.name]["gf"] - self.standings[away.name]["ga"]
        
        # Update points
        if home_goals > away_goals:
            self.standings[home.name]["won"] += 1
            self.standings[home.name]["points"] += 3
            self.standings[away.name]["lost"] += 1
        elif home_goals < away_goals:
            self.standings[away.name]["won"] += 1
            self.standings[away.name]["points"] += 3
            self.standings[home.name]["lost"] += 1
        else:
            self.standings[home.name]["drawn"] += 1
            self.standings[home.name]["points"] += 1
            self.standings[away.name]["drawn"] += 1
            self.standings[away.name]["points"] += 1

    def get_league_table(self):
        """Generate sorted league table"""
        sorted_table = sorted(self.standings.items(),
                            key=lambda x: (-x[1]['points'], -x[1]['gd'], -x[1]['gf']))
        return sorted_table

    def get_best_manager(self):
        """Find manager with best performance metrics"""
        # Get team with best points from standings
        champions = max(self.standings.items(), key=lambda x: x[1]['points'])
        champion_team = next(t for t in self.teams if t.name == champions[0])
        
        if champion_team.manager:
            return champion_team, champion_team.manager
        
        # Fallback to highest win rate if no champion manager
        return max(
            [(team, team.manager) for team in self.teams if team.manager],
            key=lambda x: (
                x[1].wins / x[1].matches_played if x[1].matches_played > 0 else 0,
                x[0].get_squad_strength()
            )
        )

    def get_best_players(self, num=11):
        """Select best players from all teams"""
        all_players = []
        for team in self.teams:
            all_players.extend(team.players)
            
        # Sort players by average attribute rating
        return sorted(all_players,
                    key=lambda p: sum(
                        sum(category.values()) 
                        for category in p.attributes.values()
                    ) / sum(len(category) for category in p.attributes.values()),
                    reverse=True)[:num]

    def _run_transfer_window(self, days=7):
        """Run a transfer window period."""
        from transfer import TransferMarket
        market = TransferMarket()
        
        for day in range(days):
            print(f"\nTransfer Window - Day {day + 1}")
            
            # Teams make transfer decisions
            for team in self.teams:
                if team.manager:
                    actions = team.manager.make_transfer_decision(market)
                    
                    # Process transfer actions
                    for action_type, *params in actions:
                        if action_type == "list":
                            player, price = params
                            market.list_player(player, team, price)
                            print(f"{team.name} lists {player.name} for £{price:,.2f}")
                        elif action_type == "buy":
                            listing, offer = params
                            success = market.make_transfer_offer(team, listing, offer)
                            if success:
                                print(f"{team.name} signs {listing.player.name} for £{offer:,.2f}")
            
            # Update market
            market.advance_day()
        
        # Print window summary
        print("\nTransfer Window Summary:")
        for team in self.teams:
            print(f"\n{team.name}:")
            print(f"Remaining Budget: £{team.budget:,.2f}")
            print(f"Squad Size: {len(team.players)}")
            needs = team.get_squad_needs()
            print(f"Squad Needs: {needs['needs']}")
    
    def _weekly_team_training(self, team):
        """Handle weekly training and development for a team."""
        # Organize players by position groups
        position_groups = {
            "GK": [],
            "DEF": [],
            "MID": [],
            "FWD": []
        }
        
        for player in team.players:
            if player.position == "GK":
                position_groups["GK"].append(player)
            elif player.position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]:
                position_groups["DEF"].append(player)
            elif player.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]:
                position_groups["MID"].append(player)
            else:
                position_groups["FWD"].append(player)
        
        # Assign best matching coaches to position groups
        for coach in team.coaches:
            # Determine coach's best position group
            coach_specialty = "MID"  # Default
            if "GK" in coach.specialties:
                coach_specialty = "GK"
            elif any(pos in coach.specialties for pos in ["CB", "LB", "RB", "LWB", "RWB", "SW"]):
                coach_specialty = "DEF"
            elif any(pos in coach.specialties for pos in ["ST", "CF", "LW", "RW"]):
                coach_specialty = "FWD"
            
            # Train players in coach's specialty group
            for player in position_groups[coach_specialty]:
                # Determine training intensity based on player fitness and upcoming matches
                if player.stats["fitness"] > 80:
                    intensity = "high"
                elif player.stats["fitness"] > 50:
                    intensity = "medium"
                else:
                    intensity = "low"
                
                # Apply training with coach bonus
                coach_bonus = coach.experience_level / 10.0
                player.train_player(
                    intensity=intensity,
                    training_days=3,  # Three sessions per week
                    coach_bonus=coach_bonus
                )
    
    def generate_season_report(self):
        """Compile comprehensive season report"""
        return {
            "league_table": self.get_league_table(),
            "best_manager": self.get_best_manager(),
            "best_players": self.get_best_players(),
            "season_stats": {
                "total_matches": len(self.matches),
                "total_goals": sum(t['gf'] for t in self.standings.values()),
                "best_attack": max(self.standings.items(), key=lambda x: x[1]['gf']),
                "best_defense": min(self.standings.items(), key=lambda x: x[1]['ga'])
            }
        }