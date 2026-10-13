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
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    obs, info = env.reset(seed=seed)
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
        elif policy == "rule_based":
            # Prefer value signings, then cheap depth; never exceed the mask.
            action = next((a for a in (3, 2, 1, 0) if action_mask[a] > 0.5), 0)
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
    from logic.evaluation_service import seed_everything
    import json
    import torch
    torch.set_num_threads(1)
    seed_everything(args.seed)

    env = FootyEnv(num_teams=args.teams, season_length=args.season_length, fast_mode=args.fast_mode)
    agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim, hidden_dim=128, learning_rate=3e-4)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    eps_start = 1.0
    eps_end = 0.05
    eps_decay = max(1, args.episodes * 0.75)

    best_reward = -float("inf")
    start_time = time.time()
    curve = []

    for episode in range(1, args.episodes + 1):
        epsilon = max(eps_end, eps_start - (eps_start - eps_end) * (episode / eps_decay))
        result = run_episode(env, agent=agent, policy="trained", training=True, epsilon=epsilon, seed=args.seed + episode)
        curve.append({'episode': episode, 'seed': args.seed + episode, 'reward': result['reward'],
                      'points': result['final_points'], 'position': result['final_position'], 'epsilon': epsilon})

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
    (output_dir / 'training_curve.json').write_text(json.dumps({'config': vars(args), 'episodes': curve}, indent=2), encoding='utf-8')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        figure, axis = plt.subplots(figsize=(8, 4))
        axis.plot([row['episode'] for row in curve], [row['reward'] for row in curve], alpha=0.4, label='Episode reward')
        window = min(10, len(curve))
        average = np.convolve([row['reward'] for row in curve], np.ones(window) / window, mode='valid')
        axis.plot(range(window, len(curve) + 1), average, label=f'{window}-episode mean')
        axis.set(xlabel='Training episode', ylabel='Management reward', title=f'DQN training, seed {args.seed}')
        axis.legend()
        figure.tight_layout()
        figure.savefig(output_dir / 'training_curve.svg')
        plt.close(figure)
    except ImportError:
        print('Training log saved; install matplotlib to render the curve')
    env.close()
    elapsed = time.time() - start_time
    print(f"Training completed in {elapsed:.2f}s. Checkpoints saved to {output_dir}")


def evaluate_agent(args):
    from logic.evaluation_service import evaluate
    model = Path(args.model).resolve()
    report = evaluate({'models': [model.name], 'episodes': args.episodes, 'seed': args.seed,
                       'teams': args.teams, 'season_length': args.season_length, 'fast_mode': True},
                      model.parent, args.report_dir)
    print(f"Evaluation report: {report['report_name']}")


def compare_agents(args):
    from logic.evaluation_service import evaluate
    models = [Path(model).resolve() for model in args.models]
    if len({model.parent for model in models}) != 1:
        raise ValueError('Compared models must share one model directory')
    report = evaluate({'models': [model.name for model in models], 'episodes': args.episodes,
                       'seed': args.seed, 'teams': args.teams,
                       'season_length': args.season_length, 'fast_mode': True},
                      models[0].parent, args.report_dir)
    print(f"Comparison report: {report['report_name']}")


def main():
    parser = argparse.ArgumentParser(description="Action-Masked DQN CLI for Footy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train
    train_parser = subparsers.add_parser("train", help="Train Action-Masked DQN")
    train_parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes")
    train_parser.add_argument('--seed', type=int, default=42)
    train_parser.add_argument("--teams", type=int, default=6, help="Number of teams in simulation")
    train_parser.add_argument("--season-length", type=int, default=20, help="Season fixture length")
    train_parser.add_argument("--fast-mode", action="store_true", default=True, help="Fast simulation mode")
    train_parser.add_argument("--output-dir", type=str, default="ml/models", help="Model checkpoint dir")

    # Eval
    eval_parser = subparsers.add_parser("eval", help="Evaluate DQN against baselines")
    eval_parser.add_argument("--model", type=str, default="ml/models/dqn_best.pt", help="Path to model checkpoint")
    eval_parser.add_argument("--seed", type=int, default=1000)
    eval_parser.add_argument("--episodes", type=int, default=10, help="Evaluation episodes")
    eval_parser.add_argument("--teams", type=int, default=6, help="Number of teams")
    eval_parser.add_argument("--season-length", type=int, default=20, help="Season fixture length")
    eval_parser.add_argument("--fast-mode", action="store_true", default=True, help="Fast simulation mode")
    eval_parser.add_argument("--report-dir", type=str, default="ml/reports", help="Output directory for reports")

    # Compare
    comp_parser = subparsers.add_parser("compare", help="Compare multiple checkpoints")
    comp_parser.add_argument("--seed", type=int, default=1000)
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
