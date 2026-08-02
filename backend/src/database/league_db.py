from database.session import SessionLocal, get_db_session
from database.models import League

def create_league(name, season_year, num_teams=20, db_file=None):
    """Inserts a new league into the database."""
    with get_db_session() as db:
        league = League(name=name, season_year=season_year)
        db.add(league)
        db.flush()
        return league.league_id

def get_league(league_id, db_file=None):
    """Retrieves a league by its ID."""
    db = SessionLocal()
    try:
        league = db.query(League).filter(League.league_id == league_id).first()
        if league:
            return {
                "league_id": league.league_id,
                "name": league.name,
                "season_year": league.season_year,
                "num_teams": 20
            }
        return None
    finally:
        db.close()

def update_league(league_id, name=None, season_year=None, num_teams=None, db_file=None):
    """Updates a league's information in the database."""
    with get_db_session() as db:
        league = db.query(League).filter(League.league_id == league_id).first()
        if league:
            if name is not None:
                league.name = name
            if season_year is not None:
                league.season_year = season_year

def delete_league(league_id, db_file=None):
    """Deletes a league from the database."""
    with get_db_session() as db:
        db.query(League).filter(League.league_id == league_id).delete()

def get_all_leagues(db_file=None):
    """Retrieves all leagues."""
    db = SessionLocal()
    try:
        leagues = db.query(League).all()
        return [(l.league_id, l.name, l.season_year) for l in leagues]
    finally:
        db.close()


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
