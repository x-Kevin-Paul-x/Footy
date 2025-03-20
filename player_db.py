import sqlite3
from db_setup import DB_FILE

def create_player(name, age, position, team_id, potential, wage, contract_length, squad_role, attributes, db_file=DB_FILE):
    """Inserts a new player and their attributes into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Player (name, age, position, team_id, potential, wage, contract_length, squad_role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, age, position, team_id, potential, wage, contract_length, squad_role))
    player_id = cursor.lastrowid

    # Insert attributes
    for attr_type, sub_attributes in attributes.items():
        for sub_attr, value in sub_attributes.items():
            cursor.execute("""
                INSERT INTO PlayerAttributes (player_id, attribute_type, sub_attribute, value)
                VALUES (?, ?, ?, ?)
            """, (player_id, attr_type, sub_attr, value))

    conn.commit()
    conn.close()
    return player_id

def get_player(player_id, db_file=DB_FILE):
    """Retrieves a player and their attributes by player ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Get basic player info
    cursor.execute("SELECT * FROM Player WHERE player_id = ?", (player_id,))
    player = cursor.fetchone()

    if not player:
        conn.close()
        return None  # Player not found

    # Get player attributes
    cursor.execute("SELECT attribute_type, sub_attribute, value FROM PlayerAttributes WHERE player_id = ?", (player_id,))
    attributes = {}
    for attr_type, sub_attr, value in cursor.fetchall():
        if attr_type not in attributes:
            attributes[attr_type] = {}
        attributes[attr_type][sub_attr] = value

    conn.close()
    # Combine player info and attributes
    player_data = {
        "player_id": player[0],
        "name": player[1],
        "age": player[2],
        "position": player[3],
        "team_id": player[4],
        "potential": player[5],
        "wage": player[6],
        "contract_length": player[7],
        "squad_role": player[8],
        "attributes": attributes
    }
    return player_data

def get_all_players(db_file=DB_FILE):
    """Retrieves all players and their attributes."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM Player")
    player_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    players = []
    for player_id in player_ids:
        players.append(get_player(player_id, db_file))

    return players

def update_player(player_id, name=None, age=None, position=None, team_id=None, potential=None, wage=None,
                  contract_length=None, squad_role=None, attributes=None, db_file=DB_FILE):
    """Updates a player's information and attributes."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Update basic player info
    update_fields = []
    update_values = []

    if name:
        update_fields.append("name = ?")
        update_values.append(name)
    if age:
        update_fields.append("age = ?")
        update_values.append(age)
    if position:
        update_fields.append("position = ?")
        update_values.append(position)
    if team_id is not None:
        update_fields.append("team_id = ?")
        update_values.append(team_id)
    if potential:
        update_fields.append("potential = ?")
        update_values.append(potential)
    if wage:
        update_fields.append("wage = ?")
        update_values.append(wage)
    if contract_length:
        update_fields.append("contract_length = ?")
        update_values.append(contract_length)
    if squad_role:
        update_fields.append("squad_role = ?")
        update_values.append(squad_role)

    if update_fields:
        update_query = f"UPDATE Player SET {', '.join(update_fields)} WHERE player_id = ?"
        update_values.append(player_id)
        cursor.execute(update_query, tuple(update_values))

    # Update attributes (delete and re-insert)
    if attributes:
        cursor.execute("DELETE FROM PlayerAttributes WHERE player_id = ?", (player_id,))
        for attr_type, sub_attributes in attributes.items():
            for sub_attr, value in sub_attributes.items():
                cursor.execute("""
                    INSERT INTO PlayerAttributes (player_id, attribute_type, sub_attribute, value)
                    VALUES (?, ?, ?, ?)
                """, (player_id, attr_type, sub_attr, value))

    conn.commit()
    conn.close()

def delete_player(player_id, db_file=DB_FILE):
    """Deletes a player and their attributes."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Delete attributes first (due to foreign key constraint)
    cursor.execute("DELETE FROM PlayerAttributes WHERE player_id = ?", (player_id,))
    # Delete player
    cursor.execute("DELETE FROM Player WHERE player_id = ?", (player_id,))

    conn.commit()
    conn.close()

def test_player_db(db_file="test_football_sim.db"):
    """Tests for player database functions."""
    print("Testing player_db.py...")

    # Create a test player
    player_name = "Test Player"
    age = 25
    position = "ST"
    team_id = 1  # Assuming a team with ID 1 exists
    potential = 85
    wage = 10000.0
    contract_length = 3
    squad_role = "Rotation"
    attributes = {
        "pace": {"acceleration": 80, "sprint_speed": 82},
        "shooting": {"finishing": 75, "shot_power": 78}
    }
    player_id = create_player(player_name, age, position, team_id, potential, wage, contract_length, squad_role, attributes, db_file=db_file)
    assert player_id is not None
    print(f"  Created player with ID: {player_id}")

    # Retrieve the player
    retrieved_player = get_player(player_id, db_file=db_file)
    assert retrieved_player is not None
    assert retrieved_player["name"] == player_name
    assert retrieved_player["age"] == age
    assert retrieved_player["position"] == position
    assert retrieved_player["team_id"] == team_id
    assert retrieved_player["potential"] == potential
    assert retrieved_player["wage"] == wage
    assert retrieved_player["contract_length"] == contract_length
    assert retrieved_player["squad_role"] == squad_role
    assert retrieved_player["attributes"] == attributes

    print(f"  Retrieved player: {retrieved_player}")

    # Update the player
    new_age = 26
    new_wage = 12000.0
    update_player(player_id, age=new_age, wage=new_wage, db_file=db_file)
    updated_player = get_player(player_id, db_file=db_file)
    assert updated_player is not None
    assert updated_player["age"] == new_age
    assert updated_player["wage"] == new_wage
    print(f"  Updated player: {updated_player}")

    # Get all players
    all_players = get_all_players(db_file=db_file)
    assert all_players is not None
    assert len(all_players) >= 1
    print(f"  Retrieved all players. Count: {len(all_players)}")

    # Delete the player
    delete_player(player_id, db_file=db_file)
    deleted_player = get_player(player_id, db_file=db_file)
    assert deleted_player is None
    print(f"  Deleted player with ID: {player_id}")

    print("player_db.py tests passed.")

if __name__ == '__main__':
    test_player_db()

