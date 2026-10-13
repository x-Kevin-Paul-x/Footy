"""Seeded manager comparisons, separate from GRF player-policy benchmarks."""
import hashlib
import platform
import random
import time
from pathlib import Path

import numpy as np

from database.jobs import check_cancelled


def resolve_model(model_id, directory):
    if not model_id or Path(model_id).name != model_id or any(c in model_id for c in ('/', '\\', ':')):
        raise ValueError('Select a registered model filename')
    root = Path(directory).resolve()
    model = (root / model_id).resolve()
    if not model.is_relative_to(root) or model.suffix != '.pt' or not model.is_file():
        raise ValueError('Model is unavailable')
    return model


def seed_everything(seed):
    import torch
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate(payload, models_dir, reports_dir, job_id=None):
    import torch
    torch.set_num_threads(1)
    from ml.dqn_agent import DQNAgent
    from ml.evaluation import build_evaluation_report, save_evaluation_report, summarize_episode_results
    from ml.footy_env import FootyEnv
    from ml.train_rl import run_episode

    models = [resolve_model(identity, models_dir) for identity in payload['models']]
    seeds = payload.get('seeds') or list(range(payload.get('seed', 1000), payload.get('seed', 1000) + payload['episodes']))
    started = time.perf_counter()
    summaries, provenance, raw = {}, {}, {}
    policies = [(f'trained_{model.stem}', model) for model in models]
    policies += [(name, None) for name in ('random', 'do_nothing', 'youth_focus', 'rule_based')]
    for name, model in policies:
        raw[name] = []
        for seed in seeds:
            if job_id:
                check_cancelled(job_id)
            seed_everything(seed)
            env = FootyEnv(num_teams=payload['teams'], season_length=payload['season_length'], fast_mode=payload['fast_mode'])
            try:
                agent = None
                if model:
                    agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim)
                    agent.load(model)
                result = run_episode(env, agent=agent, policy='trained' if model else name,
                                     training=False, epsilon=0.0, seed=seed)
                result['seed'] = seed
                raw[name].append(result)
            finally:
                env.close()
        summaries[name] = summarize_episode_results(name, raw[name])
        if model:
            provenance[name] = {'model_id': model.name, 'sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
                                'observation_dim': env.obs_dim, 'action_dim': env.action_dim}
    primary = policies[0][0]
    report = build_evaluation_report(';'.join(m.name for m in models),
                                    {**payload, 'seeds': seeds, 'environment_version': 1,
                                     'engine': 'synthetic_management'},
                                    {'elapsed_seconds': round(time.perf_counter() - started, 2),
                                     'python': platform.python_version()}, summaries,
                                    primary_policy_name=primary, policy_models=provenance)
    report['episodes'] = raw
    report_path = save_evaluation_report(report, str(reports_dir))
    report['report_name'] = Path(report_path).name
    return report
