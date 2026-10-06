"""Assign missing squad numbers without changing historical match lineups."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from database.session import get_db_session
from database.models import Team, Match, MatchEvent
from logic.recorded_player_stats import recorded_player_totals
from logic.squad_numbers import assign_squad_numbers
from sqlalchemy import text

with get_db_session() as db:
    teams = db.query(Team).all()
    totals = recorded_player_totals(db.query(Match).all(), db.query(MatchEvent).all(),
                                   {team.team_id: team.name for team in teams})
    appearances = {name: stats['appearances'] for name, stats in totals.items()}
    for team in teams:
        assign_squad_numbers(team.players, appearances)
        numbers = [p.jersey_number for p in team.players]
        assert len(numbers) == len(set(numbers))
    db.flush()
    assert not db.execute(text('PRAGMA foreign_key_check')).fetchall()
    print(f'Assigned unique numbers to {sum(len(t.players) for t in teams)} players across {len(teams)} teams.')
