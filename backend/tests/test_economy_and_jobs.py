import os
import time
from types import SimpleNamespace

import numpy as np
import pytest

from logic.availability import apply_recorded_availability
from logic.replay.frame_timeline import TimelineWriter
from models.player import FootballPlayer
from models.team import Team
from models.transfer import LoanListing, TransferListing, TransferMarket


def test_attendance_is_cash_and_weekly_ledger_reconciles():
    team = Team('Ledger club', 100_000_000)
    opening = team.budget
    attendance = team.calculate_matchday_revenue()
    assert team.budget == pytest.approx(opening + attendance)
    weekly = team.process_weekly_finances()
    assert team.budget == pytest.approx(opening + attendance + weekly['net'])
    assert opening + sum(e['amount'] for e in team.financial_ledger) == pytest.approx(team.budget)
    with pytest.raises(ValueError):
        team.record_cashflow('bad', float('nan'))


def test_fixed_broadcast_pool_reconciles_and_rewards_position():
    clubs = [Team(f'Broadcast club {i}', 100_000_000) for i in range(20)]
    revenue = [team.update_broadcast_allocation(i + 1, pool=2_000_000_000) for i, team in enumerate(clubs)]
    assert sum(revenue) == pytest.approx(2_000_000_000)
    assert all(a > b for a, b in zip(revenue, revenue[1:]))


def test_year_end_surplus_distribution_limits_cash_inflation():
    team = Team('Stable finances', 100_000_000)
    team.record_cashflow('income', 90_000_000)
    dividend = team.settle_financial_year()
    assert dividend == pytest.approx(75_000_000)
    assert team.budget == pytest.approx(115_000_000)
    assert team.initial_budget + sum(e['amount'] for e in team.financial_ledger) == pytest.approx(team.budget)


def test_loan_moves_squad_splits_wages_and_returns_on_expiry(tmp_path):
    market = TransferMarket(log_path=str(tmp_path / 'transfers.log'))
    market.current_day = 1
    lender, borrower = Team('Parent', 100_000_000), Team('Borrower', 100_000_000)
    player = FootballPlayer('Loanee', 21, 'CM', wage=10_000)
    lender.add_player(player)
    listing = LoanListing(player, 100_000, 0.5, lender, 1, None, 1)
    market.loan_list.append(listing)
    cash = lender.budget + borrower.budget
    success, message = market.make_loan_offer(borrower, listing)
    assert success, message
    assert player not in lender.players and player in borrower.players
    assert player.wage == 5_000
    assert lender.loan_wage_obligations[player.name] == 5_000
    assert lender.budget + borrower.budget == pytest.approx(cash)
    for _ in range(30):
        market.advance_day([lender, borrower])
    assert player in lender.players and player not in borrower.players
    assert player.wage == 10_000 and player.loan_contract is None
    assert lender.loan_wage_obligations == {}


def test_release_clause_and_sell_on_conserve_fee(tmp_path):
    market = TransferMarket(log_path=str(tmp_path / 'transfers.log'))
    market.current_day = 1
    prior, seller, buyer = [Team(name, 200_000_000) for name in ('Prior', 'Seller', 'Buyer')]
    market.registered_teams = [prior, seller, buyer]
    player = FootballPlayer('Clause player', 24, 'ST', wage=1000)
    seller.add_player(player)
    player.desired_wage = 1000
    player.sell_on_clause = {'beneficiary': prior.name, 'percentage': 0.1}
    market.set_release_clause(player, 1_000_000)
    listing = TransferListing(player=player, asking_price=100_000_000, selling_team=seller, listed_date=1)
    market.transfer_list.append(listing)
    cash = sum(team.budget for team in market.registered_teams)
    old_prior = prior.budget
    success, message = market.make_transfer_offer(buyer, listing, 1_000_000, sell_on_percentage=0.15)
    assert success, message
    assert player in buyer.players and player not in seller.players
    assert prior.budget - old_prior == pytest.approx(100_000)
    assert player.sell_on_clause == {'beneficiary': seller.name, 'percentage': 0.15}
    assert sum(team.budget for team in market.registered_teams) == pytest.approx(cash - market.transfer_history[-1]['agent_fee'])


