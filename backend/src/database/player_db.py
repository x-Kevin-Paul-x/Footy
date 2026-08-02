from database.session import SessionLocal, get_db_session
from database.models import Player, PlayerAttribute

def create_player(name, age, position, team_id, potential, wage, contract_length, squad_role, attributes, db_file=None):
    """Inserts a new player and their attributes into the database."""
    db_team_id = None if (team_id == -1 or team_id is None) else team_id
    with get_db_session() as db:
        player = Player(
            name=name,
            age=age,
            position=position,
            team_id=db_team_id,
            potential=potential,
            wage=wage,
            contract_length=contract_length,
            squad_role=squad_role
        )
        db.add(player)
        db.flush()
        player_id = player.player_id

        # Insert attributes
        for attr_type, sub_attributes in attributes.items():
            for sub_attr, value in sub_attributes.items():
                attr = PlayerAttribute(
                    player_id=player_id,
                    attribute_type=attr_type,
                    sub_attribute=sub_attr,
                    value=value
                )
                db.add(attr)
        db.commit()
        return player_id

def get_player(player_id, db_file=None):
    """Retrieves a player and their attributes by player ID."""
    db = SessionLocal()
    try:
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if not player:
            return None

        attributes = {}
        for attr in player.attributes:
            if attr.attribute_type not in attributes:
                attributes[attr.attribute_type] = {}
            attributes[attr.attribute_type][attr.sub_attribute] = attr.value

        player_data = {
            "player_id": player.player_id,
            "name": player.name,
            "age": player.age,
            "position": player.position,
            "team_id": player.team_id,
            "potential": player.potential,
            "wage": player.wage,
            "contract_length": player.contract_length,
            "squad_role": player.squad_role,
            "attributes": attributes
        }
        return player_data
    finally:
        db.close()

def get_all_players(db_file=None):
    """Retrieves all players and their attributes."""
    db = SessionLocal()
    try:
        player_rows = db.query(Player).all()
        players = []
        for player in player_rows:
            attributes = {}
            for attr in player.attributes:
                if attr.attribute_type not in attributes:
                    attributes[attr.attribute_type] = {}
                attributes[attr.attribute_type][attr.sub_attribute] = attr.value

            players.append({
                "player_id": player.player_id,
                "name": player.name,
                "age": player.age,
                "position": player.position,
                "team_id": player.team_id,
                "potential": player.potential,
                "wage": player.wage,
                "contract_length": player.contract_length,
                "squad_role": player.squad_role,
                "attributes": attributes
            })
        return players
    finally:
        db.close()

def update_player(player_id, name=None, age=None, position=None, team_id=None, potential=None, wage=None,
                  contract_length=None, squad_role=None, attributes=None, db_file=None):
    """Updates a player's information and attributes."""
    with get_db_session() as db:
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if not player:
            return

        if name is not None: player.name = name
        if age is not None: player.age = age
        if position is not None: player.position = position
        if team_id is not None:
            player.team_id = None if team_id == -1 else team_id
        if potential is not None: player.potential = potential
        if wage is not None: player.wage = wage
        if contract_length is not None: player.contract_length = contract_length
        if squad_role is not None: player.squad_role = squad_role

        if attributes is not None:
            db.query(PlayerAttribute).filter(PlayerAttribute.player_id == player_id).delete()
            for attr_type, sub_attributes in attributes.items():
                for sub_attr, value in sub_attributes.items():
                    db.add(PlayerAttribute(
                        player_id=player_id,
                        attribute_type=attr_type,
                        sub_attribute=sub_attr,
                        value=value
                    ))

def delete_player(player_id, db_file=None):
    """Deletes a player and their attributes."""
    with get_db_session() as db:
        db.query(PlayerAttribute).filter(PlayerAttribute.player_id == player_id).delete()
        db.query(Player).filter(Player.player_id == player_id).delete()

def test_player_db(db_file="test_football_sim.db"):
    """Tests for player database functions."""
    print("Testing player_db.py...")

    from database.team_db import create_team, delete_team

    team_id = create_team(
        "Player Test Team",
        1000000.0,
        50000.0,
        200000.0,
        800000.0,
        db_file=db_file,
    )

    # Create a test player
    player_name = "Test Player"
    age = 25
    position = "ST"
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

    delete_team(team_id, db_file=db_file)

    print("player_db.py tests passed.")

if __name__ == '__main__':
    test_player_db()

