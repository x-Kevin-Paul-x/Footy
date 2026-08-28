"""CLI entry point for training, evaluating, and comparing Action-Masked DQN agents."""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend/src to path if not present
BACKEND_SRC = Path(__file__).resolve().parent.parent
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

import numpy as np

from ml.dqn_agent import DQNAgent, TORCH_AVAILABLE
from ml.footy_env import FootyEnv
from ml.evaluation import (
    build_evaluation_report,
    save_evaluation_report,
    summarize_episode_results,
)


def run_episode(
    env: FootyEnv,
    agent: Optional[DQNAgent] = None,
    policy: str = "trained",
    training: bool = False,
    epsilon: float = 0.0,
) -> Dict[str, Any]:
    obs, info = env.reset()
    total_reward = 0.0
    done = False
    step_count = 0

    while not done:
        action_mask = env.get_action_mask()

        if policy == "trained" and agent is not None:
            action = agent.select_action(obs, action_mask=action_mask, training=training, epsilon=epsilon)
        elif policy == "random":
            valid_actions = np.where(action_mask > 0.5)[0]
            action = int(np.random.choice(valid_actions)) if len(valid_actions) > 0 else 0
        elif policy == "do_nothing":
            action = 0
        elif policy == "youth_focus":
            action = 1 if action_mask[1] > 0.5 else 0
        else:
            action = 0

        next_obs, reward, terminated, truncated, next_info = env.step(action)
        done = terminated or truncated
        total_reward += reward

        if training and agent is not None:
            next_mask = env.get_action_mask()
            agent.store_transition(obs, action, reward, next_obs, done, action_mask, next_mask)
            agent.train_step(batch_size=64)

        obs = next_obs
        info = next_info
        step_count += 1

    return {
        "reward": total_reward,
        "final_position": info.get("final_position", 1),
        "final_points": info.get("final_points", 0),
        "final_budget": info.get("final_budget", 0),
        "final_squad_size": info.get("final_squad_size", 0),
        "actions": info.get("actions", {}),
    }


def train_agent(args):
    print(f"--- Training Action-Masked DQN for {args.episodes} episodes ---")
    if not TORCH_AVAILABLE:
        print("Error: PyTorch is required to train DQN.")
        sys.exit(1)

    env = FootyEnv(num_teams=args.teams, season_length=args.season_length, fast_mode=args.fast_mode)
    agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim, hidden_dim=128, learning_rate=3e-4)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    eps_start = 1.0
    eps_end = 0.05
    eps_decay = max(1, args.episodes * 0.75)

    best_reward = -float("inf")
    start_time = time.time()

    for episode in range(1, args.episodes + 1):
        epsilon = max(eps_end, eps_start - (eps_start - eps_end) * (episode / eps_decay))
        result = run_episode(env, agent=agent, policy="trained", training=True, epsilon=epsilon)

        if result["reward"] > best_reward:
            best_reward = result["reward"]
            best_path = output_dir / "dqn_best.pt"
            agent.save(best_path)

        if episode % max(1, args.episodes // 10) == 0 or episode == args.episodes:
            print(
                f"Episode {episode:4d}/{args.episodes} | "
                f"Reward: {result['reward']:6.1f} | "
                f"Pts: {result['final_points']:2d} | "
                f"Pos: {result['final_position']:2d} | "
                f"Budget: £{result['final_budget']/1e6:5.1f}M | "
                f"Eps: {epsilon:.3f}"
            )

    final_path = output_dir / "dqn_final.pt"
    agent.save(final_path)
    elapsed = time.time() - start_time
    print(f"Training completed in {elapsed:.2f}s. Checkpoints saved to {output_dir}")


def evaluate_agent(args):
    print(f"--- Evaluating model {args.model} against baselines ({args.episodes} episodes each) ---")
    env = FootyEnv(num_teams=args.teams, season_length=args.season_length, fast_mode=args.fast_mode)
    agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim)
    
    if args.model and Path(args.model).exists():
        agent.load(args.model)
        print(f"Loaded model weights from {args.model}")
    else:
        print(f"Notice: Model {args.model} not found; running with initialized weights.")

    start_time = time.time()
    policies_to_test = ["trained", "random", "do_nothing", "youth_focus"]
    summaries = {}

    for pol in policies_to_test:
        episodes_data = []
        for _ in range(args.episodes):
            res = run_episode(env, agent=agent, policy=pol, training=False, epsilon=0.0)
            episodes_data.append(res)
        summaries[pol] = summarize_episode_results(pol, episodes_data)

    runtime = {
        "elapsed_seconds": round(time.time() - start_time, 2),
        "episodes_per_policy": args.episodes,
    }
    config = {
        "num_teams": args.teams,
        "season_length": args.season_length,
        "fast_mode": args.fast_mode,
    }

    report = build_evaluation_report(
        model_path=args.model or "none",
        config=config,
        runtime=runtime,
        policy_summaries=summaries,
        primary_policy_name="trained",
    )

    report_dir = args.report_dir or "ml/reports"
    report_file = save_evaluation_report(report, report_dir)
    print(f"Evaluation report saved to: {report_file}")
    print(f"Primary Policy Avg Reward: {summaries['trained']['avg_reward']:.2f}, Avg Rank: {summaries['trained']['avg_position']:.2f}")


