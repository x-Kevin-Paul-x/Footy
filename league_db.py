import sqlite3
from db_setup import DB_FILE

def create_league(name, season_year, num_teams=20, db_file=DB_FILE):
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
    cursor.execute("SELECT league_id, name, season_year FROM League WHERE league_id = ?", (league_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "league_id": row[0],
            "name": row[1], 
            "season_year": row[2],
            "num_teams": 20  # Default value since not stored in DB
        }
    return None

def update_league(league_id, name=None, season_year=None, num_teams=None, db_file=DB_FILE):
    """Updates a league's information in the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    update_fields = []
    update_values = []

    if name is not None:
        update_fields.append("name = ?")
        update_values.append(name)
    if season_year is not None:
        update_fields.append("season_year = ?")
        update_values.append(season_year)

    if not update_fields:
        conn.close()
        return  # Nothing to update

    update_query = f"UPDATE League SET {', '.join(update_fields)} WHERE league_id = ?"
    update_values.append(league_id)

    cursor.execute(update_query, tuple(update_values))
    conn.commit()
    conn.close()

def delete_league(league_id, db_file=DB_FILE):
    """Deletes a league from the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM League WHERE league_id = ?", (league_id,))
    conn.commit()
    conn.close()

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
    assert retrieved_league["name"] == league_name
    assert retrieved_league["season_year"] == season_year
    print(f"  Retrieved league: {retrieved_league}")

    # Update the league
    new_name = "Updated League"
    new_season = 2026
    update_league(league_id, name=new_name, season_year=new_season, db_file=db_file)
    updated_league = get_league(league_id, db_file=db_file)
    assert updated_league is not None
    assert updated_league["name"] == new_name
    assert updated_league["season_year"] == new_season
    print(f"  Updated league: {updated_league}")

    # Retrieve all leagues
    all_leagues = get_all_leagues(db_file=db_file)
    assert all_leagues is not None
    assert len(all_leagues) >= 1  # At least the one we just created
    print(f"  Retrieved all leagues. Count: {len(all_leagues)}")

    # Delete the league
    delete_league(league_id, db_file=db_file)
    deleted_league = get_league(league_id, db_file=db_file)
    assert deleted_league is None
    print(f"  Deleted league with ID: {league_id}")
    
    print("league_db.py tests passed.")

if __name__ == '__main__':
    test_league_db()
