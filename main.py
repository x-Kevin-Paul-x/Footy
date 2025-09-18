from league import League
import json
import os
import random
from datetime import datetime, timedelta

from team import Team
from player import FootballPlayer
from manager import Manager
from transfer import TransferMarket
from db_setup import initialize_fresh_database
from match_db import save_match_to_db

def initialize_database():
    """Initialize the database with fresh start - clear all data"""
    print("Initializing database...")
    initialize_fresh_database()
    # Clean up old report files so previous runs do not appear in the UI
    import shutil
    for d in ("match_reports", "season_reports", "transfer_logs"):
        if os.path.exists(d):
            for fname in os.listdir(d):
                fpath = os.path.join(d, fname)
                try:
                    if os.path.isfile(fpath) or os.path.islink(fpath):
                        os.remove(fpath)
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                except Exception as e:
                    print(f"Warning: failed to remove {fpath}: {e}")
    print("Database initialized successfully!")

def create_premier_league():
    """Create Premier League with 20 teams and enhanced realism"""
    teams = [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool",
        "Luton", "Manchester City", "Manchester United", "Newcastle",
        "Nottingham Forest", "Sheffield United", "Tottenham", "West Ham",
        "Wolves", "Burnley"
    ]
    
    # More realistic budgets based on actual Premier League finances
    budgets = {
        "Manchester City": 650000000,
        "Manchester United": 580000000,
        "Chelsea": 550000000,
        "Arsenal": 450000000,
        "Liverpool": 450000000,
        "Tottenham": 350000000,
        "Newcastle": 300000000,
        "West Ham": 250000000,
        "Aston Villa": 220000000,
        "Brighton": 180000000,
        "Crystal Palace": 170000000,
        "Wolves": 160000000,
        "Fulham": 150000000,
        "Brentford": 140000000,
        "Bournemouth": 130000000,
        "Everton": 180000000,
        "Nottingham Forest": 120000000,
        "Burnley": 110000000,
        "Sheffield United": 100000000,
        "Luton": 95000000
    }
    
    premier_league = League("Premier League")
    premier_league.teams = []  # Clear default teams
    
    print("Creating Premier League teams with enhanced financial system...")
    
    from team_db import get_all_teams
    existing_team_names = set(t[1] for t in get_all_teams())
    for team_name in teams:
        if team_name in existing_team_names:
            print(f"Team '{team_name}' already exists in database, skipping creation.")
            continue
        team = Team(team_name, budgets[team_name])
        
        # Save team to database
        team.save_to_database()
        
        premier_league.teams.append(team)
        
        # Create and assign manager with profile
        manager = Manager(profile=None)  # Will use random profile
        manager.save_to_database()
        team.set_manager(manager)
        
        #print(f"\nCreating {team_name} squad:")
        #print(f"  Budget: £{team.budget:,.0f}")
        #print(f"  Stadium: {team.stadium_name} (Capacity: {team.stadium_capacity:,})")
        #print(f"  TV Revenue: £{team.tv_revenue:,.0f}")
        #print(f"  Sponsorship Deals: {len(team.sponsorship_deals)}")
        
        # Create goalkeeper squad
        goalkeepers = []
        for i in range(2):
            gk = FootballPlayer.create_player(position="GK")
            gk.squad_role = "STARTER" if i == 0 else "BENCH"
            gk.save_to_database(team.team_id)
            team.add_player(gk)
            goalkeepers.append(gk)
        
        # Create balanced outfield squad with realistic roles
        positions_needed = {
            "CB": 4, "LB": 2, "RB": 2,  # 8 defenders
            "CDM": 2, "CM": 4, "CAM": 2,  # 8 midfielders  
            "LW": 2, "RW": 2, "ST": 3   # 7 forwards
        }
        
        players_created = 0
        for position, count in positions_needed.items():
            for i in range(count):
                player = FootballPlayer.create_player(position=position)
                
                # Assign squad roles realistically
                if players_created < 11:
                    player.squad_role = "STARTER"
                elif players_created < 18:
                    player.squad_role = "BENCH"
                else:
                    player.squad_role = "RESERVE"
                
                # Save player to database
                player.save_to_database(team.team_id)
                team.add_player(player)
                players_created += 1
        
        # Generate initial youth academy players
        youth_count = random.randint(3, 6)
        for _ in range(youth_count):
            youth_player = team.generate_youth_player()
            youth_player.save_to_database(team.team_id)
        
        #print(f"  Squad: {len(team.players)} senior players, {len(team.youth_academy)} youth")
        #print(f"  Average Squad Rating: {team.get_squad_strength():.1f}")
        
        # Process initial weekly finances
        financial_summary = team.process_weekly_finances()
        #print(f"  Weekly Finances: Revenue £{financial_summary['revenue']:,.0f}, "
        #      f"Expenses £{financial_summary['expenses']:,.0f}, "
        #      f"Net £{financial_summary['net']:,.0f}")
    
    return premier_league   