def compare_agents(args):
    print(f"--- Comparing models: {args.models} ({args.episodes} episodes each) ---")
    env = FootyEnv(num_teams=args.teams, season_length=args.season_length, fast_mode=args.fast_mode)
    start_time = time.time()
    summaries = {}
    policy_models = {}

    for idx, model_path in enumerate(args.models):
        policy_name = f"model_{Path(model_path).stem}"
        agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim)
        if Path(model_path).exists():
            agent.load(model_path)
            print(f"Loaded: {model_path}")
        else:
            print(f"Warning: {model_path} not found.")

        policy_models[policy_name] = model_path
        episodes_data = []
        for _ in range(args.episodes):
            res = run_episode(env, agent=agent, policy="trained", training=False, epsilon=0.0)
            episodes_data.append(res)
        summaries[policy_name] = summarize_episode_results(policy_name, episodes_data)

    # Baseline comparison
    baseline_data = [run_episode(env, policy="random") for _ in range(args.episodes)]
    summaries["baseline_random"] = summarize_episode_results("baseline_random", baseline_data)

    runtime = {
        "elapsed_seconds": round(time.time() - start_time, 2),
        "episodes_per_policy": args.episodes,
    }
    config = {
        "num_teams": args.teams,
        "season_length": args.season_length,
        "fast_mode": args.fast_mode,
    }

    primary = list(summaries.keys())[0]
    report = build_evaluation_report(
        model_path=";".join(args.models),
        config=config,
        runtime=runtime,
        policy_summaries=summaries,
        primary_policy_name=primary,
        policy_models=policy_models,
    )

    report_dir = args.report_dir or "ml/reports"
    report_file = save_evaluation_report(report, report_dir)
    print(f"Comparison report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Action-Masked DQN CLI for Footy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train
    train_parser = subparsers.add_parser("train", help="Train Action-Masked DQN")
    train_parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes")
    train_parser.add_argument("--teams", type=int, default=6, help="Number of teams in simulation")
    train_parser.add_argument("--season-length", type=int, default=20, help="Season fixture length")
    train_parser.add_argument("--fast-mode", action="store_true", default=True, help="Fast simulation mode")
    train_parser.add_argument("--output-dir", type=str, default="ml/models", help="Model checkpoint dir")

    # Eval
    eval_parser = subparsers.add_parser("eval", help="Evaluate DQN against baselines")
    eval_parser.add_argument("--model", type=str, default="ml/models/dqn_best.pt", help="Path to model checkpoint")
    eval_parser.add_argument("--episodes", type=int, default=10, help="Evaluation episodes")
    eval_parser.add_argument("--teams", type=int, default=6, help="Number of teams")
    eval_parser.add_argument("--season-length", type=int, default=20, help="Season fixture length")
    eval_parser.add_argument("--fast-mode", action="store_true", default=True, help="Fast simulation mode")
    eval_parser.add_argument("--report-dir", type=str, default="ml/reports", help="Output directory for reports")

    # Compare
    comp_parser = subparsers.add_parser("compare", help="Compare multiple checkpoints")
    comp_parser.add_argument("--models", nargs="+", required=True, help="List of model checkpoint paths")
    comp_parser.add_argument("--episodes", type=int, default=10, help="Episodes per checkpoint")
    comp_parser.add_argument("--teams", type=int, default=6, help="Number of teams")
    comp_parser.add_argument("--season-length", type=int, default=20, help="Season fixture length")
    comp_parser.add_argument("--fast-mode", action="store_true", default=True, help="Fast simulation mode")
    comp_parser.add_argument("--report-dir", type=str, default="ml/reports", help="Output directory for reports")

    args = parser.parse_args()
    if args.command == "train":
        train_agent(args)
    elif args.command == "eval":
        evaluate_agent(args)
    elif args.command == "compare":
        compare_agents(args)


if __name__ == "__main__":
    main()
