import sys
import os
from pathlib import Path

# Ensure project root and backend/src are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_SRC = Path(__file__).resolve().parent
for p in [str(PROJECT_ROOT), str(BACKEND_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from models.league import League
import json
import random
import shutil
import logging
from datetime import datetime, timedelta

from models.team import Team
from models.player import FootballPlayer
from models.manager import Manager
from models.transfer import TransferMarket
from config import NUM_SEASONS, REPORTS_DIR, ML_MODELS_DIR, ensure_report_directories
from database.db_setup import initialize_fresh_database
from database.match_db import save_match_to_db
from database.report_db import save_season_report_to_db, save_transfer_report_to_db

# Configure centralized logging
logger = logging.getLogger("footy.simulation")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def initialize_database():
    """Ensure database tables and report directories exist without destroying history."""
    logger.info("Verifying database infrastructure...")
    initialize_fresh_database()
    ensure_report_directories()
    logger.info("Database and directories ready!")

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
    
    logger.info("Creating Premier League teams with enhanced financial system...")
    
    from database.team_db import get_all_teams
    from database.player_db import get_all_players
    
    existing_teams = get_all_teams()
    existing_teams_map = {t[1]: t for t in existing_teams}
    all_db_players = get_all_players() if existing_teams else []

    for team_name in teams:
        if team_name in existing_teams_map:
            logger.info(f"Team '{team_name}' already exists in database, loading state...")
            team_info = existing_teams_map[team_name]
            team_id = team_info[0]
            team = Team.load_from_database(team_id)
            if team is None:
                team = Team(team_name, budgets.get(team_name, 100000000))
                team.save_to_database()

            # Load manager if exists
            manager_id = team_info[6]
            if manager_id:
                manager = Manager.load_from_database(manager_id)
                if manager:
                    team.set_manager(manager)

            if not team.manager:
                ml_model_name = os.environ.get("FOOTY_ACTIVE_ML_MODEL", "dqn_best.pt")
                model_path = ML_MODELS_DIR / ml_model_name
                has_dqn = os.path.exists(model_path)

                manager = Manager(profile=None, use_dqn=has_dqn)
                if has_dqn:
                    manager.brain.load_model(str(model_path))
                    logger.info(f"Loaded ML model: {ml_model_name} for {team_name}")

                manager.save_to_database()
                team.set_manager(manager)

            # Load players from DB for this team
            team_players_data = [p for p in all_db_players if p.get("team_id") == team_id]
            if team_players_data:
                team.players = []
                team.youth_academy = []
                for p_data in team_players_data:
                    player = FootballPlayer.load_from_database(p_data["player_id"])
                    if player:
                        if player.squad_role == "YOUTH":
                            team.youth_academy.append(player)
                        else:
                            team.add_player(player, force=True)

            # If squad is empty, generate squad
            if not team.players:
                for i in range(2):
                    gk = FootballPlayer.create_player(position="GK")
                    gk.squad_role = "STARTER" if i == 0 else "BENCH"
                    gk.save_to_database(team.team_id)
                    team.add_player(gk, force=True)

                positions_needed = {
                    "CB": 4, "LB": 2, "RB": 2,
                    "CDM": 2, "CM": 4, "CAM": 2,
                    "LW": 2, "RW": 2, "ST": 3
                }
                players_created = 0
                for position, count in positions_needed.items():
                    for i in range(count):
                        player = FootballPlayer.create_player(position=position)
                        if players_created < 11:
                            player.squad_role = "STARTER"
                        elif players_created < 18:
                            player.squad_role = "BENCH"
                        else:
                            player.squad_role = "RESERVE"
                        player.save_to_database(team.team_id)
                        team.add_player(player, force=True)
                        players_created += 1

                youth_count = random.randint(3, 6)
                for _ in range(youth_count):
                    youth_player = team.generate_youth_player()
                    youth_player.save_to_database(team.team_id)

            team.process_weekly_finances()
            premier_league.teams.append(team)
            continue
        team = Team(team_name, budgets[team_name])
        
        # Save team to database
        team.save_to_database()
        
        premier_league.teams.append(team)
        
        # Get correct dynamic ML model config. Falls back to dqn_best if not provided
        ml_model_name = os.environ.get("FOOTY_ACTIVE_ML_MODEL", "dqn_best.pt")
        model_path = ML_MODELS_DIR / ml_model_name
        has_dqn = os.path.exists(model_path)
        
        manager = Manager(profile=None, use_dqn=has_dqn)  # Will use random profile
        if has_dqn:
            manager.brain.load_model(str(model_path))
            logger.info(f"Loaded ML model: {ml_model_name} for {team_name}")
            
        manager.save_to_database()
        team.set_manager(manager)
        
        # Create goalkeeper squad
        goalkeepers = []
        for i in range(2):
            gk = FootballPlayer.create_player(position="GK")
            gk.squad_role = "STARTER" if i == 0 else "BENCH"
            gk.save_to_database(team.team_id)
            team.add_player(gk, force=True)
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
                team.add_player(player, force=True)
                players_created += 1
        
        # Generate initial youth academy players
        youth_count = random.randint(3, 6)
        for _ in range(youth_count):
            youth_player = team.generate_youth_player()
            youth_player.save_to_database(team.team_id)
        
        # Process initial weekly finances
        financial_summary = team.process_weekly_finances()
    
    return premier_league   

def print_league_table(table):
    """Print formatted league table with enhanced information"""
    logger.info("\nPremier League Final Standings")
    logger.info("=" * 85)
    logger.info(f"{'Pos':<4} {'Team':<20} {'Pld':<4} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<4} {'Pts':<4} {'Form':<6}")
    logger.info("-" * 85)
    
    for pos, (team, stats) in enumerate(table, 1):
        # Calculate recent form (last 5 games)
        recent_results = stats.get('recent_form', [])
        form_str = ''.join(recent_results[-5:]) if recent_results else "-----"
        
        logger.info(f"{pos:<4} {team:<20} {stats['played']:<4} {stats['won']:<3} {stats['drawn']:<3} {stats['lost']:<3} "
              f"{stats['gf']:<4} {stats['ga']:<4} {stats['gd']:<4} {stats['points']:<4} {form_str:<6}")

def print_financial_summary(teams):
    """Print financial summary for all teams"""
    logger.info("\nFinancial Summary")
    logger.info("=" * 100)
    logger.info(f"{'Team':<20} {'Budget':<12} {'Revenue':<12} {'Expenses':<12} {'Profit/Loss':<12} {'Health':<10}")
    logger.info("-" * 100)
    
    for team in teams:
        financials = team.get_financials()
        profit_loss = financials['annual_revenue'] - financials['annual_expenses']
        
        logger.info(f"{team.name:<20} £{team.budget/1000000:>8.1f}M £{financials['annual_revenue']/1000000:>8.1f}M "
              f"£{financials['annual_expenses']/1000000:>8.1f}M £{profit_loss/1000000:>+8.1f}M {financials['financial_health']:<10}")

def print_transfer_summary(transfer_market):
    """Print transfer window summary"""
    analysis = transfer_market.get_market_analysis()
    
    logger.info(f"\nTransfer Market Summary")
    logger.info("=" * 60)
    logger.info(f"Current Window: {analysis['current_window'] or 'CLOSED'}")
    logger.info(f"Transfer Listings: {analysis['total_listings']}")
    logger.info(f"Loan Listings: {analysis['loan_listings']}")
    logger.info(f"Free Agents: {analysis['free_agents']}")
    logger.info(f"Total Market Value: £{analysis['total_market_value']/1000000:.1f}M")
    logger.info(f"Transfers Completed: {analysis['transfers_completed']}")
    logger.info(f"Loans Completed: {analysis['loans_completed']}")
    
    if analysis['positions']:
        logger.info(f"\nMost Active Positions:")
        sorted_positions = sorted(analysis['positions'].items(), 
                                key=lambda x: x[1]['count'], reverse=True)[:5]
        for pos, data in sorted_positions:
            logger.info(f"  {pos}: {data['count']} players, Avg Value: £{data['average_value']/1000000:.1f}M")

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
        logger.info(f"\nCurrent Injury List ({len(all_injuries)} players)")
        logger.info("=" * 70)
        logger.info(f"{'Player':<20} {'Team':<15} {'Position':<8} {'Injury':<10} {'Days Out':<8}")
        logger.info("-" * 70)
        
        for injury in sorted(all_injuries, key=lambda x: x['recovery'], reverse=True):
            logger.info(f"{injury['player']:<20} {injury['team']:<15} {injury['position']:<8} "
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
    
    logger.info(f"\nTop Youth Prospects")
    logger.info("=" * 80)
    logger.info(f"{'Name':<20} {'Team':<15} {'Age':<4} {'Pos':<5} {'Current':<8} {'Potential':<9}")
    logger.info("-" * 80)
    
    for prospect in all_youth[:15]:  # Top 15
        logger.info(f"{prospect['name']:<20} {prospect['team']:<15} {prospect['age']:<4} "
              f"{prospect['position']:<5} {prospect['current_rating']:<8.1f} {prospect['potential']:<9}")

from database.session import get_db_session
from database.models import Team as DBTeam, Manager as DBManager, Player as DBPlayer

def sync_simulation_state_to_db(premier_league, transfer_market):
    """Fast batched sync of teams, managers, players, youth academy, and free agents to the database in a single transaction."""
    logger.info("Syncing simulation state to database...")
    try:
        with get_db_session() as db:
            existing_teams = {t.name: t for t in db.query(DBTeam).all()}
            existing_managers = {m.name: m for m in db.query(DBManager).all()}
            existing_players = {p.name: p for p in db.query(DBPlayer).all()}

            for team in premier_league.teams:
                # 1. Team sync
                db_team = existing_teams.get(team.name)
                if db_team:
                    db_team.budget = team.budget
                    db_team.wage_budget = team.wage_budget
                    db_team.transfer_budget = team.transfer_budget
                    db_team.weekly_budget = team.weekly_budget
                    team.team_id = db_team.team_id
                else:
                    db_team = DBTeam(
                        name=team.name,
                        budget=team.budget,
                        weekly_budget=team.weekly_budget,
                        transfer_budget=team.transfer_budget,
                        wage_budget=team.wage_budget,
                    )
                    db.add(db_team)
                    db.flush()
                    team.team_id = db_team.team_id
                    existing_teams[team.name] = db_team

                # 2. Manager sync
                if team.manager:
                    db_mgr = existing_managers.get(team.manager.name)
                    if db_mgr:
                        db_mgr.team_id = team.team_id
                        db_mgr.formation = team.manager.formation
                        db_mgr.matches_played = getattr(team.manager, "matches_played", 0)
                        db_mgr.wins = getattr(team.manager, "wins", 0)
                        db_mgr.draws = getattr(team.manager, "draws", 0)
                        db_mgr.losses = getattr(team.manager, "losses", 0)
                        db_mgr.total_rewards = getattr(team.manager, "total_rewards", 0.0)
                        team.manager.manager_id = db_mgr.manager_id
                    else:
                        db_mgr = DBManager(
                            name=team.manager.name,
                            experience_level=getattr(team.manager, "experience_level", 5),
                            team_id=team.team_id,
                            formation=team.manager.formation,
                            matches_played=getattr(team.manager, "matches_played", 0),
                            wins=getattr(team.manager, "wins", 0),
                            draws=getattr(team.manager, "draws", 0),
                            losses=getattr(team.manager, "losses", 0),
                            total_rewards=getattr(team.manager, "total_rewards", 0.0),
                        )
                        db.add(db_mgr)
                        db.flush()
                        team.manager.manager_id = db_mgr.manager_id
                        existing_managers[team.manager.name] = db_mgr
                    db_team.manager_id = db_mgr.manager_id

                # 3. Squad Players sync
                for player in team.players:
                    db_p = existing_players.get(player.name)
                    if db_p:
                        db_p.team_id = team.team_id
                        db_p.age = player.age
                        db_p.position = player.position
                        db_p.potential = player.potential
                        db_p.wage = player.wage
                        db_p.contract_length = player.contract_length
                        db_p.squad_role = player.squad_role
                        player.player_id = db_p.player_id
                    else:
                        db_p = DBPlayer(
                            name=player.name,
                            age=player.age,
                            position=player.position,
                            team_id=team.team_id,
                            potential=player.potential,
                            wage=player.wage,
                            contract_length=player.contract_length,
                            squad_role=player.squad_role,
                        )
                        db.add(db_p)
                        db.flush()
                        player.player_id = db_p.player_id
                        existing_players[player.name] = db_p

                # 4. Youth Academy sync
                for player in team.youth_academy:
                    db_p = existing_players.get(player.name)
                    if db_p:
                        db_p.team_id = team.team_id
                        db_p.squad_role = "YOUTH"
                        player.player_id = db_p.player_id
                    else:
                        db_p = DBPlayer(
                            name=player.name,
                            age=player.age,
                            position=player.position,
                            team_id=team.team_id,
                            potential=player.potential,
                            wage=player.wage,
                            contract_length=player.contract_length,
                            squad_role="YOUTH",
                        )
                        db.add(db_p)
                        db.flush()
                        player.player_id = db_p.player_id
                        existing_players[player.name] = db_p

            # 5. Free Agents sync
            for player in transfer_market.free_agents:
                db_p = existing_players.get(player.name)
                if db_p:
                    db_p.team_id = None
                    player.player_id = db_p.player_id
                else:
                    db_p = DBPlayer(
                        name=player.name,
                        age=player.age,
                        position=player.position,
                        team_id=None,
                        potential=player.potential,
                        wage=player.wage,
                        contract_length=player.contract_length,
                        squad_role="RESERVE",
                    )
                    db.add(db_p)
                    db.flush()
                    player.player_id = db_p.player_id
                    existing_players[player.name] = db_p
        logger.info("Database sync complete.")

        # Immediately save live season report so frontend displays current standings in real time
        save_live_season_report(premier_league, transfer_market)
    except Exception as e:
        logger.warning(f"Error during batched database sync: {e}")


def save_live_season_report(premier_league, transfer_market):
    try:
        report_filename = REPORTS_DIR / 'season_reports' / f'season_report_{premier_league.season_year}.json'
        table = premier_league.get_final_table()
        champions_name = table[0][0] if table else "TBD"

        all_teams_details = []
        for team in premier_league.teams:
            all_teams_details.append({
                "id": team.team_id,
                "name": team.name,
                "budget": team.budget,
                "manager_name": team.manager.name if team.manager else "N/A",
                "manager_formation": team.manager.formation if team.manager else "4-3-3",
                "players_count": len(team.players),
            })

        best_p = []
        if hasattr(premier_league, "get_best_players"):
            try:
                best_p = premier_league.get_best_players(11)
            except Exception:
                best_p = []

        live_report = {
            "season_year": premier_league.season_year,
            "champions": champions_name,
            "champions_manager": premier_league.teams[0].manager.get_stats() if (premier_league.teams and premier_league.teams[0].manager and hasattr(premier_league.teams[0].manager, "get_stats")) else {},
            "table": table,
            "transfers": transfer_market.get_market_analysis() if transfer_market else {},
            "best_players": best_p,
            "season_stats": {
                "total_matches": sum(stats.get("played", 0) for _, stats in table) // 2 if table else 0,
                "total_goals": sum(stats.get("gf", 0) for _, stats in table) if table else 0,
                "average_goals_per_match": round(sum(stats.get("gf", 0) for _, stats in table) / max(1, sum(stats.get("played", 0) for _, stats in table) // 2), 2) if table else 0,
                "best_attack": [table[0][0], {"gf": table[0][1].get("gf", 0)}] if table else ["N/A", {"gf": 0}],
                "best_defense": [table[0][0], {"ga": table[0][1].get("ga", 0)}] if table else ["N/A", {"ga": 0}],
            },
            "all_teams_details": all_teams_details,
            "financial_summary": [team.get_financials() for team in premier_league.teams],
            "transfer_summary": transfer_market.get_market_analysis() if transfer_market else {},
        }

        save_season_report_to_db(premier_league.season_year, champions_name, live_report)
    except Exception as e:
        logger.warning(f"Live season report DB save notice: {e}")

def simulate_season_with_transfers(premier_league, transfer_market):
    """Simulate a season with active transfer market"""
    logger.info(f"\nSeason {premier_league.season_year} - Starting with Transfer Windows")
    
    # Summer transfer window (days 1-61)
    logger.info("\n=== SUMMER TRANSFER WINDOW OPEN ===")
    for day in range(1, 62):
        transfer_market.advance_day(premier_league.teams)
        
        # AI transfer activity (every 3 days)
        if day % 3 == 0:
            # AI managers act on their scouting lists
            transfer_market.simulate_ai_transfers(premier_league.teams)
        
        # Print progress every 20 days
        if day % 20 == 0:
            analysis = transfer_market.get_market_analysis()
            logger.info(f"Day {day}: {analysis['transfers_completed']} transfers completed, "
                  f"{analysis['total_listings']} active listings")
    
    logger.info("=== SUMMER TRANSFER WINDOW CLOSED ===")
    print_transfer_summary(transfer_market)
    sync_simulation_state_to_db(premier_league, transfer_market)
    
    # Generate schedule and play first half of season
    premier_league.generate_schedule()
    
    # Play matches until January (concurrent multi-process matchdays)
    matches_played = 0
    total_matches = len(premier_league.schedule)
    recorded_match_ids = set()
    january_start = total_matches // 2
    matches_per_week = max(1, len(premier_league.teams) // 2)
    chunk_size = matches_per_week * 2  # 2 matchdays = 20 matches concurrently

    logger.info(f"\nPlaying first half of season ({january_start} matches)...")
    for start_idx in range(0, january_start, chunk_size):
        end_idx = min(start_idx + chunk_size, january_start)
        matchday_batches = []
        for m_start in range(start_idx, end_idx, matches_per_week):
            m_end = min(m_start + matches_per_week, end_idx)
            matchday_batches.append(premier_league.schedule[m_start:m_end])

        all_batch_results = premier_league.play_matchdays_concurrent(matchday_batches, max_workers=2)

        for md_offset, (batch, batch_results) in enumerate(zip(matchday_batches, all_batch_results)):
            curr_start = start_idx + md_offset * matches_per_week
            matchday = curr_start // matches_per_week
            season_start = datetime(premier_league.season_year, 8, 1)
            scheduled_date = season_start + timedelta(days=7 * matchday)

            for idx_in_batch, match_result in enumerate(batch_results):
                match_global_idx = curr_start + idx_in_batch
                if match_result is not None:
                    match_result['date'] = scheduled_date.isoformat()
                    recorded_match_ids.add(str(match_result.get("match_id", match_global_idx)))
                save_match_to_db(match_result, premier_league.season_year, match_global_idx + 1)
                matches_played += 1

                home_team, away_team = batch[idx_in_batch]
                if match_result:
                    attendance_factor = 1.0 if match_result['score'][0] >= match_result['score'][1] else 0.9
                    home_team.calculate_matchday_revenue(attendance_factor)

            for team in premier_league.teams:
                team.process_weekly_finances()
                if matches_played % 10 == 0:
                    if team.manager:
                        team.manager.scout_for_talent(premier_league.teams, transfer_market)
                    team.check_and_reinforce_squad(transfer_market)
                    for player in team.players + team.youth_academy:
                        if random.random() < 0.02:
                            player.apply_age_decline()
                        if hasattr(player, 'recover_from_injury'):
                            player.recover_from_injury(7)

            # Instantly sync updated league standings, team records, and player stats after every matchday
            sync_simulation_state_to_db(premier_league, transfer_market)

    # January transfer window (days 183-214)
    logger.info("\n=== JANUARY TRANSFER WINDOW OPEN ===")
    transfer_market.current_day = 183

    for day in range(183, 215):
        transfer_market.advance_day(premier_league.teams)

        # More active January window
        if day % 2 == 0:
            # AI managers act on their scouting lists
            transfer_market.simulate_ai_transfers(premier_league.teams)

        if day % 10 == 0:
            analysis = transfer_market.get_market_analysis()
            logger.info(f"Day {day}: {analysis['transfers_completed']} total transfers, "
                  f"{analysis['total_listings']} active listings")

    logger.info("=== JANUARY TRANSFER WINDOW CLOSED ===")
    print_transfer_summary(transfer_market)
    sync_simulation_state_to_db(premier_league, transfer_market)

    # Play remaining matches
    logger.info(f"\nPlaying second half of season...")
    for start_idx in range(january_start, total_matches, chunk_size):
        end_idx = min(start_idx + chunk_size, total_matches)
        matchday_batches = []
        for m_start in range(start_idx, end_idx, matches_per_week):
            m_end = min(m_start + matches_per_week, end_idx)
            matchday_batches.append(premier_league.schedule[m_start:m_end])

        all_batch_results = premier_league.play_matchdays_concurrent(matchday_batches, max_workers=2)

        for md_offset, (batch, batch_results) in enumerate(zip(matchday_batches, all_batch_results)):
            curr_start = start_idx + md_offset * matches_per_week
            matchday = curr_start // matches_per_week
            season_start = datetime(premier_league.season_year, 8, 1)
            scheduled_date = season_start + timedelta(days=7 * matchday)

            for idx_in_batch, match_result in enumerate(batch_results):
                match_global_idx = curr_start + idx_in_batch
                if match_result is not None:
                    match_result['date'] = scheduled_date.isoformat()
                    recorded_match_ids.add(str(match_result.get("match_id", match_global_idx)))
                save_match_to_db(match_result, premier_league.season_year, match_global_idx + 1)
                matches_played += 1

                home_team, away_team = batch[idx_in_batch]
                if match_result:
                    attendance_factor = 1.0 if match_result['score'][0] >= match_result['score'][1] else 0.9
                    home_team.calculate_matchday_revenue(attendance_factor)

            for team in premier_league.teams:
                team.process_weekly_finances()
                if matches_played % 10 == 0:
                    if team.manager:
                        team.manager.scout_for_talent(premier_league.teams, transfer_market)

            # Instantly sync updated league standings, team records, and player stats after every matchday
            sync_simulation_state_to_db(premier_league, transfer_market)

    # Assert season fixture completeness and uniqueness
    if matches_played != total_matches:
        raise RuntimeError(
            f"Season simulation incomplete for {premier_league.season_year}: "
            f"played {matches_played}/{total_matches} expected fixtures."
        )
    if len(recorded_match_ids) != total_matches:
        raise RuntimeError(
            f"Season simulation duplicate fixture detected for {premier_league.season_year}: "
            f"recorded {len(recorded_match_ids)} unique match IDs out of {total_matches} expected."
        )

    # Process contract expiries at end of season
    expired_contracts = transfer_market.process_contract_expiries(premier_league.teams)
    if expired_contracts > 0:
        logger.info(f"\n{expired_contracts} players' contracts expired and became free agents")

    sync_simulation_state_to_db(premier_league, transfer_market)
    
    return premier_league.get_final_table()

def main():
    """Enhanced main function with comprehensive simulation"""
    # Initialize database with fresh start
    initialize_database()

    ensure_report_directories()

    num_seasons = int(os.environ.get("FOOTY_NUM_SEASONS", str(NUM_SEASONS)))
    
    # Create league and transfer market
    premier_league = create_premier_league()
    transfer_market = TransferMarket()
    
    logger.info(f"\nInitial Financial Overview:")
    print_financial_summary(premier_league.teams)
    
    for season in range(num_seasons):
        logger.info(f"\n{'='*60}")
        logger.info(f"SEASON {premier_league.season_year}")
        logger.info(f"{'='*60}")
        
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
        logger.info(f"\n Premier League Champions: {champions_name}!")
        
        champion_manager_details = full_season_report['champions_manager']
        logger.info(f"\n Manager of the Season: {champion_manager_details['name']} ({champions_name})")
        logger.info(f"   Experience Level: {champion_manager_details['experience']}")
        logger.info(f"   Formation: {champion_manager_details['formation']}")
        logger.info(f"   Transfer Success Rate: {champion_manager_details['transfer_success_rate']:.1f}%")
        
        # Print team of the season
        logger.info(f"\n Premier League Team of the Season")
        logger.info("=" * 85)
        logger.info(f"{'Position':<8} {'Name':<20} {'Team':<15} {'Age':<4} {'Rating':<7} {'Value':<10}")
        logger.info("-" * 85)
        
        for player_data in full_season_report['best_players']:
            rating = 0
            if "attributes" in player_data and player_data["attributes"]:
                try:
                    rating = sum(sum(cat.values()) for cat in player_data["attributes"].values()) / \
                           sum(len(cat) for cat in player_data["attributes"].values())
                except Exception:
                    rating = 0
            
            logger.info(f"{player_data.get('position', 'N/A'):<8} {player_data.get('name', 'N/A'):<20} "
                  f"{player_data.get('team', 'N/A'):<15} {player_data.get('age', 0):<4} "
                  f"{rating:<7.1f} £{player_data.get('value', 0)/1000000:<8.1f}M")
        
        # Additional reports
        print_financial_summary(premier_league.teams)
        print_injury_report(premier_league.teams)
        print_youth_prospects(premier_league.teams)
        
        # Save comprehensive season report to file and DB
        report_filename = REPORTS_DIR / 'season_reports' / f'season_report_{premier_league.season_year}.json'
        logger.info(f"\n Saving detailed season {premier_league.season_year} report to '{report_filename}' and database...")

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

        save_season_report_to_db(premier_league.season_year, champions_name, enhanced_report)

        transfer_report_data = {
            "season": premier_league.season_year,
            "analysis": transfer_market.get_market_analysis(),
            "transfer_history": transfer_market.transfer_history,
            "loan_history": transfer_market.loan_history
        }
        save_transfer_report_to_db(premier_league.season_year, transfer_report_data)

        # Increment to next season
        premier_league.increment_season()
        transfer_market.season_year = premier_league.season_year
        
        logger.info(f"\n Season {premier_league.season_year - 1} completed successfully!")

if __name__ == "__main__":
    main()