def print_league_table(table):
    """Print formatted league table with enhanced information"""
    print("\nPremier League Final Standings")
    print("=" * 85)
    print(f"{'Pos':<4} {'Team':<20} {'Pld':<4} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<4} {'Pts':<4} {'Form':<6}")
    print("-" * 85)
    
    for pos, (team, stats) in enumerate(table, 1):
        # Calculate recent form (last 5 games)
        recent_results = stats.get('recent_form', [])
        form_str = ''.join(recent_results[-5:]) if recent_results else "-----"
        
        print(f"{pos:<4} {team:<20} {stats['played']:<4} {stats['won']:<3} {stats['drawn']:<3} {stats['lost']:<3} "
              f"{stats['gf']:<4} {stats['ga']:<4} {stats['gd']:<4} {stats['points']:<4} {form_str:<6}")

def print_financial_summary(teams):
    """Print financial summary for all teams"""
    print("\nFinancial Summary")
    print("=" * 100)
    print(f"{'Team':<20} {'Budget':<12} {'Revenue':<12} {'Expenses':<12} {'Profit/Loss':<12} {'Health':<10}")
    print("-" * 100)
    
    for team in teams:
        financials = team.get_financials()
        profit_loss = financials['annual_revenue'] - financials['annual_expenses']
        
        print(f"{team.name:<20} £{team.budget/1000000:>8.1f}M £{financials['annual_revenue']/1000000:>8.1f}M "
              f"£{financials['annual_expenses']/1000000:>8.1f}M £{profit_loss/1000000:>+8.1f}M {financials['financial_health']:<10}")

def print_transfer_summary(transfer_market):
    """Print transfer window summary"""
    analysis = transfer_market.get_market_analysis()
    
    print(f"\nTransfer Market Summary")
    print("=" * 60)
    print(f"Current Window: {analysis['current_window'] or 'CLOSED'}")
    print(f"Transfer Listings: {analysis['total_listings']}")
    print(f"Loan Listings: {analysis['loan_listings']}")
    print(f"Free Agents: {analysis['free_agents']}")
    print(f"Total Market Value: £{analysis['total_market_value']/1000000:.1f}M")
    print(f"Transfers Completed: {analysis['transfers_completed']}")
    print(f"Loans Completed: {analysis['loans_completed']}")
    
    if analysis['positions']:
        print(f"\nMost Active Positions:")
        sorted_positions = sorted(analysis['positions'].items(), 
                                key=lambda x: x[1]['count'], reverse=True)[:5]
        for pos, data in sorted_positions:
            print(f"  {pos}: {data['count']} players, Avg Value: £{data['average_value']/1000000:.1f}M")

def print_injury_report(teams):
    """Print injury report across all teams"""
    all_injuries = []
    for team in teams:
        for player in team.players:
            if hasattr(player, 'is_injured') and player.is_injured:
                all_injuries.append({
                    'player': player.name,
                    'team': team.name,
                    'injury': getattr(player, 'injury_type', 'Unknown'),
                    'recovery': getattr(player, 'recovery_time', 0),
                    'position': player.position
                })
    
    if all_injuries:
        print(f"\nCurrent Injury List ({len(all_injuries)} players)")
        print("=" * 70)
        print(f"{'Player':<20} {'Team':<15} {'Position':<8} {'Injury':<10} {'Days Out':<8}")
        print("-" * 70)
        
        for injury in sorted(all_injuries, key=lambda x: x['recovery'], reverse=True):
            print(f"{injury['player']:<20} {injury['team']:<15} {injury['position']:<8} "
                  f"{injury['injury']:<10} {injury['recovery']:<8}")

def print_youth_prospects(teams):
    """Print best youth academy prospects"""
    all_youth = []
    for team in teams:
        for player in team.youth_academy:
            all_youth.append({
                'name': player.name,
                'team': team.name,
                'age': player.age,
                'position': player.position,
                'potential': player.potential,
                'current_rating': player.get_overall_rating()
            })
    
    # Sort by potential and current rating
    all_youth.sort(key=lambda x: (x['potential'], x['current_rating']), reverse=True)
    
    print(f"\nTop Youth Prospects")
    print("=" * 80)
    print(f"{'Name':<20} {'Team':<15} {'Age':<4} {'Pos':<5} {'Current':<8} {'Potential':<9}")
    print("-" * 80)
    
    for prospect in all_youth[:15]:  # Top 15
        print(f"{prospect['name']:<20} {prospect['team']:<15} {prospect['age']:<4} "
              f"{prospect['position']:<5} {prospect['current_rating']:<8.1f} {prospect['potential']:<9}")

