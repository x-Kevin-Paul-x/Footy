from league import League
import json

from team import Team
from player import FootballPlayer
from manager import Manager

def create_premier_league():
    """Create Premier League with 20 teams"""
    teams = [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool",
        "Luton", "Manchester City", "Manchester United", "Newcastle",
        "Nottingham Forest", "Sheffield United", "Tottenham", "West Ham",
        "Wolves", "Burnley"
    ]
    
    # Create league with realistic budgets
    budgets = {
        "Manchester City": 500000000,
        "Manchester United": 400000000,
        "Chelsea": 400000000,
        "Arsenal": 300000000,
        "Liverpool": 300000000,
        "Tottenham": 250000000,
        "Newcastle": 250000000,
        "West Ham": 200000000,
        "Aston Villa": 200000000,
        "Brighton": 150000000,
        "Crystal Palace": 150000000,
        "Wolves": 150000000,
        "Fulham": 150000000,
        "Brentford": 120000000,
        "Bournemouth": 120000000,
        "Everton": 120000000,
        "Nottingham Forest": 100000000,
        "Burnley": 100000000,
        "Sheffield United": 100000000,
        "Luton": 100000000
    }
    
    premier_league = League("Premier League")
    premier_league.teams = []  # Clear default teams
    
    print("Creating Premier League teams...")
    for team_name in teams:
        team = Team(team_name, budgets[team_name])
        premier_league.teams.append(team)
        
        # Create and assign manager with profile
        profile = None  # Will use random profile from ManagerProfile.create_random_profile()
        manager = Manager(profile=profile)
        team.set_manager(manager)
        
        # Create squad
        #print(f"\nCreating {team_name} squad:")
        goalkeepers = [FootballPlayer.create_player(position="GK") for _ in range(2)]
        for gk in goalkeepers:
            team.add_player(gk)
            #print(f"Signed: {gk.name} ({gk.position}, Age: {gk.age})")
        
        # Add balanced squad of outfield players
        positions = {
            "DEF": ["CB", "LB", "RB", "CB", "LB", "RB", "CB", "CB"],  # 8 defenders
            "MID": ["CM", "CDM", "CAM", "CM", "LM", "RM", "CM", "CM"],  # 8 midfielders
            "FWD": ["ST", "CF", "LW", "RW", "ST"]  # 5 forwards
        }
        
        for pos_group, pos_list in positions.items():
            for position in pos_list:
                player = FootballPlayer.create_player(position=position)
                team.add_player(player)
                #print(f"Signed: {player.name} ({position}, Age: {player.age})")
    
    return premier_league

def print_league_table(table):
    """Print formatted league table"""
    print("\nPremier League Final Standings")
    print("=" * 75)
    print(f"{'Pos':<4} {'Team':<25} {'Pld':<4} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<4} {'Pts':<4}")
    print("-" * 75)
    
    for pos, (team, stats) in enumerate(table, 1):
        print(f"{pos:<4} {team:<25} {stats['played']:<4} {stats['won']:<3} {stats['drawn']:<3} {stats['lost']:<3} "
              f"{stats['gf']:<4} {stats['ga']:<4} {stats['gd']:<4} {stats['points']:<4}")

def print_best_xi(players):
    """Print team of the season"""
    print("\nPremier League Team of the Season")
    print("=" * 65)
    print(f"{'Position':<10} {'Name':<25} {'Team':<20} {'Rating':<6}")
    print("-" * 65)
    
    for player in players:
        avg_rating = sum(sum(cat.values()) for cat in player.attributes.values()) / \
                    sum(len(cat) for cat in player.attributes.values())
        print(f"{player.position:<10} {player.name:<25} {player.team:<20} {avg_rating:>6.2f}")

def main():
    
    num_seasons = 2

    # Create and simulate league
    premier_league = create_premier_league()
    
    for season in range(num_seasons):
        print(f"\nSeason {premier_league.season_year} - Generating season schedule...")
        premier_league.generate_schedule()
        
        print(f"Season {premier_league.season_year} - Simulating season...")
        premier_league.play_season()
        
        # Generate final reports
        full_season_report = premier_league.generate_season_report() # This now returns the rich dictionary
        
        # Print results (can use data from full_season_report)
        print_league_table(full_season_report['table'])
        
        # Print champions info
        champions_name = full_season_report['champions']
        print(f"\nPremier League Champions: {champions_name}!")
        
        # Print best manager (using the already prepared dict from the report)
        champion_manager_details = full_season_report['champions_manager']
        print(f"\nManager of the Season: {champion_manager_details['name']} ({champions_name})")
        print(f"Experience Level: {champion_manager_details['experience']}")
        print(f"Formation: {champion_manager_details['formation']}")
        print(f"Transfer Success Rate: {champion_manager_details['transfer_success_rate']:.1f}%")
        # Note: Detailed manager stats like win rate, specific profile weights, etc.,
        # would need to be added to the manager dict in generate_season_report if desired for console output here.
        # For now, focusing on what's in the example JSON.

        # Print team of the season (using the already prepared list of dicts)
        # The print_best_xi function expects player objects, but report['best_players'] is now dicts.
        # We can adjust print_best_xi or print directly. For simplicity, let's print directly.
        print("\nPremier League Team of the Season")
        print("=" * 75)
        print(f"{'Position':<10} {'Name':<25} {'Team':<20} {'Potential':<9} {'Age':<3} {'Value':<10}")
        print("-" * 75)
        for player_data in full_season_report['best_players']:
            print(f"{player_data.get('position', 'N/A'):<10} {player_data.get('name', 'N/A'):<25} {player_data.get('team', 'N/A'):<20} "
                  f"{player_data.get('potential', 0):<9} {player_data.get('age', 0):<3} {player_data.get('value', 0):<10}")

        # Save detailed report for each season
        report_filename = f'season_reports/season_report_{premier_league.season_year}.json'
        print(f"\nSaving detailed season {premier_league.season_year} report to '{report_filename}'...")
        with open(report_filename, 'w') as f:
            json.dump(full_season_report, f, indent=2) # Directly save the comprehensive report
        
        # Increment to next season
        premier_league.increment_season()

if __name__ == "__main__":
    main()
