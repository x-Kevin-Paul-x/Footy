from database.session import SessionLocal, get_db_session
from database.models import Manager

def create_manager(name, experience_level, team_id=None, profile_id=None, transfers_made=0, successful_transfers=0, formation="4-4-2", matches_played=0, wins=0, draws=0, losses=0, total_rewards=0.0, db_file=None):
    """Inserts a new manager into the database using SQLAlchemy."""
    with get_db_session() as db:
        manager = Manager(
            name=name,
            experience_level=experience_level,
            team_id=team_id,
            profile_id=profile_id,
            transfers_made=transfers_made,
            successful_transfers=successful_transfers,
            formation=formation,
            matches_played=matches_played,
            wins=wins,
            draws=draws,
            losses=losses,
            total_rewards=total_rewards
        )
        db.add(manager)
        db.flush()
        return manager.manager_id

def get_manager(manager_id, db_file=None):
    """Retrieves a manager by ID as a tuple."""
    db = SessionLocal()
    try:
        m = db.query(Manager).filter(Manager.manager_id == manager_id).first()
        if m:
            return (
                m.manager_id,
                m.name,
                m.experience_level,
                m.team_id,
                m.profile_id,
                m.transfers_made,
                m.successful_transfers,
                m.formation,
                m.matches_played,
                m.wins,
                m.draws,
                m.losses,
                m.total_rewards
            )
        return None
    finally:
        db.close()

def get_all_managers(db_file=None):
    """Retrieves all managers as tuples."""
    db = SessionLocal()
    try:
        managers = db.query(Manager).all()
        return [
            (
                m.manager_id,
                m.name,
                m.experience_level,
                m.team_id,
                m.profile_id,
                m.transfers_made,
                m.successful_transfers,
                m.formation,
                m.matches_played,
                m.wins,
                m.draws,
                m.losses,
                m.total_rewards
            )
            for m in managers
        ]
    finally:
        db.close()
    
def update_manager(manager_id, name=None, experience_level=None, team_id=None, profile_id=None, transfers_made=None,
                   successful_transfers=None, formation=None, matches_played=None, wins=None, draws=None,
                   losses=None, total_rewards=None, db_file=None):
    """Updates a manager's information in the database."""
    with get_db_session() as db:
        m = db.query(Manager).filter(Manager.manager_id == manager_id).first()
        if m:
            if name is not None: m.name = name
            if experience_level is not None: m.experience_level = experience_level
            if team_id is not None: m.team_id = team_id
            if profile_id is not None: m.profile_id = profile_id
            if transfers_made is not None: m.transfers_made = transfers_made
            if successful_transfers is not None: m.successful_transfers = successful_transfers
            if formation is not None: m.formation = formation
            if matches_played is not None: m.matches_played = matches_played
            if wins is not None: m.wins = wins
            if draws is not None: m.draws = draws
            if losses is not None: m.losses = losses
            if total_rewards is not None: m.total_rewards = total_rewards

def delete_manager(manager_id, db_file=None):
    """Deletes a manager from the database."""
    with get_db_session() as db:
        db.query(Manager).filter(Manager.manager_id == manager_id).delete()

def test_manager_db():
    """Tests for manager database functions."""
    print("Testing manager_db.py...")

    # Create a test manager
    manager_name = "Test Manager"
    experience_level = 3
    team_id = None
    profile_id = None
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


