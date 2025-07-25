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
    import random
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
        
        # Generate initial youth academy players for the first season
        for _ in range(random.randint(1, 3)):
            team.generate_youth_player()
    
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

def print_rising_talents(league):
    """Print the best youth academy players in the league."""
    all_youth = []
    for team in league.teams:
        for player in getattr(team, "youth_academy", []):
            if getattr(player, "age", 0) <= 19 and getattr(player, "squad_role", "") == "YOUTH":
                # Calculate actual ability (average attribute rating)
                try:
                    ability = sum(sum(cat.values()) for cat in player.attributes.values()) / sum(len(cat) for cat in player.attributes.values())
                except Exception:
                    ability = 0
                all_youth.append({
                    "name": player.name,
                    "team": team.name,
                    "potential": player.potential,
                    "ability": ability,
                    "age": player.age,
                    "position": player.position,
                    "value": getattr(league.transfer_market, "calculate_player_value", lambda x: 0)(player)
                })
    # Sort by potential, then value
    rising = sorted(all_youth, key=lambda p: (p["potential"], p["value"]), reverse=True)[:10]
    print("\nRising Talents: Best Youth Academy Players")
    print("=" * 90)
    print(f"{'Name':<25} {'Team':<20} {'Potential':<9} {'Ability':<8} {'Age':<3} {'Position':<10} {'Value':<10}")
    print("-" * 90)
    for p in rising:
        name_str = str(p['name']) if p['name'] is not None else "N/A"
        team_str = str(p['team']) if p['team'] is not None else "N/A"
        potential_str = str(p['potential']) if p['potential'] is not None else "N/A"
        ability_str = f"{p['ability']:.1f}" if p.get('ability') is not None else "N/A"
        age_str = str(p['age']) if p['age'] is not None else "N/A"
        position_str = str(p['position']) if p['position'] is not None else "N/A"
        value_str = str(p['value']) if p['value'] is not None else "N/A"
        print(f"{name_str:<25} {team_str:<20} {potential_str:<9} {ability_str:<8} {age_str:<3} {position_str:<10} {value_str:<10}")

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

        # Print team of the season (using the already prepared list of dicts)
        print("\nPremier League Team of the Season")
        print("=" * 95)
        print(f"{'Position':<10} {'Name':<25} {'Team':<20} {'Potential':<9} {'Ability':<8} {'Age':<3} {'Value':<10}")
        print("-" * 95)
        for player_data in full_season_report['best_players']:
            # Calculate actual ability (average attribute rating)
            ability = 0
            try:
                if "attributes" in player_data and player_data["attributes"]:
                    ability = sum(sum(cat.values()) for cat in player_data["attributes"].values()) / sum(len(cat) for cat in player_data["attributes"].values())
                else:
                    # If not present, fallback to 0
                    ability = 0
            except Exception:
                ability = 0
            print(f"{player_data.get('position', 'N/A'):<10} {player_data.get('name', 'N/A'):<25} {player_data.get('team', 'N/A'):<20} "
                  f"{player_data.get('potential', 0):<9} {ability:<8.1f} {player_data.get('age', 0):<3} {player_data.get('value', 0):<10}")

        # Print Rising Talents
        print_rising_talents(premier_league)

        # Save detailed report for each season
        report_filename = f'season_reports/season_report_{premier_league.season_year}.json'
        print(f"\nSaving detailed season {premier_league.season_year} report to '{report_filename}'...")
        with open(report_filename, 'w') as f:
            json.dump(full_season_report, f, indent=2) # Directly save the comprehensive report
        
        # Increment to next season
        premier_league.increment_season()

if __name__ == "__main__":
    main()
