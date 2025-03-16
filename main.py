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
        manager_stats = champions_manager.get_stats()
        
        # Print performance stats
        print(f"Experience Level: {champions_manager.experience_level}")
        print(f"Win Rate: {manager_stats['win_rate']:.1f}%")
        print(f"Draw Rate: {manager_stats['draw_rate']:.1f}%")
        print(f"Total Matches: {manager_stats['matches_played']}")
        print(f"Record: W{manager_stats['wins']}-D{manager_stats['draws']}-L{manager_stats['losses']}")
        
        # Print learning stats
        print("\nLearning Statistics:")
        print(f"Exploration Rate: {manager_stats['exploration_rate']:.2f}")
        print(f"Average Recent Reward: {manager_stats.get('average_reward', 0):.2f}")
        print(f"Transfer Success Rate: {manager_stats.get('transfer_success_rate', 0):.1f}%")
        
        # Print preferred formation and tactics
        if manager_stats.get('formation_preferences'):
            print(f"\nPreferred Formation: {manager_stats['formation_preferences'][0][0]}")
            
        # Print profile info
        print("\nManager Profile:")
        print(f"Short-term Focus: {champions_manager.profile.short_term_weight:.2f}")
        print(f"Long-term Focus: {champions_manager.profile.long_term_weight:.2f}")
        print(f"Risk Tolerance: {champions_manager.profile.risk_tolerance:.2f}")
        
        # Print team of the season
        print_best_xi(report['best_players'])
        
        # Save detailed report for each season
        report_filename = f'season_reports/season_report_{premier_league.season_year}.json'
        print(f"\nSaving detailed season {premier_league.season_year} report to '{report_filename}'...")
        with open(report_filename, 'w') as f:
            json.dump({
                'season': premier_league.season_year,
                'champions': champions_team,
                'champions_manager': {
                    'name': champions_manager.name,
                    'experience': champions_manager.experience_level,
                    'formation': manager_stats.get('formation_preferences', [])[0][0] if manager_stats.get('formation_preferences') else '4-4-2',
                    'transfer_success_rate': manager_stats.get('transfer_success_rate', 0),
                    'market_trends': manager_stats.get('market_trends', {})
                },
                'table': report['league_table'],
                'transfers': {
                    'total_transfers': sum(len(team.statistics['transfer_history']) for team in premier_league.teams),
                    'biggest_spenders': sorted(
                        [(team.name, sum(t['fee'] for t in team.statistics['transfer_history'] if t['type'] == 'purchase'))
                         for team in premier_league.teams],
                        key=lambda x: x[1], reverse=True
                    )[:5],
                    'most_active': sorted(
                        [(team.name, len(team.statistics['transfer_history']))
                         for team in premier_league.teams],
                        key=lambda x: x[1], reverse=True
                    )[:5]
                },
                'best_players': [
                    {
                        'name': p.name,
                        'position': p.position,
                        'team': p.team,
                        'potential': p.potential,
                        'age': p.age,
                        'value': premier_league.transfer_market.calculate_player_value(p) if hasattr(premier_league, 'transfer_market') else 0
                    }
                    for p in report['best_players']
                ]
            }, f, indent=2)
        
        # Increment to next season
        premier_league.increment_season()

if __name__ == "__main__":
    main()
