from database.session import SessionLocal
from database.models import Team

def create_team(name, budget, weekly_budget, transfer_budget, wage_budget, manager_id=None, db_file=None):
    """Inserts a new team into the database (SQLAlchemy)."""
    db = SessionLocal()
    team = Team(
        name=name,
        budget=budget,
        weekly_budget=weekly_budget,
        transfer_budget=transfer_budget,
        wage_budget=wage_budget,
        manager_id=manager_id
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    team_id = team.team_id
    db.close()
    return team_id

def get_team(team_id, db_file=None):
    """Retrieves a team by its ID."""
    db = SessionLocal()
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if team:
        result = (team.team_id, team.name, team.budget, team.weekly_budget, team.transfer_budget, team.wage_budget, team.manager_id)
    else:
        result = None
    db.close()
    return result

def get_all_teams(db_file=None):
    """Retrieves all teams."""
    db = SessionLocal()
    teams = db.query(Team).all()
    results = [(t.team_id, t.name, t.budget, t.weekly_budget, t.transfer_budget, t.wage_budget, t.manager_id) for t in teams]
    db.close()
    return results

def update_team(team_id, name=None, budget=None, weekly_budget=None, transfer_budget=None, wage_budget=None, manager_id=None, db_file=None):
    """Updates a team's information."""
    db = SessionLocal()
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if team:
        if name is not None: team.name = name
        if budget is not None: team.budget = budget
        if weekly_budget is not None: team.weekly_budget = weekly_budget
        if transfer_budget is not None: team.transfer_budget = transfer_budget
        if wage_budget is not None: team.wage_budget = wage_budget
        if manager_id is not None: team.manager_id = manager_id
        db.commit()
    db.close()

def delete_team(team_id, db_file=None):
    """Deletes a team by its ID."""
    db = SessionLocal()
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if team:
        db.delete(team)
        db.commit()
    db.close()
    
def test_team_db(db_file="test_football_sim.db"):
    """Tests for team database functions."""
    print("Testing team_db.py...")

    # Create a test team
    team_name = "Test Team"
    budget = 1000000.0
    weekly_budget = 50000.0
    transfer_budget = 200000.0
    wage_budget = 800000.0
    team_id = create_team(team_name, budget, weekly_budget, transfer_budget, wage_budget, db_file=db_file)
    assert team_id is not None
    print(f"  Created team with ID: {team_id}")

    # Retrieve the team
    retrieved_team = get_team(team_id, db_file=db_file)
    assert retrieved_team is not None
    assert retrieved_team[1] == team_name  # Check name (index 1)
    assert retrieved_team[2] == budget
    assert retrieved_team[3] == weekly_budget
    assert retrieved_team[4] == transfer_budget
    assert retrieved_team[5] == wage_budget

    print(f"  Retrieved team: {retrieved_team}")

    # Update the team
    new_name = "Updated Team Name"
    new_budget = 1200000.0
    update_team(team_id, name=new_name, budget=new_budget, db_file=db_file)
    updated_team = get_team(team_id, db_file=db_file)
    assert updated_team is not None
    assert updated_team[1] == new_name
    assert updated_team[2] == new_budget
    print(f"  Updated team: {updated_team}")

    # Get all teams
    all_teams = get_all_teams(db_file=db_file)
    assert all_teams is not None
    assert len(all_teams) >= 1
    print(f"  Retrieved all teams. Count: {len(all_teams)}")

    # Delete the team
    delete_team(team_id, db_file=db_file)
    deleted_team = get_team(team_id, db_file=db_file)
    assert deleted_team is None
    print(f"  Deleted team with ID: {team_id}")

    print("team_db.py tests passed.")

if __name__ == '__main__':
    test_team_db()

