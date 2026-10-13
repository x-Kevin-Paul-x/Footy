"""Deterministic manager changes applied before policy modulation at a tick."""
from logic.footy_grf_adapter import FORMATION_COORDINATES


def validate_changes(changes, max_steps):
    seen = set()
    for change in changes:
        key = (change.get('step'), change.get('team'))
        if key in seen or not isinstance(key[0], int) or not 0 <= key[0] < max_steps or key[1] not in ('home', 'away'):
            raise ValueError('Tactical changes need unique valid steps and team identities')
        seen.add(key)
        if change.get('condition', 'always') not in ('always', 'leading', 'trailing'):
            raise ValueError('Invalid tactical condition')
        for name in ('offensive_bias', 'defensive_bias', 'pressing_intensity', 'tempo'):
            if name in change and not 0 <= change[name] <= 100:
                raise ValueError('Tactical values must be between zero and 100')
        if 'formation' in change and change['formation'] not in FORMATION_COORDINATES:
            raise ValueError('Unsupported formation')


def apply_changes(changes, step, home, away, score):
    emitted = []
    for change in changes:
        if change['step'] != step:
            continue
        side = 0 if change['team'] == 'home' else 1
        delta = score[side] - score[1 - side]
        condition = change.get('condition', 'always')
        if condition == 'leading' and delta <= 0 or condition == 'trailing' and delta >= 0:
            continue
        target = home if side == 0 else away
        for name in ('formation', 'offensive_bias', 'defensive_bias', 'pressing_intensity', 'tempo'):
            if name in change:
                setattr(target, name, change[name])
        emitted.append({'type': 'tactical_change', 'team': change['team'], 'step': step, 'changes': change})
    return emitted
