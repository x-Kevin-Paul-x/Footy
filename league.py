import os
import json
from datetime import datetime
import random
from match import Match
from team import Team
from manager import Manager
from coach import Coach
from transfer import TransferMarket

class League:
    def __init__(self, name, num_teams=20):
        self.name = name
        self.teams = [Team(f"Team {i+1}", budget=100000000) for i in range(num_teams)]
        self.matches = []
        self.standings = {}
        self.match_reports_dir = "match_reports"
        self.historical_standings = []
        self.season_year = datetime.now().year
        
        # Initialize teams with players
        for team in self.teams:
            # Add players to each team (minimum squad size)
            self._initialize_team_squad(team)
        
        # Initialize managers and coaches for all teams
        for team in self.teams:
            # Initialize manager with random profile for varied strategies
            profile = None  # Will use random profile from ManagerProfile.create_random_profile()
            team.manager = Manager(profile=profile)
            
            # Add coaches
            for _ in range(3):
                team.add_coach(Coach())
        
        # Create directory for match reports
        self._init_season()
        os.makedirs(self.match_reports_dir, exist_ok=True)

    def generate_schedule(self):
        """Create a proper double round-robin schedule"""
        fixtures = []
        teams = self.teams
        n = len(teams)
        
        # Create home/away matches for each unique pair
        for i in range(n):
            for j in range(n):
                if i != j:
                    fixtures.append((teams[i], teams[j]))
        
        # Randomize match order to create realistic schedule
        random.shuffle(fixtures)
        self.matches = fixtures

    def play_season(self):
        """Play all matches in the season"""
        match_day = 1
        
        for idx, (home, away) in enumerate(self.matches):
            # Weekly training and development for both teams
            for team in [home, away]:
                self._weekly_team_training(team)
            
            # Play the match
            #print(f"\nMatch Day {match_day}")
            match = Match(home, away)
            result = match.play_match()
            
            # Save match report
            self.save_match_report(match, result, idx+1)
            
            # Update standings
            self.update_standings(home, away, result)
            
            # Provide learning feedback to managers
            if home.manager:
                home_result = {
                    "winner": result["score"][0] > result["score"][1],
                    "draw": result["score"][0] == result["score"][1],
                    "goals_for": result["score"][0],
                    "goals_against": result["score"][1],
                    "possession": result.get("possession", [50, 50])[0],
                    "youth_minutes": self._calculate_youth_minutes(home.players, match),
                    "player_development": self._calculate_player_development(home.players)
                }
                home.manager.learn_from_match(home_result)
                
            if away.manager:
                away_result = {
                    "winner": result["score"][1] > result["score"][0],
                    "draw": result["score"][0] == result["score"][1],
                    "goals_for": result["score"][1],
                    "goals_against": result["score"][0],
                    "possession": result.get("possession", [50, 50])[1],
                    "youth_minutes": self._calculate_youth_minutes(away.players, match),
                    "player_development": self._calculate_player_development(away.players)
                }
                away.manager.learn_from_match(away_result)
            
            # Every 7 matches is considered a new week
            if idx % 7 == 6:
                match_day += 1
                if match_day in [13, 26]:  # Transfer windows
                    #print(f"\nTransfer Window Opens!")
                    self._run_transfer_window(days=7)

    def save_match_report(self, match, result, match_number):
        """Save match details to JSON file"""
        report = {
            "match_number": match_number,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "season_year": self.season_year,
            "away_team": match.away_team.name,
            "score": result["score"],
            "possession": result.get("possession", [50, 50]),
            "shots": result.get("shots", {"total": [0, 0], "on_target": [0, 0]}),
            "weather": match.weather,
            "intensity": match.intensity
        }
        
        filename = f"{datetime.now().year}_Match_{match_number:04d}.json"
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
        market = TransferMarket()
        
        for day in range(days):
            #print(f"\nTransfer Window - Day {day + 1}")
            
            # Teams make transfer decisions
            for team in self.teams:
                if team.manager:
                    # Get manager's decisions using Q-learning
                    actions = team.manager.make_transfer_decision(market)
                    
                    # Process transfer actions and collect results
                    for action_type, *params in actions:
                        if action_type == "list":
                            player, price = params
                            listed = market.list_player(player, team, price)
                            
                            if listed:
                                result = {
                                    "type": "list",
                                    "player": player,
                                    "price": price,
                                    "value_ratio": price / market.calculate_player_value(player),
                                    "need_satisfaction": 0.0,
                                    "month": (self.season_year % 12) + 1,
                                    "market": market
                                }
                                team.manager.learn_from_transfer(result)
                                
                        elif action_type == "buy":
                            listing, offer = params
                            success = market.make_transfer_offer(team, listing, offer)
                            
                            if success:
                                result = {
                                    "type": "buy",
                                    "player": listing.player,
                                    "price": offer,
                                    "value_ratio": market.calculate_player_value(listing.player) / offer,
                                    "need_satisfaction": self._calculate_need_satisfaction(team, listing.player),
                                    "age_impact": (27 - listing.player.age) / 27 if listing.player.age <= 27 else 0,
                                    "month": (self.season_year % 12) + 1,
                                    "market": market
                                }
                                team.manager.learn_from_transfer(result)
            
            # Update market
            market.advance_day()
        
        # Print window summary
        #print("\nTransfer Window Summary:")
        #for team in self.teams:
        #   print(f"\n{team.name}:")
        #    print(f"Remaining Budget: £{team.budget:,.2f}")
        #    print(f"Squad Size: {len(team.players)}")
        #    needs = team.get_squad_needs()
        #    print(f"Squad Needs: {needs['needs']}")
    
    def increment_season(self):
        """Advance to new season"""
        self.season_year += 1
        self._init_season()
        print(f"Advanced to season {self.season_year}")

    def _calculate_youth_minutes(self, players: list, match: Match) -> float:
        """Calculate minutes played by youth players (under 23)."""
        youth_minutes = 0
        for player in players:
            if player.age < 23:
                # Estimate minutes based on match participation
                if player in match.home_lineup or player in match.away_lineup:
                    youth_minutes += 90  # Full match assumption
        return youth_minutes

    def _calculate_player_development(self, players: list) -> float:
        """Calculate average development progress for the squad."""
        if not players:
            return 0.0
            
        total_progress = 0
        for player in players:
            # Calculate progress as percentage towards potential
            current_ability = sum(sum(cat.values()) for cat in player.attributes.values()) / (
                len(player.attributes) * len(next(iter(player.attributes.values())))
            )
            max_potential = player.potential
            progress = (current_ability / max_potential) if max_potential > 0 else 0
            total_progress += progress
            
        return total_progress / len(players)

    def _calculate_need_satisfaction(self, team: Team, player) -> float:
        """Calculate how well a player satisfies team needs."""
        squad_needs = team.get_squad_needs()
        position_group = self._get_position_group(player.position)
        
        # Get current and ideal counts for the position
        current_count = squad_needs["current_distribution"].get(position_group, 0)
        ideal_count = squad_needs["ideal_distribution"].get(position_group, 0)
        
        if ideal_count == 0:
            return 0.0
            
        # Calculate need satisfaction (0.0 to 1.0)
        if current_count < ideal_count:
            return 1.0  # Fills a needed position
        else:
            return max(0.0, 1.0 - ((current_count - ideal_count) / ideal_count))

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
            if "GK" in coach.specialty:
                coach_specialty = "GK"
            elif any(pos in coach.specialty for pos in ["CB", "LB", "RB", "LWB", "RWB", "SW"]):
                coach_specialty = "DEF"
            elif any(pos in coach.specialty for pos in ["ST", "CF", "LW", "RW"]):
                coach_specialty = "FWD"
            # Train all players with appropriate intensity
            for group, players in position_groups.items():
                for player in players:
                    # Determine training intensity based on player fitness and upcoming matches
                    if player.stats["fitness"] > 80:
                        intensity = "high"
                    elif player.stats["fitness"] > 50:
                        intensity = "medium"
                    else:
                        intensity = "low"
                    
                    # Apply higher coach bonus if player matches coach specialty
                    coach_bonus = coach.experience_level / 10.0
                    if group == coach_specialty:
                        coach_bonus *= 1.5  # 50% bonus for specialized coaching
                    
                    # Apply training with focus on position-specific attributes
                    focus_area = None
                    if group == "GK":
                        focus_area = "goalkeeping"
                    elif group == "DEF":
                        focus_area = "defending"
                    elif group == "MID":
                        focus_area = "passing"
                    elif group == "FWD":
                        focus_area = "shooting"
                    
                    player.train_player(
                        intensity=intensity,
                        training_days=3,  # Three sessions per week
                        coach_bonus=coach_bonus,
                        focus_area=focus_area
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
    
    def _init_season(self):
        """Initialize/reset season-specific data"""
        self.historical_standings.append((self.season_year, self.standings))
        self.standings = {}
        
    def _initialize_team_squad(self, team):
        """Initialize a team with a full squad of players."""
        from player import FootballPlayer
        import names
        import random
        
        # Create squad with position distribution
        squad_template = {
            "GK": 3,  # Goalkeepers
            "DEF": 8,  # Defenders (CB, LB, RB)
            "MID": 8,  # Midfielders (CM, CDM, CAM)
            "FWD": 4   # Forwards (ST, LW, RW)
        }
        
        position_details = {
            "GK": ["GK"],
            "DEF": ["CB", "LB", "RB", "CB", "CB", "LWB", "RWB", "SW"],
            "MID": ["CM", "CDM", "CAM", "CM", "LM", "RM", "CM", "DM"],
            "FWD": ["ST", "CF", "LW", "RW"]
        }
        
        # Generate players for each position group
        for group, count in squad_template.items():
            positions = position_details[group]
            for _ in range(count):
                age = random.randint(17, 35)
                potential = random.randint(60, 90)
                # Higher potential for younger players
                if age < 23:
                    potential = random.randint(70, 95)
                
                player = FootballPlayer(
                    name=names.get_full_name(),
                    age=age,
                    position=positions[_ % len(positions)],
                    potential=potential
                )
                team.add_player(player)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Football League Simulation')
    parser.add_argument('--seasons', type=int, default=1, help='Number of seasons to simulate')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    # Helper function for debug output
    def debug_print(*msg, **kwargs):
        if args.debug:
            print(*msg, **kwargs)

    # Create league with smaller number of teams for testing
    league = League("Debug League", num_teams=6)
    debug_print(f"\nCreated league with {len(league.teams)} teams")

    # Enable debug mode for managers if --debug flag is set
    if args.debug:
        for team in league.teams:
            if team.manager:
                team.manager.set_debug(True)
                debug_print(f"Enabled debug mode for {team.manager.name} ({team.name})")

    debug_print(f"\nStarting {args.seasons} season simulation...")

    for season in range(args.seasons):
        debug_print(f"\n{'='*50}")
        debug_print(f"Season {season + 1}")
        debug_print(f"{'='*50}")
        
        league.generate_schedule()
        league.play_season()
        
        # Print season summary in debug mode
        if args.debug:
            standings = league.get_league_table()
            debug_print("\nFinal Standings:")
            debug_print(f"{'Team':<20} {'Pts':>3} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>3} {'GA':>3} {'GD':>3}")
            debug_print('-' * 55)
            for team_name, stats in standings:
                debug_print(f"{team_name:<20} {stats['points']:>3} {stats['played']:>3} "
                          f"{stats['won']:>3} {stats['drawn']:>3} {stats['lost']:>3} "
                          f"{stats['gf']:>3} {stats['ga']:>3} {stats['gd']:>3}")
            
            champion_team, champion_manager = league.get_best_manager()
            debug_print(f"\nChampion Manager: {champion_manager.name}")
            debug_print(f"Team: {champion_team.name}")
            debug_print(f"Record: W{champion_manager.wins}-D{champion_manager.draws}-L{champion_manager.losses}")
            win_rate = (champion_manager.wins/champion_manager.matches_played)*100 if champion_manager.matches_played > 0 else 0
            debug_print(f"Win Rate: {win_rate:.1f}%")
            
            # Show top managers' learning stats
            debug_print("\nManager Learning Progress:")
            for team in sorted(league.teams,
                            key=lambda t: t.manager.wins/t.manager.matches_played if t.manager and t.manager.matches_played > 0 else 0,
                            reverse=True)[:3]:
                if team.manager:
                    debug_print(f"\n{team.manager.name} ({team.name}):")
                    stats = team.manager.get_stats()
                    debug_print(f"Exploration Rate: {stats['current_exploration_rate']:.2f}")
                    debug_print(f"Transfer Success: {stats['transfer_success_rate']*100:.1f}%")
        
        league.increment_season()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, default=1, help="Number of seasons to simulate")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    def debug_print(*msg, **kwargs):
        if args.debug:
            print(*msg, **kwargs)

    # Create and run league simulation
    league = League("Debug League", num_teams=6)  # Smaller league for testing
    debug_print(f"\nStarting {args.seasons} season simulation...")

    for season in range(args.seasons):
        debug_print(f"\nSeason {season + 1}")
        league.generate_schedule()
        league.play_season()
        
        # Print season summary in debug mode
        if args.debug:
            standings = league.get_league_table()
            debug_print("\nFinal Standings:")
            for team_name, stats in standings:
                debug_print(f"{team_name}: {stats['points']} pts (W{stats['won']}-D{stats['drawn']}-L{stats['lost']})")
            
            champion_team, champion_manager = league.get_best_manager()
            debug_print(f"\nChampion Manager: {champion_manager.name}")
            debug_print(f"Team: {champion_team.name}")
            debug_print(f"Win Rate: {(champion_manager.wins/champion_manager.matches_played)*100:.1f}%")
        
        league.increment_season()