def test_existing_ban_served_before_new_red_card_and_injury_persists():
    player = FootballPlayer('Booked', 24, 'CB')
    player.suspended_matches = 1
    player.serve_suspension()
    prepared = SimpleNamespace(home_team=SimpleNamespace(players=[player]), away_team=SimpleNamespace(players=[]))
    apply_recorded_availability(prepared, {'events': [{'type': 'red_card', 'team': 'home', 'player': player.name}]})
    assert player.suspended_matches == 3
    assert not player.is_available_for_selection()
    player.apply_injury('severe')
    assert player.recovery_time > 42
    player.recover_from_injury(7)
    assert player.is_injured


def test_timeline_uses_emitted_frames_for_event_seek(tmp_path):
    class Sink:
        def append_data(self, frame):
            pass
        def close(self):
            pass
    writer = TimelineWriter(Sink(), tmp_path / 'test.mp4', 'match', 10)
    writer.mark('intro', 0, 0)
    for _ in range(30):
        writer.append_data(None)
    writer.mark('match_play', 0, 1, ['goal-1'])
    writer.append_data(None)
    writer.mark('goal_replay', 0, 1)
    for _ in range(70):
        writer.append_data(None)
    writer.mark('match_play', 1, 2, ['goal-2'])
    writer.append_data(None)
    writer.close()
    assert writer.timeline.events_pts_map == {'goal-1': 3.0, 'goal-2': 10.1}
    assert writer.timeline.total_frames == 102
    assert writer.timeline.total_duration_seconds == pytest.approx(10.2)


def _crashing_fake_worker(w_id, task_queue, result_queue, checkpoint, tikick, steps, mode, core, in_flight):
    # The first worker dies before dequeue; its assignment must remain recoverable.
    marker = checkpoint + '.crashed'
    if w_id == 0 and not os.path.exists(marker):
        with open(marker, 'w') as handle:
            handle.write('crashed')
        os._exit(9)
    while True:
        fixture = task_queue.get()
        if fixture is None:
            return
        time.sleep(0.01)
        result_queue.put({'success': True, 'match_id': fixture['match_id'], 'worker_id': w_id,
                          'lease_token': fixture['__lease_token'], 'data': {'match_id': fixture['match_id'], 'score': [1, 0]}})


def test_supervisor_recovers_death_before_dequeue_and_preserves_order(tmp_path, monkeypatch):
    import logic.simulation.simulation_process_pool as pool_module
    monkeypatch.setattr(pool_module, '_dynamic_queue_worker_runner', _crashing_fake_worker)
    fixtures = [{'match_id': 'first'}, {'match_id': 'second'}, {'match_id': 'third'}]
    result = pool_module.SimulationProcessPool(num_workers=2, use_affinity=False).run_batch(
        fixtures, str(tmp_path / 'checkpoint'), 'unused', max_steps=10)
    assert [item['match_id'] for item in result] == [item['match_id'] for item in fixtures]
    assert all(item['score'] == [1, 0] for item in result)


def test_synthetic_benchmark_observes_concurrency_and_topology_invariance(tmp_path):
    from benchmarks.benchmark_harness import BenchmarkConfig, BenchmarkRunner
    config = BenchmarkConfig(worker_counts=[1, 2], fixture_counts=[4], step_counts=[100],
                             replay_modes=['none'], repetitions=2, smoke=True, output_dir=tmp_path)
    report = BenchmarkRunner(config).run_suite()
    assert report['workload'] == 'synthetic_concurrent'
    assert report['topology_invariance'] and report['all_passed']
    assert [r['observed_workers'] for r in report['results']] == [1, 2]
    assert all(r['p95_latency_sec'] >= r['p50_latency_sec'] for r in report['results'])


def test_tactical_schedule_validates_and_applies_only_when_trailing():
    from logic.footy_grf_adapter import GRFTeamTactics
    from logic.tactical_schedule import apply_changes, validate_changes
    changes = [{'step': 100, 'team': 'home', 'condition': 'trailing', 'offensive_bias': 70}]
    validate_changes(changes, 200)
    home, away = GRFTeamTactics('Home'), GRFTeamTactics('Away')
    assert apply_changes(changes, 100, home, away, [1, 0]) == []
    assert home.offensive_bias == 50
    assert apply_changes(changes, 100, home, away, [0, 1])[0]['type'] == 'tactical_change'
    assert home.offensive_bias == 70 and away.offensive_bias == 50
    with pytest.raises(ValueError):
        validate_changes([{'step': 100, 'team': 'away', 'tempo': 101}], 200)
