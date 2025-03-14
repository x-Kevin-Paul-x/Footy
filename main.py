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
        
        # Create and assign manager
        manager = Manager()
        team.set_manager(manager)
        #print(f"{team_name} Manager: {manager.name} (Experience: {manager.experience_level})")
        
        # Create squad
        #print(f"\nCreating {team_name} squad:")
        goalkeepers = [FootballPlayer.create_player(position="GK") for _ in range(2)]
        for gk in goalkeepers:
            team.add_player(gk)
            #print(f"Signed: {gk.name} ({gk.position}, Age: {gk.age})")
        
        for _ in range(14):  # 14 outfield players
            player = FootballPlayer.create_player()
            team.add_player(player)
            #print(f"Signed: {player.name} ({player.position}, Age: {player.age})")
    
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
    # Create and simulate league
    premier_league = create_premier_league()
    
    for _ in range(3):
        print("\nGenerating season schedule...")
        premier_league.generate_schedule()
        
        print("\nSimulating season...")
        premier_league.play_season()
        
        # Generate final reports
        report = premier_league.generate_season_report()
        
        # Print results
        print_league_table(report['league_table'])
        
        # Print champions info
        champions = report['league_table'][0][0]
        print(f"\nPremier League Champions: {champions}!")
        
        # Print best manager
        champions_team = report['league_table'][0][0]
        champions_manager = next(team.manager for team in premier_league.teams if team.name == champions_team)
        print(f"\nManager of the Season: {champions_manager.name} ({champions_team})")
        print(f"Experience Level: {champions_manager.experience_level}")
        manager_stats = champions_manager.getstats()
        # Calculate stats if available
        matches_played = manager_stats.get('matches_played',38)  # Assuming full season
        wins = manager_stats.get('wins', 0)
        draws = manager_stats.get('draws', 0)
        losses = manager_stats.get('losses', 0)
        
        win_rate = manager_stats.get('win_rate', 0) 
        draw_rate = manager_stats.get('draw_rate', 0) 
        
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Draw Rate: {draw_rate:.1f}%")
        print(f"Total Matches: {matches_played}")
        print(f"Record: W{wins}-D{draws}-L{losses}")
        print(f"Preferred Formation: {manager_stats['formation_preferences'][0][0]}")
        
        # Print team of the season
        print_best_xi(report['best_players'])
        
        # Save detailed report
        print("\nSaving detailed season report to 'season_report.json'...")
        with open('season_report.json', 'w') as f:
            json.dump({
                'season': premier_league.season_year,
                'champions': champions_team,
                'champions_manager': {
                    'name': champions_manager.name,
                    'experience': champions_manager.experience_level,
                    'formation': manager_stats['formation_preferences'][0][0]
                },
                'table': report['league_table'],
                'best_players': [
                    {
                        'name': p.name,
                        'position': p.position,
                        'team': p.team,
                        'potential': p.potential
                    }
                    for p in report['best_players']
                ]
            }, f, indent=2)

if __name__ == "__main__":
    main()