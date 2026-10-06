from types import SimpleNamespace as Player
from logic.squad_numbers import assign_squad_numbers


def make_player(name, position, rating=50, role='STARTER', number=None):
    return Player(name=name, position=position, attributes={'ability': {'value': rating}},
                  squad_role=role, jersey_number=number)


def test_numbers_are_unique_stable_and_follow_starting_positions():
    keeper = make_player('Starting keeper', 'GK', 60)
    backup = make_player('Backup keeper', 'GK', 70)
    players = [backup, keeper, make_player('Right back', 'RB'),
               make_player('Left back', 'LB'), make_player('Striker', 'ST'),
               make_player('Youth keeper', 'GK', 90, 'YOUTH')]
    assign_squad_numbers(players, {'Starting keeper': 38, 'Backup keeper': 0})
    assert keeper.jersey_number == 1
    assert players[2].jersey_number == 2
    assert players[3].jersey_number == 3
    assert players[4].jersey_number == 9
    assert len({p.jersey_number for p in players}) == len(players)
    before = {p.name: p.jersey_number for p in players}
    assign_squad_numbers(list(reversed(players)))
    assert before == {p.name: p.jersey_number for p in players}
    newcomer = make_player('New player', 'ST', number=9)
    assign_squad_numbers(players + [newcomer])
    assert len({p.jersey_number for p in players + [newcomer]}) == len(players) + 1


def test_youth_attributes_are_saved_during_full_season_sync(monkeypatch):
    from models.player import FootballPlayer
    from main import sync_simulation_state_to_db
    from database.player_db import get_player
    monkeypatch.setattr('main.save_live_season_report', lambda *args: None)
    youth = FootballPlayer('Youth attribute sync test', 16, 'GK')
    youth.squad_role = 'YOUTH'
    youth.attributes['goalkeeping']['reflexes'] = 64
    team = Player(name='Youth sync test club', team_id=None, budget=1,
                  weekly_budget=1, wage_budget=1, transfer_budget=1,
                  manager=None, players=[], youth_academy=[youth])
    sync_simulation_state_to_db(Player(teams=[team]), Player(free_agents=[]))
    saved = get_player(youth.player_id)
    assert saved['attributes']['goalkeeping']['reflexes'] == 64
    assert saved['jersey_number'] == 1
    youth.attributes['goalkeeping']['reflexes'] = 68
    sync_simulation_state_to_db(Player(teams=[team]), Player(free_agents=[]))
    assert get_player(youth.player_id)['attributes']['goalkeeping']['reflexes'] == 68


def test_attribute_sync_is_idempotent_before_transaction_flush():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from database.models import Base, Player as DBPlayer
    from logic.squad_numbers import sync_player_attributes
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as db:
        target = DBPlayer(name='Repeated sync', age=16, position='GK', potential=70,
                          wage=100, contract_length=2, squad_role='YOUTH')
        db.add(target)
        db.flush()
        source = Player(attributes={'goalkeeping': {'reflexes': 64}})
        sync_player_attributes(db, source, target)
        source.attributes['goalkeeping']['reflexes'] = 68
        sync_player_attributes(db, source, target)
        db.commit()
        assert len(target.attributes) == 1
        assert target.attributes[0].value == 68
