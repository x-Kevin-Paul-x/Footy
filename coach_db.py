import sqlite3
from db_setup import DB_FILE

def create_coach(name, specialty, experience_level, team_id=None, db_file=DB_FILE): 
    """Inserts a new coach into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Coach (name, specialty, experience_level, team_id, learning_rate, exploration_rate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, specialty, experience_level, team_id, 0.1, 0.2))
    coach_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return coach_id

def get_coach(coach_id, db_file=DB_FILE):
    """Retrieves a coach by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Coach WHERE coach_id = ?", (coach_id,))
    coach = cursor.fetchone()
    conn.close()
    return coach

def get_all_coaches(db_file=DB_FILE):
    """Retrieves all coaches."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Coach")
    coaches = cursor.fetchall()
    conn.close()
    return coaches

def update_coach(coach_id, name=None, specialty=None, experience_level=None, team_id=None, learning_rate=None, exploration_rate=None, db_file=DB_FILE):
    """Updates a coach's information."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    update_fields = []
    update_values = []

    if name:
        update_fields.append("name = ?")
        update_values.append(name)
    if specialty:
        update_fields.append("specialty = ?")
        update_values.append(specialty)
    if experience_level:
        update_fields.append("experience_level = ?")
        update_values.append(experience_level)
    if team_id is not None:
        update_fields.append("team_id = ?")
        update_values.append(team_id)
    if learning_rate is not None:
        update_fields.append("learning_rate = ?")
        update_values.append(learning_rate)
    if exploration_rate is not None:
        update_fields.append("exploration_rate = ?")
        update_values.append(exploration_rate)

    if not update_fields:
        conn.close()
        return  # Nothing to update

    update_query = f"UPDATE Coach SET {', '.join(update_fields)} WHERE coach_id = ?"
    update_values.append(coach_id)

    cursor.execute(update_query, tuple(update_values))
    conn.commit()
    conn.close()

def delete_coach(coach_id, db_file=DB_FILE):
    """Deletes a coach by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Coach WHERE coach_id = ?", (coach_id,))
    conn.commit()
    conn.close()
    
def add_coach_to_team(coach_id, team_id, db_file=DB_FILE):
    """Adds a coach to a team in the TeamCoaches table."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO TeamCoaches (team_id, coach_id) VALUES (?, ?)", (team_id, coach_id))
    conn.commit()
    conn.close()

def remove_coach_from_team(coach_id, team_id, db_file=DB_FILE):
    """Removes a coach from a team in the TeamCoaches table."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TeamCoaches WHERE team_id = ? AND coach_id = ?", (team_id, coach_id))
    conn.commit()
    conn.close()

def get_coaches_for_team(team_id, db_file=DB_FILE):
    """Retrieves all coaches associated with a team."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Coach.*
        FROM Coach
        INNER JOIN TeamCoaches ON Coach.coach_id = TeamCoaches.coach_id
        WHERE TeamCoaches.team_id = ?
    """, (team_id,))
    coaches = cursor.fetchall()
    conn.close()
    return coaches

def test_coach_db():
    """Tests for coach database functions."""
    print("Testing coach_db.py...")

    # Create a test coach
    coach_name = "Test Coach"
    specialty = "Attacking"
    experience_level = 5
    team_id = 1  # Assuming a team with ID 1 exists
    coach_id = create_coach(coach_name, specialty, experience_level, team_id)
    assert coach_id is not None
    print(f"  Created coach with ID: {coach_id}")

    # Retrieve the coach
    retrieved_coach = get_coach(coach_id)
    assert retrieved_coach is not None
    assert retrieved_coach[1] == coach_name  # Check name (index 1)
    assert retrieved_coach[2] == specialty
    assert retrieved_coach[3] == experience_level
    assert retrieved_coach[4] == team_id

    print(f"  Retrieved coach: {retrieved_coach}")

    # Update the coach
    new_specialty = "Defending"
    new_experience_level = 6
    update_coach(coach_id, specialty=new_specialty, experience_level=new_experience_level)
    updated_coach = get_coach(coach_id)
    assert updated_coach is not None
    assert updated_coach[2] == new_specialty
    assert updated_coach[3] == new_experience_level
    print(f"  Updated coach: {updated_coach}")

    # Get all coaches
    all_coaches = get_all_coaches()
    assert all_coaches is not None
    assert len(all_coaches) >= 1
    print(f"  Retrieved all coaches. Count: {len(all_coaches)}")
    
    # Add coach to team and check
    add_coach_to_team(coach_id, team_id)
    team_coaches = get_coaches_for_team(team_id)
    assert any([coach[0] == coach_id for coach in team_coaches])
    print(f"   Added coach to team and verified.")

    # Remove coach from team and check
    remove_coach_from_team(coach_id, team_id)
    team_coaches = get_coaches_for_team(team_id)
    assert not any([coach[0] == coach_id for coach in team_coaches])
    print(f"   Removed coach from team and verified.")

    # Delete the coach
    delete_coach(coach_id)
    deleted_coach = get_coach(coach_id)
    assert deleted_coach is None
    print(f"  Deleted coach with ID: {coach_id}")

    print("coach_db.py tests passed.")

if __name__ == '__main__':
    test_coach_db()