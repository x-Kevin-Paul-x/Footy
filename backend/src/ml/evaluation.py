import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

ACTION_NAMES = {
    0: "do_nothing",
    1: "scout_or_youth",
    2: "buy_cheap",
    3: "buy_value",
    4: "buy_star",
}


def summarize_episode_results(policy_name: str, episodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not episodes_data:
        return {
            "policy_name": policy_name,
            "episodes": 0,
            "avg_reward": 0.0,
            "std_reward": 0.0,
            "median_reward": 0.0,
            "best_reward": 0.0,
            "worst_reward": 0.0,
            "avg_position": 0.0,
            "best_position": 0,
            "avg_points": 0.0,
            "avg_budget": 0.0,
            "avg_squad_size": 0.0,
            "top_4_rate": 0.0,
            "title_rate": 0.0,
            "position_histogram": {},
            "action_distribution": {name: 0 for name in ACTION_NAMES.values()},
        }

    rewards = [e.get("reward", 0.0) for e in episodes_data]
    positions = [e.get("final_position", 1) for e in episodes_data]
    points = [e.get("final_points", 0) for e in episodes_data]
    budgets = [e.get("final_budget", 0) for e in episodes_data]
    squad_sizes = [e.get("final_squad_size", 0) for e in episodes_data]

    n = len(episodes_data)
    avg_reward = sum(rewards) / n
    avg_pos = sum(positions) / n
    avg_pts = sum(points) / n
    avg_bud = sum(budgets) / n
    avg_sq = sum(squad_sizes) / n

    variance = sum((r - avg_reward) ** 2 for r in rewards) / n
    std_reward = math.sqrt(variance)

    best_position = min(positions)
    top_4_count = sum(1 for p in positions if p <= 4)
    title_count = sum(1 for p in positions if p == 1)

    position_histogram = {}
    for p in positions:
        key = str(p)
        position_histogram[key] = position_histogram.get(key, 0) + 1

    action_counts = {name: 0 for name in ACTION_NAMES.values()}
    for e in episodes_data:
        actions = e.get("actions", {})
        for act_key, count in actions.items():
            act_int = int(act_key) if isinstance(act_key, (int, str)) else 0
            act_name = ACTION_NAMES.get(act_int, "do_nothing")
            action_counts[act_name] = action_counts.get(act_name, 0) + count

    return {
        "policy_name": policy_name,
        "episodes": n,
        "avg_reward": avg_reward,
        "std_reward": std_reward,
        "median_reward": sorted(rewards)[n // 2],
        "best_reward": max(rewards),
        "worst_reward": min(rewards),
        "avg_position": avg_pos,
        "best_position": best_position,
        "avg_points": avg_pts,
        "avg_budget": avg_bud,
        "avg_squad_size": avg_sq,
        "top_4_rate": top_4_count / n,
        "title_rate": title_count / n,
        "position_histogram": position_histogram,
        "action_distribution": action_counts,
    }


def compare_policy_summaries(trained: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "reward_delta": trained.get("avg_reward", 0.0) - baseline.get("avg_reward", 0.0),
        "points_delta": trained.get("avg_points", 0.0) - baseline.get("avg_points", 0.0),
        "position_delta": baseline.get("avg_position", 0.0) - trained.get("avg_position", 0.0),
        "top_4_rate_delta": trained.get("top_4_rate", 0.0) - baseline.get("top_4_rate", 0.0),
        "title_rate_delta": trained.get("title_rate", 0.0) - baseline.get("title_rate", 0.0),
        "budget_delta": trained.get("avg_budget", 0.0) - baseline.get("avg_budget", 0.0),
        "squad_size_delta": trained.get("avg_squad_size", 0.0) - baseline.get("avg_squad_size", 0.0),
    }


def build_evaluation_report(
    model_path: str,
    config: Dict[str, Any],
    runtime: Dict[str, Any],
    policy_summaries: Dict[str, Dict[str, Any]],
    primary_policy_name: str = "trained",
    policy_models: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    comparisons = {}
    primary_summary = policy_summaries.get(primary_policy_name, {})

    for name, summary in policy_summaries.items():
        if name != primary_policy_name:
            comparisons[name] = compare_policy_summaries(primary_summary, summary)

    best_reward_policy = max(
        policy_summaries.keys(),
        key=lambda k: policy_summaries[k].get("avg_reward", -float("inf")),
    )
    best_position_policy = min(
        policy_summaries.keys(),
        key=lambda k: policy_summaries[k].get("avg_position", float("inf")),
    )

    return {
        "generated_at": datetime.now().isoformat(),
        "config": config,
        "runtime": runtime,
        "model_path": model_path,
        "policy_models": policy_models or {},
        "policies": policy_summaries,
        "comparisons": comparisons,
        "summary": {
            "primary_policy": primary_policy_name,
            "best_policy_by_reward": best_reward_policy,
            "best_policy_by_position": best_position_policy,
        },
    }


def save_evaluation_report(report: Dict[str, Any], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = f"evaluation_{int(datetime.now().timestamp())}.json"
    file_path = Path(output_dir) / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return str(file_path)
