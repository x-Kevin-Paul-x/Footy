import sqlite3
from db_setup import DB_FILE

def create_manager(name, experience_level, team_id=None, profile_id=None, transfers_made=0, successful_transfers=0, formation="4-4-2", matches_played=0, wins=0, draws=0, losses=0, total_rewards=0.0, db_file=DB_FILE ):
    """Inserts a new manager into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Manager (name, experience_level, team_id, profile_id, transfers_made, successful_transfers, formation, matches_played, wins, draws, losses, total_rewards)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, experience_level, team_id, profile_id, transfers_made, successful_transfers, formation, matches_played, wins, draws, losses, total_rewards))
    manager_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return manager_id

def get_manager(manager_id, db_file=DB_FILE):
    """Retrieves a manager by its ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Manager WHERE manager_id = ?", (manager_id,))
    manager = cursor.fetchone()
    conn.close()
    return manager

def get_all_managers(db_file=DB_FILE):
    """Retrieves all managers."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Manager")
    managers = cursor.fetchall()
    conn.close()
    return managers
    
def update_manager(manager_id, name=None, experience_level=None, team_id=None, profile_id=None, transfers_made=None,
                   successful_transfers=None, formation=None, matches_played=None, wins=None, draws=None,
                   losses=None, total_rewards=None, db_file=DB_FILE):
    """Updates a manager's information in the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    update_fields = []
    update_values = []

    if name is not None:
        update_fields.append("name = ?")
        update_values.append(name)
    if experience_level is not None:
        update_fields.append("experience_level = ?")
        update_values.append(experience_level)
    if team_id is not None:
        update_fields.append("team_id = ?")
        update_values.append(team_id)
    if profile_id is not None:
        update_fields.append("profile_id = ?")
        update_values.append(profile_id)
    if transfers_made is not None:
        update_fields.append("transfers_made = ?")
        update_values.append(transfers_made)
    if successful_transfers is not None:
        update_fields.append("successful_transfers = ?")
        update_values.append(successful_transfers)
    if formation is not None:
        update_fields.append("formation = ?")
        update_values.append(formation)
    if matches_played is not None:
        update_fields.append("matches_played = ?")
        update_values.append(matches_played)
    if wins is not None:
        update_fields.append("wins = ?")
        update_values.append(wins)
    if draws is not None:
        update_fields.append("draws = ?")
        update_values.append(draws)
    if losses is not None:
        update_fields.append("losses = ?")
        update_values.append(losses)
    if total_rewards is not None:
        update_fields.append("total_rewards = ?")
        update_values.append(total_rewards)

    if not update_fields:
        conn.close()
        return  # Nothing to update

    update_query = f"UPDATE Manager SET {', '.join(update_fields)} WHERE manager_id = ?"
    update_values.append(manager_id)

    cursor.execute(update_query, tuple(update_values))
    conn.commit()
    conn.close()

def delete_manager(manager_id, db_file=DB_FILE):
    """Deletes a manager from the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Manager WHERE manager_id = ?", (manager_id,))
    conn.commit()
    conn.close()

def test_manager_db():
    """Tests for manager database functions."""
    print("Testing manager_db.py...")

    # Create a test manager
    manager_name = "Test Manager"
    experience_level = 3
    team_id = 1
    profile_id = 1
    manager_id = create_manager(manager_name, experience_level, team_id, profile_id)
    assert manager_id is not None
    print(f"  Created manager with ID: {manager_id}")

    # Retrieve the manager
    retrieved_manager = get_manager(manager_id)
    assert retrieved_manager is not None
    assert retrieved_manager[1] == manager_name  # Check name
    assert retrieved_manager[2] == experience_level  # Check experience
    assert retrieved_manager[3] == team_id
    assert retrieved_manager[4] == profile_id

    print(f"  Retrieved manager: {retrieved_manager}")

    # Update the manager
    new_experience_level = 4
    new_formation = "4-3-3"
    update_manager(manager_id, experience_level=new_experience_level, formation=new_formation)
    updated_manager = get_manager(manager_id)
    assert updated_manager is not None
    assert updated_manager[2] == new_experience_level
    assert updated_manager[7] == new_formation  # Check formation (index 7)
    print(f"  Updated manager: {updated_manager}")

    # Get all managers
    all_managers = get_all_managers()
    assert all_managers is not None
    assert len(all_managers) >= 1
    print(f"  Retrieved all managers. Count: {len(all_managers)}")

    # Delete the manager
    delete_manager(manager_id)
    deleted_manager = get_manager(manager_id)
    assert deleted_manager is None
    print(f"  Deleted manager with ID: {manager_id}")

    print("manager_db.py tests passed.")

if __name__ == '__main__':
    test_manager_db()

