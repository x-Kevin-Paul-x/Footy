from pathlib import Path

from ml.evaluation import (
    build_evaluation_report,
    compare_policy_summaries,
    save_evaluation_report,
    summarize_episode_results,
)
from ml.footy_env import FootyEnv


def test_summarize_episode_results_aggregates_actions_and_positions():
    summary = summarize_episode_results(
        "trained",
        [
            {
                "reward": 10.0,
                "final_position": 2,
                "final_points": 70,
                "final_budget": 120_000_000,
                "final_squad_size": 24,
                "actions": {0: 3, 1: 1, 2: 0, 3: 2, 4: 0},
            },
            {
                "reward": 20.0,
                "final_position": 4,
                "final_points": 66,
                "final_budget": 115_000_000,
                "final_squad_size": 25,
                "actions": {0: 1, 1: 0, 2: 2, 3: 1, 4: 0},
            },
        ],
    )

    assert summary["episodes"] == 2
    assert summary["avg_reward"] == 15.0
    assert summary["best_position"] == 2
    assert summary["std_reward"] == 5.0
    assert summary["top_4_rate"] == 1.0
    assert summary["position_histogram"] == {"2": 1, "4": 1}
    assert summary["action_distribution"]["do_nothing"] == 4
    assert summary["action_distribution"]["buy_value_or_prime"] == 3


def test_compare_policy_summaries_returns_reward_and_position_deltas():
    trained = {
        "avg_reward": 25.0,
        "avg_points": 72.0,
        "avg_position": 3.0,
        "avg_budget": 100.0,
        "avg_squad_size": 24.0,
    }
    baseline = {
        "avg_reward": 10.0,
        "avg_points": 60.0,
        "avg_position": 6.0,
        "avg_budget": 80.0,
        "avg_squad_size": 23.0,
    }

    comparison = compare_policy_summaries(trained, baseline)

    assert comparison["reward_delta"] == 15.0
    assert comparison["points_delta"] == 12.0
    assert comparison["position_delta"] == 3.0


def test_build_and_save_evaluation_report(tmp_path: Path):
    report = build_evaluation_report(
        model_path=str(tmp_path / "missing_model.pt"),
        config={"episodes": 4, "fast_mode": True},
        runtime={"packages": {"torch": "2.10.0"}},
        policy_summaries={
            "trained": {
                "avg_reward": 30.0,
                "avg_position": 2.5,
                "avg_points": 75.0,
                "avg_budget": 100.0,
                "avg_squad_size": 24.0,
                "top_4_rate": 1.0,
                "title_rate": 0.5,
            },
            "random": {
                "avg_reward": 5.0,
                "avg_position": 8.0,
                "avg_points": 50.0,
                "avg_budget": 95.0,
                "avg_squad_size": 24.0,
                "top_4_rate": 0.0,
                "title_rate": 0.0,
            },
        },
        primary_policy_name="trained",
        policy_models={"trained": {"path": "trained.pt", "exists": False}},
    )

    report_path = save_evaluation_report(report, str(tmp_path))

    assert Path(report_path).exists()
    assert report["summary"]["best_policy_by_reward"] == "trained"
    assert report["summary"]["best_policy_by_position"] == "trained"
    assert report["comparisons"]["random"]["reward_delta"] == 25.0
    assert report["comparisons"]["random"]["top_4_rate_delta"] == 1.0
    assert report["policy_models"]["trained"]["path"] == "trained.pt"


def test_env_rollover_preserves_completed_season_summary():
    env = FootyEnv(num_teams=6, season_length=1, fast_mode=True)
    try:
        env.reset(seed=7)
        _, _, _, _, info = env.step(FootyEnv.ACTION_DO_NOTHING)

        assert info["season"] == 1
        assert info["week"] == 0
        assert info["completed_season_points"] == info["points"]
        assert info["completed_season_position"] == info["position"]
    finally:
        env.close()


def test_env_seeds_transfer_market_on_reset():
    env = FootyEnv(num_teams=6, season_length=4, fast_mode=True)
    try:
        env.reset(seed=11)

        assert env.transfer_market.is_transfer_window_open() is True
        assert len(env.transfer_market.transfer_list) >= 6
        assert len(env.transfer_market.free_agents) >= 6
    finally:
        env.close()


def test_env_weekly_progression_closes_summer_window():
    env = FootyEnv(num_teams=6, season_length=20, fast_mode=True)
    try:
        env.reset(seed=3)

        assert env.transfer_market.get_current_window() == "summer"

        for _ in range(9):
            env.step(FootyEnv.ACTION_DO_NOTHING)

        assert env.transfer_market.is_transfer_window_open() is False
        assert env.transfer_market.get_current_window() is None
    finally:
        env.close()