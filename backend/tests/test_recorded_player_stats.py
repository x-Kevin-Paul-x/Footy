import json
from types import SimpleNamespace as Row
from logic.recorded_player_stats import recorded_player_totals, describe_match_event


def test_recorded_stats_include_scorer_and_real_substitution_minutes():
    match = Row(match_id=10, home_team_id=1, away_team_id=2,
                home_goals=0, away_goals=1, date='2026-08-01')
    def event(kind, payload, side='away', minute=0, player=''):
        return Row(match_id=10, type=kind, details=json.dumps(payload),
                   team=side, minute=minute, player=player)
    rows = [event('home_lineup', [{'name': 'Home Player'}], 'home'),
            event('away_lineup', [{'name': 'Helen Booker'}]),
            event('goal', {'canonical_event': {'type': 'goal', 'player': 'Helen Booker', 'team': 'away'}}),
            event('substitutions', [{'player_out': 'Helen Booker', 'player_in': 'Replacement',
                                     'minute': 70, 'team': 'away'}])]
    stats = recorded_player_totals([match], rows, {1: 'Liverpool', 2: 'Luton'})
    assert stats['Helen Booker']['goals'] == 1
    assert stats['Helen Booker']['appearances'] == 1
    assert stats['Helen Booker']['minutes_played'] == 70
    assert stats['Replacement']['minutes_played'] == 20
    assert stats['Helen Booker']['match_history'][0]['opponent'] == 'Liverpool'
    assert stats['Helen Booker']['assists_recorded'] is False


def test_event_descriptions_preserve_names_and_match_intervals():
    assert describe_match_event({'type': 'goal', 'player': 'Helen Booker', 'score': '2-1'}) == 'Goal — Helen Booker. Score: 2-1'
    assert describe_match_event({'type': 'half_time', 'score': '1-0'}) == 'Half time — 1-0'
    assert describe_match_event({'type': 'substitution', 'player_in': 'A', 'player_out': 'B'}) == 'Substitution — A on for B'
    assert describe_match_event({'type': 'goal', 'details': 'Original description'}) == 'Original description'


def test_report_and_match_api_use_saved_player_data_and_bench_provenance():
    from database.session import get_db_session
    from database.models import Team, Player, PlayerAttribute, SimulationRun
    from database.match_db import save_match_to_db, get_match_details
    from api_fastapi import build_live_season_report_from_db

    with get_db_session() as db:
        home = Team(name='Profile Test Home', budget=1, weekly_budget=1,
                    transfer_budget=1, wage_budget=1)
        away = Team(name='Profile Test Away', budget=1, weekly_budget=1,
                    transfer_budget=1, wage_budget=1)
        db.add_all([home, away])
        db.flush()
        home_id, away_id = home.team_id, away.team_id
        player = Player(name='Profile Test Scorer', age=25, position='ST',
                        team_id=away_id, potential=90, wage=100,
                        contract_length=2, squad_role='starter')
        db.add(player)
        db.flush()
        db.add(PlayerAttribute(player_id=player.player_id,
                               attribute_type='shooting', sub_attribute='finishing', value=53))
        db.add(SimulationRun(run_id='profile_test_run', season_year=2099,
                             created_at='2099-01-01', status='completed'))
        db.commit()

    payload = dict(date='2099-08-01', home_team_id=home_id, away_team_id=away_id,
                   score=[0, 1], home_lineup=[{'name': 'Profile Test Defender', 'position': 'CB'}],
                   away_lineup=[{'name': 'Profile Test Scorer', 'position': 'ST'}],
                   away_bench=[{'name': 'Profile Test Reserve', 'position': 'ST'}],
                   events=[{'type': 'goal', 'minute': 84, 'player': 'Profile Test Scorer',
                            'team': 'away', 'score': '0-1'},
                           {'type': 'half_time', 'minute': 45, 'team': 'home', 'score': '0-0'}])
    match_id = save_match_to_db(payload, 2099, 1, simulation_run_id='profile_test_run')
    assert match_id is not None
    details = get_match_details(match_id)
    assert details['away_bench_recorded'] is True
    assert details['home_bench_recorded'] is False
    assert details['away_bench'][0]['name'] == 'Profile Test Reserve'
    assert next(e for e in details['events'] if e['type'] == 'goal')['details'].startswith('Goal — Profile Test Scorer')
    assert next(e for e in details['events'] if e['type'] == 'half_time')['team'] == 'both'

    report = build_live_season_report_from_db(2099)
    scorer = next(p for t in report['all_teams_details'] for p in t['players']
                  if p['name'] == 'Profile Test Scorer')
    assert scorer['overall_rating'] == 53
    assert scorer['attributes']['shooting']['finishing'] == 53
    assert scorer['stats']['goals'] == scorer['stats']['appearances'] == 1
    assert scorer['form'] == []
    assert scorer['match_history'][0]['match_id'] == match_id

    payload['home_bench'] = []
    payload['substitutions'] = [{'minute': 85, 'team': 'away',
                                'player_out': 'Profile Test Scorer',
                                'player_in': 'Profile Test Reserve'}]
    save_match_to_db(payload, 2099, 1, simulation_run_id='profile_test_run')
    updated = get_match_details(match_id)
    assert updated['home_bench_recorded'] is True
    sub = next(e for e in updated['events'] if e['type'] == 'substitution')
    assert sub['details'] == 'Substitution — Profile Test Reserve on for Profile Test Scorer'

    payload.pop('substitutions')
    payload['events'].append(dict(type='substitution', minute=85, team='away',
                                  player_in='Profile Test Reserve', player_out='Profile Test Scorer'))
    save_match_to_db(payload, 2099, 1, simulation_run_id='profile_test_run')
    updated = get_match_details(match_id)
    assert len(updated['substitutions']) == 1
    assert len([e for e in updated['events'] if e['type'] == 'substitution']) == 1
