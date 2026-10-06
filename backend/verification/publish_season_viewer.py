"""Refresh a local, reviewable season viewer from the isolated verification DB."""
import json
import sqlite3
import shutil
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
latest = json.loads((ROOT / 'verification/latest.json').read_text())
output = Path(latest['output'])
shutil.copy2(ROOT / 'verification/season_viewer.html', output / 'index.html')
while True:
    connection = sqlite3.connect(output / 'data/football_sim.db')
    connection.row_factory = sqlite3.Row
    names = dict(connection.execute('SELECT team_id,name FROM Team'))
    matches = connection.execute('SELECT * FROM Match WHERE simulation_run_id=? ORDER BY match_number',
                                 (latest['run_id'],)).fetchall()
    table = {i: dict(team=name,played=0,gf=0,ga=0,points=0) for i,name in names.items()}
    fixtures = []
    for m in matches:
        fixture = f"match_{m['season_year']}_{m['home_team_id']}_{m['away_team_id']}"
        home, away = table[m['home_team_id']], table[m['away_team_id']]
        hg, ag = m['home_goals'], m['away_goals']
        for team,gf,ga in ((home,hg,ag),(away,ag,hg)):
            team['played'] += 1
            team['gf'] += gf
            team['ga'] += ga
            team['points'] += 3 if gf>ga else 1 if gf==ga else 0
        fixtures.append(dict(number=m['match_number'],fixture=fixture,home=home['team'],away=away['team'],
            score=[hg,ag],view=(output / f'replay_views/trace_{fixture}.json').is_file()))
    connection.close()
    recordings = output / 'reports/recordings' / latest['run_id']
    audits = [json.loads(p.read_text()) for p in recordings.glob('trace_*.audit.json')]
    passed = [a for a in audits if a['passed']]
    season_audit = output / 'season_audit.json'
    complete = season_audit.is_file() and json.loads(season_audit.read_text())['passed'] and len(passed)==380 and all(m['view'] for m in fixtures)
    data = dict(run_id=latest['run_id'],matches=fixtures,checked=len(passed),
        frames=sum(a['frames_compared'] for a in passed),goals=sum(sum(m['score']) for m in fixtures),
        complete=complete,standings=sorted(table.values(),key=lambda t:(t['points'],t['gf']-t['ga'],t['gf']),reverse=True))
    temporary = output / 'viewer_data.json.tmp'
    temporary.write_text(json.dumps(data,separators=(',',':')))
    temporary.replace(output / 'viewer_data.json')
    if complete:
        print('FULL_SEASON_VIEWER_READY',output / 'index.html',flush=True)
        break
    time.sleep(5)
