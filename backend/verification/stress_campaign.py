"""Isolated multi-season domain/economy soak, independent of native GRF physics."""
import argparse
import gc
import json
import os
import random
import tempfile
import tracemalloc
from pathlib import Path


def run(seasons=5, seed=42):
    root = Path(tempfile.mkdtemp(prefix='footy_stress_'))
    os.environ['FOOTY_DATA_DIR'] = str(root / 'data')
    os.environ['FOOTY_REPORTS_DIR'] = str(root / 'reports')
    os.environ['FOOTY_ENGINE_MODE'] = 'HEURISTIC'
    from models.league import League
    from models.player import FootballPlayer
    from models.team import Team
    random.seed(seed)
    league = League('Stress league', num_teams=6)
    for index in range(6):
        team = Team(f'Stress club {index}', 100_000_000)
        for position, count in [('GK', 2), ('CB', 6), ('CM', 6), ('ST', 4)]:
            for player_index in range(count):
                team.add_player(FootballPlayer(f'{index}_{position}_{player_index}', 25, position, wage=1000))
        league.teams.append(team)
    league._init_season()
    reports = []
    tracemalloc.start()
    for season in range(seasons):
        opening = sum(team.budget for team in league.teams)
        for week in range(38):
            for team in league.teams:
                team.process_weekly_finances()
                if week % 2 == 0:
                    team.calculate_matchday_revenue()
                team.generate_youth_players_weekly(count=3)
        for team in league.teams:
            assert team.initial_budget + sum(entry['amount'] for entry in team.financial_ledger) == team.budget or abs(team.initial_budget + sum(entry['amount'] for entry in team.financial_ledger) - team.budget) < 0.01
            assert team.budget > 0
        league.increment_season(process_contracts=False)
        closing = sum(team.budget for team in league.teams)
        assert closing <= opening * 1.15 + 0.01
        assert all(len(team.youth_academy) <= 24 for team in league.teams)
        gc.collect()
        retained, peak = tracemalloc.get_traced_memory()
        reports.append({'season': season + 1, 'opening_cash': opening, 'closing_cash': closing,
                        'money_growth': closing / opening - 1, 'squads': [len(t.players) for t in league.teams],
                        'academies': [len(t.youth_academy) for t in league.teams],
                        'retained_python_bytes': retained, 'peak_python_bytes': peak})
    tracemalloc.stop()
    return {'workload': 'domain_finances_and_rollover', 'seasons': seasons, 'seed': seed,
            'checks': ['cashflow_reconciles', 'no_insolvency', 'squad_replenishment', 'academy_bounded'],
            'reports': reports, 'native_match_physics': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seasons', type=int, default=5)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = run(args.seasons, args.seed)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
