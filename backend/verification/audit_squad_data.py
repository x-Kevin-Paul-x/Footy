"""Check actual persisted squad data in the latest isolated season."""
import json
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parent
latest = json.loads((root / 'latest.json').read_text())
output = Path(latest['output'])
conn = sqlite3.connect(f'file:{output / "data/football_sim.db"}?mode=ro', uri=True)
failures = []
players = conn.execute('SELECT player_id,team_id,jersey_number FROM Player').fetchall()
missing_attributes = conn.execute('SELECT COUNT(*) FROM Player p WHERE NOT EXISTS '
                                 '(SELECT 1 FROM PlayerAttributes a WHERE a.player_id=p.player_id)').fetchone()[0]
if missing_attributes:
    failures.append(f'{missing_attributes} players without attributes')
numbers = {}
for player_id, team_id, number in players:
    if team_id is None:
        continue
    used = numbers.setdefault(team_id, set())
    if not isinstance(number, int) or number < 1 or number in used:
        failures.append(f'Invalid or duplicated squad number: player {player_id}, team {team_id}, number {number}')
    used.add(number)
matches = conn.execute('SELECT match_id FROM Match WHERE simulation_run_id=?', (latest['run_id'],)).fetchall()
bench_sizes = []
for (match_id,) in matches:
    events = dict(conn.execute("SELECT type,details FROM MatchEvent WHERE match_id=? "
                              "AND type IN ('home_bench','away_bench','home_lineup','away_lineup')", (match_id,)))
    for side in ('home', 'away'):
        if side + '_bench' not in events:
            failures.append(f'Match {match_id}: {side} bench missing')
        else:
            bench = json.loads(events[side + '_bench'])
            bench_sizes.append(len(bench))
            lineup = json.loads(events.get(side + '_lineup', '[]'))
            if len(lineup) != 11:
                failures.append(f'Match {match_id}: {side} has {len(lineup)} starters')
            match_numbers = [p.get('number') for p in lineup + bench]
            if any(not isinstance(n, int) or n < 1 for n in match_numbers) or len(set(match_numbers)) != len(match_numbers):
                failures.append(f'Match {match_id}: {side} invalid lineup/bench numbers')
result = {'passed': not failures, 'players': len(players), 'clubs': len(numbers),
          'matches': len(matches), 'benches_recorded': len(bench_sizes),
          'bench_size_range': [min(bench_sizes), max(bench_sizes)] if bench_sizes else [],
          'players_without_attributes': missing_attributes,
          'native_substitutions_supported': False, 'failures': failures}
(output / 'squad_audit.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