def simulate_season_with_transfers(premier_league, transfer_market):
    """Simulate a season with active transfer market"""
    print(f"\nSeason {premier_league.season_year} - Starting with Transfer Windows")
    
    # Summer transfer window (days 1-61)
    print("\n=== SUMMER TRANSFER WINDOW OPEN ===")
    for day in range(1, 62):
        transfer_market.advance_day(premier_league.teams)
        
        # AI transfer activity (every 3 days)
        if day % 3 == 0:
            # AI managers act on their scouting lists
            transfer_market.simulate_ai_transfers(premier_league.teams)
        
        # Print progress every 20 days
        if day % 20 == 0:
            analysis = transfer_market.get_market_analysis()
            print(f"Day {day}: {analysis['transfers_completed']} transfers completed, "
                  f"{analysis['total_listings']} active listings")
    
    print("=== SUMMER TRANSFER WINDOW CLOSED ===")
    print_transfer_summary(transfer_market)
    
    # Generate schedule and play first half of season
    premier_league.generate_schedule()
    
    # Play matches until January
    matches_played = 0
    total_matches = len(premier_league.schedule)
    january_start = total_matches // 2
    
    print(f"\nPlaying first half of season ({january_start} matches)...")
    # Compute scheduling helpers
    for i in range(january_start):
        match = premier_league.schedule[i]
        match_result = premier_league.play_match(match[0], match[1])
        # Assign scheduled date consistent with League.play_season
        season_start = datetime(premier_league.season_year, 8, 1)
        matches_per_week = max(1, len(premier_league.teams) // 2)
        matchday = i // matches_per_week
        scheduled_date = season_start + timedelta(days=7 * matchday)
        if match_result is not None:
            match_result['date'] = scheduled_date.isoformat()
        save_match_to_db(match_result, premier_league.season_year, i + 1)
        matches_played += 1
        
        # Process weekly finances for teams
        if matches_played % 2 == 0:  # Every 2 matches = roughly 1 week
            for team in premier_league.teams:
                # Calculate matchday revenue
                if match_result:
                    home_team = match[0]
                    away_team = match[1]
                    
                    if team == home_team:
                        attendance_factor = 1.0 if match_result['score'][0] >= match_result['score'][1] else 0.9
                        team.calculate_matchday_revenue(attendance_factor)
                    
                team.process_weekly_finances()
        
        # Age players and apply decline
        if matches_played % 10 == 0:  # Every 10 matches
            for team in premier_league.teams:
                # Manager scouts for talent
                if team.manager:
                    team.manager.scout_for_talent(premier_league.teams, transfer_market)

                # Check and reinforce squad if necessary
                team.check_and_reinforce_squad(transfer_market)
                
                for player in team.players + team.youth_academy:
                    if random.random() < 0.02:  # 2% chance per period
                        player.apply_age_decline()
                    
                    # Process injury recovery
                    if hasattr(player, 'recover_from_injury'):
                        player.recover_from_injury(7)  # 1 week recovery
    
    # January transfer window (days 183-214)
    print("\n=== JANUARY TRANSFER WINDOW OPEN ===")
    transfer_market.current_day = 183
    
    for day in range(183, 215):
        transfer_market.advance_day(premier_league.teams)
        
        # More active January window
        if day % 2 == 0:
            # AI managers act on their scouting lists
            transfer_market.simulate_ai_transfers(premier_league.teams)
        
        if day % 10 == 0:
            analysis = transfer_market.get_market_analysis()
            print(f"Day {day}: {analysis['transfers_completed']} total transfers, "
                  f"{analysis['total_listings']} active listings")
    
    print("=== JANUARY TRANSFER WINDOW CLOSED ===")
    print_transfer_summary(transfer_market)
    
    # Play remaining matches
    print(f"\nPlaying second half of season...")
    # Compute scheduling helpers
    for i in range(january_start, total_matches):
        match = premier_league.schedule[i]
        match_result = premier_league.play_match(match[0], match[1])
        # Assign scheduled date consistent with League.play_season
        season_start = datetime(premier_league.season_year, 8, 1)
        matches_per_week = max(1, len(premier_league.teams) // 2)
        matchday = i // matches_per_week
        scheduled_date = season_start + timedelta(days=7 * matchday)
        if match_result is not None:
            match_result['date'] = scheduled_date.isoformat()
        save_match_to_db(match_result, premier_league.season_year, i + 1)
        matches_played += 1
        
        # Continue financial processing
        if matches_played % 2 == 0:
            for team in premier_league.teams:
                if team == match[0]:  # Home team
                    attendance_factor = 1.0 if match_result['score'][0] >= match_result['score'][1] else 0.9
                    team.calculate_matchday_revenue(attendance_factor)
                
                team.process_weekly_finances()

        if matches_played % 10 == 0:
             for team in premier_league.teams:
                # Manager scouts for talent
                if team.manager:
                    team.manager.scout_for_talent(premier_league.teams, transfer_market)
    
    # Process contract expiries at end of season
    expired_contracts = transfer_market.process_contract_expiries(premier_league.teams)
    if expired_contracts > 0:
        print(f"\n{expired_contracts} players' contracts expired and became free agents")
    
    return premier_league.get_final_table()

def main():
    """Enhanced main function with comprehensive simulation"""
    # Initialize database with fresh start
    initialize_database()
    
    # Create directories for reports
    os.makedirs("season_reports", exist_ok=True)
    os.makedirs("transfer_logs", exist_ok=True)
    os.makedirs("match_reports", exist_ok=True)
    
    num_seasons = 2
    
    # Create league and transfer market
    premier_league = create_premier_league()
    transfer_market = TransferMarket()
    
    print(f"\nInitial Financial Overview:")
    print_financial_summary(premier_league.teams)
    
    for season in range(num_seasons):
        print(f"\n{'='*60}")
        print(f"SEASON {premier_league.season_year}")
        print(f"{'='*60}")
        
        # Simulate season with transfer activity
        transfer_market.season_year = premier_league.season_year
        transfer_market._init_transfer_log()
        final_table = simulate_season_with_transfers(premier_league, transfer_market)
        
        # Generate comprehensive season report
        full_season_report = premier_league.generate_season_report()
        
        # Print results
        print_league_table(full_season_report['table'])
        
        # Enhanced reporting
        champions_name = full_season_report['champions']
        print(f"\n Premier League Champions: {champions_name}!")
        
        champion_manager_details = full_season_report['champions_manager']
        print(f"\n Manager of the Season: {champion_manager_details['name']} ({champions_name})")
        print(f"   Experience Level: {champion_manager_details['experience']}")
        print(f"   Formation: {champion_manager_details['formation']}")
        print(f"   Transfer Success Rate: {champion_manager_details['transfer_success_rate']:.1f}%")
        
        # Print team of the season
        print(f"\n Premier League Team of the Season")
        print("=" * 85)
        print(f"{'Position':<8} {'Name':<20} {'Team':<15} {'Age':<4} {'Rating':<7} {'Value':<10}")
        print("-" * 85)
        
        for player_data in full_season_report['best_players']:
            rating = 0
            if "attributes" in player_data and player_data["attributes"]:
                try:
                    rating = sum(sum(cat.values()) for cat in player_data["attributes"].values()) / \
                           sum(len(cat) for cat in player_data["attributes"].values())
                except:
                    rating = 0
            
            print(f"{player_data.get('position', 'N/A'):<8} {player_data.get('name', 'N/A'):<20} "
                  f"{player_data.get('team', 'N/A'):<15} {player_data.get('age', 0):<4} "
                  f"{rating:<7.1f} £{player_data.get('value', 0)/1000000:<8.1f}M")
        
        # Additional reports
        print_financial_summary(premier_league.teams)
        print_injury_report(premier_league.teams)
        print_youth_prospects(premier_league.teams)
        
        # Save comprehensive season report
        report_filename = f'season_reports/season_report_{premier_league.season_year}.json'
        print(f"\n Saving detailed season {premier_league.season_year} report to '{report_filename}'...")
        
        # Enhanced report with financial data
        enhanced_report = {
            **full_season_report,
            "financial_summary": [team.get_financials() for team in premier_league.teams],
            "transfer_summary": transfer_market.get_market_analysis(),
            "injury_summary": {
                "total_injuries": sum(1 for team in premier_league.teams 
                                    for player in team.players if hasattr(player, 'is_injured') and player.is_injured),
                "injury_types": {}
            },
            "youth_development": {
                "total_youth": sum(len(team.youth_academy) for team in premier_league.teams),
                "promotions": 0  # Would track this in a full implementation
            }
        }
        
        with open(report_filename, 'w') as f:
            json.dump(enhanced_report, f, indent=2, default=str)
        
        # Save transfer market data
        transfer_filename = f'transfer_logs/transfer_summary_{premier_league.season_year}.json'
        with open(transfer_filename, 'w') as f:
            json.dump({
                "season": premier_league.season_year,
                "analysis": transfer_market.get_market_analysis(),
                "transfer_history": transfer_market.transfer_history,
                "loan_history": transfer_market.loan_history
            }, f, indent=2, default=str)
        
        # Increment to next season
        premier_league.increment_season()
        transfer_market.season_year = premier_league.season_year
        
        print(f"\n Season {premier_league.season_year - 1} completed successfully!")

if __name__ == "__main__":
    main()
