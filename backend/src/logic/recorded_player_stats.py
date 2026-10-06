"""Derive season player totals and history from the saved match ledger."""
import json
from collections import defaultdict


def unpack_event(row):
    event = {key: getattr(row, key, None) for key in ('minute', 'type', 'player', 'team')}
    try:
        payload = json.loads(row.details or '{}')
        if isinstance(payload, dict):
            event.update(payload.get('canonical_event', payload))
    except (TypeError, ValueError):
        pass
    return event


def recorded_player_totals(matches, event_rows, team_names):
    grouped = defaultdict(list)
    for row in event_rows:
        grouped[row.match_id].append(row)
    totals = defaultdict(lambda: dict(goals=0, assists=0, appearances=0,
        minutes_played=0, clean_sheets=0, yellow_cards=0, red_cards=0,
        assists_recorded=False, match_history=[]))
    for match in matches:
        rows = grouped[match.match_id]
        events = [unpack_event(row) for row in rows if row.type not in (
            'home_lineup', 'away_lineup', 'home_bench', 'away_bench', 'substitutions')]
        duration = next((int(e['minute']) for e in events if e['type'] == 'full_time'), 90)
        substitutions = [e for e in events if e['type'] == 'substitution']
        for row in rows:
            if row.type == 'substitutions':
                try:
                    substitutions.extend(json.loads(row.details))
                except (TypeError, ValueError):
                    pass
        for side in ('home', 'away'):
            lineup = next((row for row in rows if row.type == side + '_lineup'), None)
            if lineup is None:
                continue  # A scorer name alone does not establish a full appearance.
            try:
                names = {p['name'] for p in json.loads(lineup.details)}
            except (TypeError, ValueError, KeyError):
                continue
            own = match.home_goals if side == 'home' else match.away_goals
            against = match.away_goals if side == 'home' else match.home_goals
            opponent = team_names.get(match.away_team_id if side == 'home' else match.home_team_id, 'Unknown')
            starts = {name: 0 for name in names}
            finishes = {name: duration for name in names}
            for sub in substitutions:
                if sub.get('team') != side:
                    continue
                minute = max(0, min(duration, int(sub.get('minute', 0))))
                outgoing, incoming = sub.get('player_out'), sub.get('player_in')
                if outgoing in finishes:
                    finishes[outgoing] = minute
                if incoming:
                    starts[incoming] = minute
                    finishes[incoming] = duration
            for name in starts:
                minutes = max(0, finishes[name] - starts[name])
                total = totals[name]
                total['appearances'] += 1
                total['minutes_played'] += minutes
                total['clean_sheets'] += int(against == 0)
                goals = sum(e['type'] == 'goal' and e.get('player') == name
                            and e.get('team') == side for e in events)
                total['match_history'].append(dict(match_id=match.match_id,
                    date=match.date, opponent=opponent, score=f'{own}–{against}',
                    goals=goals, minutes=minutes))
        for event in events:
            name = event.get('player') or event.get('scorer')
            if name and name != 'Unknown':
                field = {'goal': 'goals', 'yellow_card': 'yellow_cards', 'red_card': 'red_cards'}.get(event['type'])
                if field:
                    totals[name][field] += 1
            assister = event.get('assister') or event.get('assist')
            if event['type'] == 'goal' and isinstance(assister, str) and assister:
                totals[assister]['assists'] += 1
                totals[assister]['assists_recorded'] = True
    return dict(totals)


def apply_native_player_statistics(prepared, result):
    """Keep native batch player totals in sync with the same recorded events."""
    for side, lineup, conceded in (('home', prepared.home_lineup, result['score'][1]),
                                  ('away', prepared.away_lineup, result['score'][0])):
        for player in lineup:
            player.stats['appearances'] = player.stats.get('appearances', 0) + 1
            player.stats['minutes_played'] = player.stats.get('minutes_played', 0) + 90
            player.stats['clean_sheets'] = player.stats.get('clean_sheets', 0) + int(conceded == 0)
            for kind, field in (('goal', 'goals'), ('yellow_card', 'yellow_cards'), ('red_card', 'red_cards')):
                count = sum(e.get('type') == kind and e.get('player') == player.name
                            and e.get('team') == side for e in result.get('events', []))
                player.stats[field] = player.stats.get(field, 0) + count


def describe_match_event(event):
    if event.get('details'):
        return event['details']
    player = event.get('player') or event.get('scorer') or 'Player not recorded'
    kind = event.get('type', '')
    if kind == 'goal':
        return f"Goal — {player}" + (f". Score: {event['score']}" if event.get('score') else '')
    if kind == 'shot':
        outcome = {'GOAL': 'leads to a goal', 'SAVED': 'saved', 'MISS': 'off target'}.get(event.get('outcome'))
        return f"Shot — {player}" + (f" ({outcome})" if outcome else '')
    if kind in ('half_time', 'full_time'):
        return ('Half time' if kind == 'half_time' else 'Full time') + (f" — {event['score']}" if event.get('score') else '')
    if kind == 'substitution':
        incoming, outgoing = event.get('player_in'), event.get('player_out')
        if incoming and outgoing:
            return f"Substitution — {incoming} on for {outgoing}"
    return f"{kind.replace('_', ' ').capitalize()} — {player}"
