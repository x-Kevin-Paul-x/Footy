from database.session import SessionLocal, get_db_session
from database.models import Coach, team_coaches_association

def create_coach(name, specialty, experience_level, team_id=None, db_file=None): 
    """Inserts a new coach into the database using SQLAlchemy."""
    with get_db_session() as db:
        coach = Coach(
            name=name,
            specialty=specialty,
            experience_level=experience_level,
            team_id=team_id,
            learning_rate=0.1,
            exploration_rate=0.2
        )
        db.add(coach)
        db.flush()
        return coach.coach_id

def get_coach(coach_id, db_file=None):
    """Retrieves a coach by ID as a tuple."""
    db = SessionLocal()
    try:
        coach = db.query(Coach).filter(Coach.coach_id == coach_id).first()
        if coach:
            return (
                coach.coach_id,
                coach.name,
                coach.specialty,
                coach.experience_level,
                coach.team_id,
                coach.learning_rate,
                coach.exploration_rate
            )
        return None
    finally:
        db.close()

def get_all_coaches(db_file=None):
    """Retrieves all coaches as tuples."""
    db = SessionLocal()
    try:
        coaches = db.query(Coach).all()
        return [
            (
                c.coach_id,
                c.name,
                c.specialty,
                c.experience_level,
                c.team_id,
                c.learning_rate,
                c.exploration_rate
            )
            for c in coaches
        ]
    finally:
        db.close()

def update_coach(coach_id, name=None, specialty=None, experience_level=None, team_id=None, learning_rate=None, exploration_rate=None, db_file=None):
    """Updates a coach's information."""
    with get_db_session() as db:
        coach = db.query(Coach).filter(Coach.coach_id == coach_id).first()
        if coach:
            if name is not None:
                coach.name = name
            if specialty is not None:
                coach.specialty = specialty
            if experience_level is not None:
                coach.experience_level = experience_level
            if team_id is not None:
                coach.team_id = team_id
            if learning_rate is not None:
                coach.learning_rate = learning_rate
            if exploration_rate is not None:
                coach.exploration_rate = exploration_rate

def delete_coach(coach_id, db_file=None):
    """Deletes a coach by ID."""
    with get_db_session() as db:
        db.query(Coach).filter(Coach.coach_id == coach_id).delete()

def add_coach_to_team(coach_id, team_id, db_file=None):
    """Adds a coach to a team in the team_coaches_association table."""
    with get_db_session() as db:
        stmt = team_coaches_association.insert().values(team_id=team_id, coach_id=coach_id)
        db.execute(stmt)

def remove_coach_from_team(coach_id, team_id, db_file=None):
    """Removes a coach from a team in the team_coaches_association table."""
    with get_db_session() as db:
        stmt = team_coaches_association.delete().where(
            (team_coaches_association.c.team_id == team_id) & 
            (team_coaches_association.c.coach_id == coach_id)
        )
        db.execute(stmt)

def get_coaches_for_team(team_id, db_file=None):
    """Retrieves all coaches associated with a team."""
    db = SessionLocal()
    try:
        coaches = db.query(Coach).join(team_coaches_association).filter(
            team_coaches_association.c.team_id == team_id
        ).all()
        return [
            (
                c.coach_id,
                c.name,
                c.specialty,
                c.experience_level,
                c.team_id,
                c.learning_rate,
                c.exploration_rate
            )
            for c in coaches
        ]
    finally:
        db.close()

def test_coach_db():
    """Tests for coach database functions."""
    print("Testing coach_db.py...")

    import random
    from database.team_db import create_team
    test_team_id = create_team(f"Test Coach Team {random.randint(1000, 9999)}", 100000.0, 1000.0, 1000.0, 1000.0)

    # Create a test coach
    coach_name = "Test Coach"
    specialty = "Attacking"
    experience_level = 5
    coach_id = create_coach(coach_name, specialty, experience_level, test_team_id)
    assert coach_id is not None
    print(f"  Created coach with ID: {coach_id}")

    # Retrieve the coach
    retrieved_coach = get_coach(coach_id)
    assert retrieved_coach is not None
    assert retrieved_coach[1] == coach_name  # Check name (index 1)
    assert retrieved_coach[2] == specialty
    assert retrieved_coach[3] == experience_level
    assert retrieved_coach[4] == test_team_id

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
    add_coach_to_team(coach_id, test_team_id)
    team_coaches = get_coaches_for_team(test_team_id)
    assert any([coach[0] == coach_id for coach in team_coaches])
    print(f"   Added coach to team and verified.")

    # Remove coach from team and check
    remove_coach_from_team(coach_id, test_team_id)
    team_coaches = get_coaches_for_team(test_team_id)
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