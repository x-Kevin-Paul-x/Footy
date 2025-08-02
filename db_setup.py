import sqlite3

DB_FILE = "football_sim.db"

def create_tables(db_file=DB_FILE):
    """Create all database tables."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # League Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS League (
            league_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            season_year INTEGER NOT NULL
        )
    """)

    # LeagueTeams Table (Many-to-Many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS LeagueTeams (
            league_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            FOREIGN KEY (league_id) REFERENCES League(league_id),
            FOREIGN KEY (team_id) REFERENCES Team(team_id),
            PRIMARY KEY (league_id, team_id, season_year)
        )
    """)

    # Team Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Team (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            budget REAL NOT NULL,
            weekly_budget REAL NOT NULL,
            transfer_budget REAL NOT NULL,
            wage_budget REAL NOT NULL,
            manager_id INTEGER,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)
    
    # TeamStatistics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamStatistics (
            team_id INTEGER PRIMARY KEY,
            wins INTEGER NOT NULL,
            draws INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            goals_for INTEGER NOT NULL,
            goals_against INTEGER NOT NULL,
            FOREIGN KEY (team_id) REFERENCES Team(team_id)
        )
    """)


    # Manager Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Manager (
            manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            experience_level INTEGER NOT NULL,
            team_id INTEGER,
            profile_id INTEGER,
            transfers_made INTEGER NOT NULL,
            successful_transfers INTEGER NOT NULL,
            formation TEXT NOT NULL,
            matches_played INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            draws INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            total_rewards REAL NOT NULL,
            FOREIGN KEY (team_id) REFERENCES Team(team_id),
            FOREIGN KEY (profile_id) REFERENCES ManagerProfile(profile_id)
        )
    """)

    # ManagerTactics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerTactics (
            manager_id INTEGER PRIMARY KEY,
            offensive INTEGER NOT NULL,
            defensive INTEGER NOT NULL,
            pressure INTEGER NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerProfile Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerProfile (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_aversion REAL NOT NULL,
            financial_preference REAL NOT NULL,
            youth_preference REAL NOT NULL,
            aggression REAL NOT NULL,
            patience REAL NOT NULL
        )
    """)

    # Coach Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Coach (
            coach_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            experience_level INTEGER NOT NULL,
            team_id INTEGER,
            learning_rate REAL NOT NULL,
            exploration_rate REAL NOT NULL,
            FOREIGN KEY (team_id) REFERENCES Team(team_id)
        )
    """)

    # TeamCoaches Table (Many-to-Many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamCoaches (
            team_id INTEGER NOT NULL,
            coach_id INTEGER NOT NULL,
            FOREIGN KEY (team_id) REFERENCES Team(team_id),
            FOREIGN KEY (coach_id) REFERENCES Coach(coach_id),
            PRIMARY KEY (team_id, coach_id)
        )
    """)

    # Player Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Player (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            age INTEGER NOT NULL,
            position TEXT NOT NULL,
            team_id INTEGER,
            potential INTEGER NOT NULL,
            wage REAL NOT NULL,
            contract_length INTEGER NOT NULL,
            squad_role TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES Team(team_id)
        )
    """)

    # PlayerAttributes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PlayerAttributes (
            player_id INTEGER NOT NULL,
            attribute_type TEXT NOT NULL,
            sub_attribute TEXT NOT NULL,
            value REAL NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            PRIMARY KEY (player_id, attribute_type, sub_attribute)
        )
    """)

    # PlayerStats Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PlayerStats (
            player_id INTEGER NOT NULL,
            goals INTEGER NOT NULL,
            assists INTEGER NOT NULL,
            appearances INTEGER NOT NULL,
            fitness REAL NOT NULL,
            clean_sheets INTEGER NOT NULL,
            yellow_cards INTEGER NOT NULL,
            red_cards INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            PRIMARY KEY (player_id)
        )
    """)
    
    # Match Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Match (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_number INTEGER NOT NULL,
            date TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_goals INTEGER NOT NULL,
            away_goals INTEGER NOT NULL,
            home_possession REAL NOT NULL,
            away_possession REAL NOT NULL,
            weather TEXT NOT NULL,
            intensity TEXT NOT NULL,
            home_passes_attempted INTEGER NOT NULL DEFAULT 0,
            away_passes_attempted INTEGER NOT NULL DEFAULT 0,
            home_passes_completed INTEGER NOT NULL DEFAULT 0,
            away_passes_completed INTEGER NOT NULL DEFAULT 0,
            home_fouls INTEGER NOT NULL DEFAULT 0,
            away_fouls INTEGER NOT NULL DEFAULT 0,
            home_corners INTEGER NOT NULL DEFAULT 0,
            away_corners INTEGER NOT NULL DEFAULT 0,
            home_offsides INTEGER NOT NULL DEFAULT 0,
            away_offsides INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (home_team_id) REFERENCES Team(team_id),
            FOREIGN KEY (away_team_id) REFERENCES Team(team_id)
        )
    """)

    # MatchShots Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MatchShots (
            match_id INTEGER NOT NULL,
            team TEXT NOT NULL,  -- 'home' or 'away'
            total INTEGER NOT NULL,
            on_target INTEGER NOT NULL,
            FOREIGN KEY (match_id) REFERENCES Match(match_id),
            PRIMARY KEY (match_id, team)
        )
    """)
    
    # MatchEvent Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MatchEvent (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            minute INTEGER NOT NULL,
            type TEXT NOT NULL,
            player TEXT,
            team TEXT,
            details TEXT,
            FOREIGN KEY (match_id) REFERENCES Match(match_id)
        )
    """)
    
    # TransferListing Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TransferListing (
            listing_id INTEGER PRIMARY KEY,
            player_id INTEGER NOT NULL,
            asking_price REAL NOT NULL,
            selling_team_id INTEGER NOT NULL,
            listed_date INTEGER NOT NULL,
            expires_in INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            FOREIGN KEY (selling_team_id) REFERENCES Team(team_id)
        )
    """)

    # TransferHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TransferHistory (
            transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            from_team_id INTEGER NOT NULL,
            to_team_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            day INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            FOREIGN KEY (from_team_id) REFERENCES Team(team_id),
            FOREIGN KEY (to_team_id) REFERENCES Team(team_id)
        )
    """)

    # CoachTrainingEffectiveness Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CoachTrainingEffectiveness (
            coach_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            effectiveness REAL NOT NULL,
            FOREIGN KEY (coach_id) REFERENCES Coach(coach_id),
            PRIMARY KEY (coach_id, method)
        )
    """)

    # CoachSessionResults Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CoachSessionResults (
            coach_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            average_improvement REAL NOT NULL,
            players_improved INTEGER NOT NULL,
            FOREIGN KEY (coach_id) REFERENCES Coach(coach_id)
        )
    """)

    # CoachPlayerProgress Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CoachPlayerProgress (
            coach_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            focus_attribute TEXT NOT NULL,
            improvement TEXT NOT NULL,
            FOREIGN KEY (coach_id) REFERENCES Coach(coach_id)
        )
    """)
    # ManagerTransferAttempts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerTransferAttempts (
            manager_id INTEGER NOT NULL,
            attempt_successful BOOLEAN NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerTransferValueEstimates Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerTransferValueEstimates (
            manager_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            estimated_value REAL NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMarketMemoryPriceHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMarketMemoryPriceHistory (
            manager_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMarketMemoryPositionDemand Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMarketMemoryPositionDemand (
            manager_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            demand_value REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMarketMemorySeasonalFactors Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMarketMemorySeasonalFactors (
            manager_id INTEGER NOT NULL,
            month INTEGER NOT NULL,
            factor REAL NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMarketMemorySuccessPatterns Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMarketMemorySuccessPatterns (
            manager_id INTEGER NOT NULL,
            pattern_data TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)
    
    # ManagerTransferHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerTransferHistory (
            transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            from_team_id INTEGER NOT NULL,
            to_team_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            day INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            FOREIGN KEY (from_team_id) REFERENCES Team(team_id),
            FOREIGN KEY (to_team_id) REFERENCES Team(team_id)
        )
    """)

    # ManagerMatchHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMatchHistory (
            manager_id INTEGER NOT NULL,
            match_data TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerLineupHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerLineupHistory (
            lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            match_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id),
            FOREIGN KEY (match_id) REFERENCES Match(match_id)
        )
    """)

    # ManagerLineupPlayers Table (Many-to-Many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerLineupPlayers (
            lineup_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            FOREIGN KEY (lineup_id) REFERENCES ManagerLineupHistory(lineup_id),
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            PRIMARY KEY (lineup_id, player_id)
        )
    """)

    # ManagerPerformanceHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerPerformanceHistory (
            performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            total_rewards REAL NOT NULL,
            win_rate REAL NOT NULL,
            draw_rate REAL NOT NULL,
            exploration_rate REAL NOT NULL,
            learning_rate REAL NOT NULL,
            matches_played INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            draws INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            average_reward REAL NOT NULL,
            transfer_success_rate REAL NOT NULL,
            current_exploration_rate REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMarketLearning Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMarketLearning (
            market_learning_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            price_trends TEXT NOT NULL,
            position_demand TEXT NOT NULL,
            seasonal_patterns TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerFormationPreferences Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerFormationPreferences (
            formation_preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            formation TEXT NOT NULL,
            preference_weight REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMemoryUsage Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMemoryUsage (
            memory_usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            transfer_history_size INTEGER NOT NULL,
            market_memory_size TEXT NOT NULL,
            value_estimates_size INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMarketStateHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMarketStateHistory (
            market_state_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            market_trend TEXT NOT NULL,
            position_demand TEXT NOT NULL,
            seasonal_factor TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerEpisodeRewards Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerEpisodeRewards (
            manager_id INTEGER NOT NULL,
            reward REAL NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # ManagerMatchRewards Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerMatchRewards (
            manager_id INTEGER NOT NULL,
            reward REAL NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)
    
    # ManagerQTable Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ManagerQTable (
            manager_id INTEGER NOT NULL,
            qtable_type TEXT NOT NULL,
            qtable_data TEXT NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
        )
    """)

    # PlayerForm Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PlayerForm (
            player_id INTEGER NOT NULL,
            form TEXT NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id),
            PRIMARY KEY (player_id)
        )
    """)

    # PlayerInjuryHistory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PlayerInjuryHistory (
            injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            injury_type TEXT NOT NULL,
            duration INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (player_id) REFERENCES Player(player_id)
        )
    """)

    # LeagueHistoricalStandings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS LeagueHistoricalStandings (
            historical_standing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            standings TEXT NOT NULL,
            FOREIGN KEY (league_id) REFERENCES League(league_id)
        )
    """)


    conn.commit()
    conn.close()

def reset_database(db_file=DB_FILE):
    """Drop all tables for a true fresh start."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    # Disable foreign key constraints temporarily
    cursor.execute("PRAGMA foreign_keys = OFF")

    # Drop all tables except sqlite_sequence
    for table in tables:
        table_name = table[0]
        if table_name != 'sqlite_sequence':
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"Dropped table: {table_name}")

    # Re-enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")

    conn.commit()
    conn.close()
    print("Database reset completed - all tables dropped!")

def initialize_fresh_database(db_file=DB_FILE):
    """Initialize database with fresh start - clear all data then recreate tables."""
    print("Initializing fresh database...")
    reset_database(db_file)
    create_tables(db_file)
    print("Fresh database initialization completed!")

if __name__ == '__main__':
    create_tables()
    print("Tables created successfully in", DB_FILE)
