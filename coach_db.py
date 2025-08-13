import sqlite3
from db_setup import DB_FILE

def create_coach(name, specialty, experience_level, team_id=None, learning_rate=0.1, exploration_rate=0.2, improvement_history=None, training_effectiveness=None, training_methods=None, session_results=None, player_progress=None, db_file=DB_FILE):
    """Inserts a new coach into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    improvement_history_json = json.dumps(improvement_history) if improvement_history else None
    training_effectiveness_json = json.dumps(training_effectiveness) if training_effectiveness else None
    training_methods_json = json.dumps(training_methods) if training_methods else None
    session_results_json = json.dumps(session_results) if session_results else None
    player_progress_json = json.dumps(player_progress) if player_progress else None

    cursor.execute("""
        INSERT INTO Coach (name, specialty, experience_level, team_id, learning_rate, exploration_rate, improvement_history, training_effectiveness, training_methods, session_results, player_progress)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, specialty, experience_level, team_id, learning_rate, exploration_rate, improvement_history_json, training_effectiveness_json, training_methods_json, session_results_json, player_progress_json))
    coach_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return coach_id

import json

def get_coach(coach_id, db_file=DB_FILE):
    """Retrieves a coach by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Coach WHERE coach_id = ?", (coach_id,))
    coach_row = cursor.fetchone()
    conn.close()
    if not coach_row:
        return None

    coach_data = list(coach_row)
    # Deserialize JSON fields
    coach_data[7] = json.loads(coach_data[7]) if coach_data[7] else None
    coach_data[8] = json.loads(coach_data[8]) if coach_data[8] else None
    coach_data[9] = json.loads(coach_data[9]) if coach_data[9] else None
    coach_data[10] = json.loads(coach_data[10]) if coach_data[10] else []
    coach_data[11] = json.loads(coach_data[11]) if coach_data[11] else None

    return tuple(coach_data)

def get_all_coaches(db_file=DB_FILE):
    """Retrieves all coaches."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Coach")
    coaches = cursor.fetchall()
    conn.close()
    return coaches

def update_coach(coach_id, name=None, specialty=None, experience_level=None, team_id=None, learning_rate=None, exploration_rate=None, improvement_history=None, training_effectiveness=None, training_methods=None, session_results=None, player_progress=None, db_file=DB_FILE):
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
    if improvement_history is not None:
        update_fields.append("improvement_history = ?")
        update_values.append(json.dumps(improvement_history))
    if training_effectiveness is not None:
        update_fields.append("training_effectiveness = ?")
        update_values.append(json.dumps(training_effectiveness))
    if training_methods is not None:
        update_fields.append("training_methods = ?")
        update_values.append(json.dumps(training_methods))
    if session_results is not None:
        update_fields.append("session_results = ?")
        update_values.append(json.dumps(session_results))
    if player_progress is not None:
        update_fields.append("player_progress = ?")
        update_values.append(json.dumps(player_progress))

    if not update_fields:
        conn.close()
        return

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