"""Run-scoped read models and a reconciled financial ledger."""
import json
from datetime import datetime, timezone

from database.models import CampaignSnapshot, FinancialEntry
from database.session import get_db_session


def checkpoint_campaign(league, matches_played):
    run_id = getattr(league, 'simulation_run_id', None)
    if not run_id:
        return
    teams = []
    with get_db_session() as db:
        for team in league.teams:
            entries = getattr(team, 'financial_ledger', [])
            last = db.query(FinancialEntry.entry_number).filter_by(run_id=run_id, team_name=team.name).order_by(FinancialEntry.entry_number.desc()).first()
            last_number = last[0] if last else 0
            for entry in entries:
                if entry['entry_number'] > last_number:
                    db.add(FinancialEntry(run_id=run_id, team_name=team.name, season_year=league.season_year, **entry))
            players = [{'id': p.player_id, 'name': p.name, 'age': p.age, 'position': p.position,
                        'attributes': p.attributes, 'stats': p.stats, 'wage': p.wage,
                        'contract_length': p.contract_length,
                        'suspended_matches': getattr(p, 'suspended_matches', 0),
                        'injury_days': getattr(p, 'recovery_time', 0),
                        'release_clause': getattr(p, 'release_clause', None),
                        'sell_on_clause': getattr(p, 'sell_on_clause', None),
                        'loan_contract': getattr(p, 'loan_contract', None)} for p in team.players]
            teams.append({'name': team.name, 'team_id': team.team_id, 'finances': team.get_financials(),
                          'players': players, 'manager': team.manager.get_stats() if team.manager else None})
        state = {'snapshot_version': 1, 'run_id': run_id, 'season_year': league.season_year,
                 'matches_played': matches_played, 'standings': league.standings, 'teams': teams}
        row = db.get(CampaignSnapshot, (run_id, league.season_year))
        if row is None:
            row = CampaignSnapshot(run_id=run_id, season_year=league.season_year)
            db.add(row)
        row.matches_played = matches_played
        row.state_json = json.dumps(state, default=str)
        row.created_at = datetime.now(timezone.utc).isoformat()


def get_campaign(run_id, season_year):
    with get_db_session() as db:
        row = db.get(CampaignSnapshot, (run_id, season_year))
        return json.loads(row.state_json) if row else None


def financial_ledger(run_id, team_name):
    with get_db_session() as db:
        rows = db.query(FinancialEntry).filter_by(run_id=run_id, team_name=team_name).order_by(FinancialEntry.entry_number).all()
        entries = [{k: getattr(row, k) for k in ('entry_number', 'season_year', 'category', 'amount', 'balance', 'description')} for row in rows]
        opening = entries[0]['balance'] - entries[0]['amount'] if entries else 0
        closing = entries[-1]['balance'] if entries else opening
        return {'run_id': run_id, 'team': team_name, 'entries': entries, 'opening_balance': opening,
                'closing_balance': closing, 'net_cashflow': sum(e['amount'] for e in entries)}
