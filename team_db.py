import sqlite3
from db_setup import DB_FILE

def create_team(name, budget, weekly_budget, transfer_budget, wage_budget, manager_id=None, db_file=DB_FILE):
    """Inserts a new team into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Team (name, budget, weekly_budget, transfer_budget, wage_budget, manager_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, budget, weekly_budget, transfer_budget, wage_budget, manager_id))
    conn.commit()
    team_id = cursor.lastrowid
    conn.close()
    return team_id

def get_team(team_id, db_file=DB_FILE):
    """Retrieves a team by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Team WHERE team_id = ?", (team_id,))
    team = cursor.fetchone()
    conn.close()
    return team

def get_all_teams(db_file=DB_FILE):
    """Retrieves all teams."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Team")
    teams = cursor.fetchall()
    conn.close()
    return teams

def update_team(team_id, name=None, budget=None, weekly_budget=None, transfer_budget=None, wage_budget=None, manager_id=None, db_file=DB_FILE):
    """Updates a team's information."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    update_fields = []
    update_values = []

    if name:
        update_fields.append("name = ?")
        update_values.append(name)
    if budget:
        update_fields.append("budget = ?")
        update_values.append(budget)
    if weekly_budget:
        update_fields.append("weekly_budget = ?")
        update_values.append(weekly_budget)
    if transfer_budget:
        update_fields.append("transfer_budget = ?")
        update_values.append(transfer_budget)
    if wage_budget:
        update_fields.append("wage_budget = ?")
        update_values.append(wage_budget)
    if manager_id is not None:  # Allow setting manager_id to NULL
        update_fields.append("manager_id = ?")
        update_values.append(manager_id)

    if not update_fields:
        conn.close()
        return  # Nothing to update

    update_query = f"UPDATE Team SET {', '.join(update_fields)} WHERE team_id = ?"
    update_values.append(team_id)

    cursor.execute(update_query, tuple(update_values))
    conn.commit()
    conn.close()

def delete_team(team_id, db_file=DB_FILE):
    """Deletes a team by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Team WHERE team_id = ?", (team_id,))
    conn.commit()
    conn.close()
    
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

