import sqlite3
from db_setup import DB_FILE

def create_league(name, season_year, db_file=DB_FILE):
    """Inserts a new league into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO League (name, season_year) VALUES (?, ?)", (name, season_year))
    conn.commit()
    league_id = cursor.lastrowid
    conn.close()
    return league_id

def get_league(league_id, db_file=DB_FILE):
    """Retrieves a league by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM League WHERE league_id = ?", (league_id,))
    league = cursor.fetchone()
    conn.close()
    return league

def get_all_leagues(db_file=DB_FILE):
    """Retrieves all leagues."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM League")
    leagues = cursor.fetchall()
    conn.close()
    return leagues

def test_league_db(db_file="test_football_sim.db"):
    """Tests for league database functions."""
    print("Testing league_db.py...")

    # Create a test league
    league_name = "Test League"
    season_year = 2025
    league_id = create_league(league_name, season_year, db_file=db_file)
    assert league_id is not None
    print(f"  Created league with ID: {league_id}")

    # Retrieve the league
    retrieved_league = get_league(league_id, db_file=db_file)
    assert retrieved_league is not None
    assert retrieved_league[1] == league_name  # Check name (index 1)
    assert retrieved_league[2] == season_year  # Check season_year (index 2)
    print(f"  Retrieved league: {retrieved_league}")

    # Retrieve all leagues
    all_leagues = get_all_leagues(db_file=db_file)
    assert all_leagues is not None
    assert len(all_leagues) >= 1  # At least the one we just created
    print(f"  Retrieved all leagues. Count: {len(all_leagues)}")
    print("league_db.py tests passed.")

if __name__ == '__main__':
    test_league_db()