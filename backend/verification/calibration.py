"""Read-only calibration against a named, attributable season."""
import argparse
import csv
import hashlib
import json
import math
import sqlite3
from pathlib import Path


def summarize(fixtures):
    fixtures = list(fixtures)
    if not fixtures:
        raise ValueError('Calibration needs completed fixtures')
    goals = [home + away for home, away in fixtures]
    mean = sum(goals) / len(goals)
    variance = sum((value - mean) ** 2 for value in goals) / max(1, len(goals) - 1)
    error = 1.96 * math.sqrt(variance / len(goals))
    return {'matches': len(goals), 'goals': sum(goals), 'goals_per_match': mean,
            'goals_mean_ci95': [mean - error, mean + error],
            'home_win_rate': sum(home > away for home, away in fixtures) / len(fixtures),
            'draw_rate': sum(home == away for home, away in fixtures) / len(fixtures),
            'away_win_rate': sum(home < away for home, away in fixtures) / len(fixtures)}


def reference_from_csv(source):
    with Path(source).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    summary = summarize((int(row['FTHG']), int(row['FTAG'])) for row in rows)
    summary.update({'competition': 'Premier League', 'season': '2023/24',
                    'source': 'https://www.football-data.co.uk/mmz4281/2324/E0.csv',
                    'official_goals_confirmation': 'https://www.premierleague.com/en/news/4316617',
                    'dataset_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                    'shots_per_match': sum(int(r['HS']) + int(r['AS']) for r in rows) / len(rows),
                    'yellow_cards_per_match': sum(int(r['HY']) + int(r['AY']) for r in rows) / len(rows),
                    'red_cards_per_match': sum(int(r['HR']) + int(r['AR']) for r in rows) / len(rows),
                    'xg': None, 'injuries': None})
    return summary


def audit_database(database, run_id, reference):
    with sqlite3.connect(f'file:{Path(database).resolve().as_posix()}?mode=ro', uri=True) as db:
        fixtures = db.execute('SELECT home_goals,away_goals FROM Match WHERE simulation_run_id=?', (run_id,)).fetchall()
    simulated = summarize(fixtures)
    return {'run_id': run_id, 'reference': reference, 'simulation': simulated,
            'differences': {key: simulated[key] - reference[key] for key in ('goals_per_match', 'home_win_rate', 'draw_rate', 'away_win_rate')},
            'status': 'measured_discrepancies', 'note': 'Scores are authoritative; this audit never changes the engine or results.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-csv', required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    reference = reference_from_csv(args.reference_csv)
    report = audit_database(args.database, args.run_id, reference)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['simulation'], indent=2))


if __name__ == '__main__':
    main()
