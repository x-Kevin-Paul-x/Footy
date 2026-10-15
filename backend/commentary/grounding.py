"""Time-scoped evidence and controlled realization for released commentary.

The model may select a candidate. It cannot supply names, numbers or prose.
All factual values originate in the trusted recorded-artifact adapter below.
"""

from copy import deepcopy
from dataclasses import dataclass
import hashlib

from backend.commentary.schemas import CommentaryUtterance
from backend.commentary.speech_text import classify_goal, format_score_speech, number_word, parse_score


class MissingEvidence(ValueError):
    pass


def short_name(name):
    words = name.split()
    return " ".join(words[-2:]) if words and words[-1].isdigit() else words[-1] if words else ""


def build_evidence(manifest, events):
    """Trusted adapter: never turn arbitrary natural-language 'facts' into evidence."""
    records = []
    match = str(manifest['match_id'])
    home, away = manifest['home_team'], manifest['away_team']

    def put(cid, kind, data, when=0, expires=None, source=None):
        records.append(dict(id=cid, match_id=match, kind=kind, available_ms=int(when),
                            expires_ms=expires, data=deepcopy(data), source=source or f'manifest:{cid}'))

    put('fixture', 'fixture', dict(home=home, away=away, venue=manifest.get('venue') or ''))
    for side, team in (('home', home), ('away', away)):
        formation = manifest.get(f'{side}_formation')
        if formation and all(part.isdigit() for part in formation.split('-')):
            put(f'{side}.formation', 'formation', dict(team=team, formation=formation))
        roster = {p['name']: p for p in manifest.get(f'{side}_roster', []) if p.get('name')}
        for i, name in enumerate(manifest.get(f'{side}_players', [])):
            p = roster.get(name, {})
            put(f'{side}.player.{i}', 'player', dict(name=name, team=team,
                player_id=p.get('player_id'), position=p.get('position'), number=p.get('jersey_number')))
    previous = (0, 0)
    scorer_counts = {}
    scorer_events = {}
    for event in sorted(events, key=lambda e: (e.presentation_ms, e.event_id)):
        data = dict(event.facts)
        data.update(team=event.team, player=event.player, minute=event.match_minute)
        expires = event.presentation_ms + 2500
        if event.type == 'GOAL':
            transition = classify_goal(previous, event.facts['score'], event.match_minute)
            expected_team = (home, away)[transition.side]
            if event.team != expected_team:
                raise MissingEvidence('Goal beneficiary conflicts with canonical score change')
            if event.player and event.player not in manifest.get(('home' if transition.side == 0 else 'away') + '_players', []):
                raise MissingEvidence('Goal scorer is absent from the recorded roster')
            data.update(before=list(previous), after=list(transition.after), category=transition.category,
                        side=transition.side, late=transition.late)
            previous = transition.after
            expires = None
            if event.player:
                scorer_key = (event.team, event.player)
                scorer_counts[scorer_key] = scorer_counts.get(scorer_key, 0) + 1
                scorer_events.setdefault(scorer_key, []).append(event.event_id)
                if scorer_counts[scorer_key] >= 2:
                    put(f'tally.{event.event_id}', 'goal_tally', dict(team=event.team,
                        player=event.player, count=scorer_counts[scorer_key]), event.presentation_ms,
                        source='canonical_goal_ledger:' + ','.join(scorer_events[scorer_key]))
        elif event.type in ('HALFTIME', 'FULLTIME'):
            # A whistle is authoritative; absent legacy score fields use the
            # chronological goal ledger, never the manifest's final score.
            if event.facts.get('score') and parse_score(event.facts['score']) != previous:
                raise MissingEvidence('Whistle score conflicts with recorded goals')
            data['after'] = list(previous)
            expires = None
        put(event.event_id, event.type, data, event.presentation_ms, expires,
            f'event:{event.event_id};source_step:{event.step}')
    return records


class EvidenceLedger:
    def __init__(self, context):
        self.match_id = context.match_id
        self.records = deepcopy(context.evidence_records)
        ids = [r['id'] for r in self.records]
        if len(ids) != len(set(ids)) or any(r['match_id'] != self.match_id for r in self.records):
            raise MissingEvidence('Duplicate or cross-match evidence')

    def at(self, milliseconds):
        available = [r for r in self.records if r['available_ms'] <= milliseconds and
                (r.get('expires_ms') is None or milliseconds <= r['expires_ms'])]
        # A later third goal supersedes "two goals" only once it has happened.
        latest_tallies = {}
        for record in available:
            if record['kind'] == 'goal_tally':
                key = (record['data']['team'],record['data']['player'])
                previous = latest_tallies.get(key)
                if previous is None or record['available_ms'] > previous['available_ms']:
                    latest_tallies[key] = record
        return [r for r in available if r['kind'] != 'goal_tally' or
                latest_tallies[(r['data']['team'],r['data']['player'])]['id'] == r['id']]


@dataclass(frozen=True)
class Candidate:
    template_id: str
    claim_ids: tuple
    primary: str
    short: str
    emergency_short: str


class GroundedCompiler:
    version = 'evidence-1'

    def __init__(self, context):
        self.context = context
        self.ledger = EvidenceLedger(context)

    def options(self, slot):
        eligible = self.ledger.at(slot.start_ms)
        fixture = next((r for r in eligible if r['kind'] == 'fixture'), None)
        if fixture is None:
            raise MissingEvidence('No recorded fixture identity')
        home, away = fixture['data']['home'], fixture['data']['away']
        options = []

        def add(key, records, primary, short=None, emergency=None):
            options.append(Candidate(key, tuple(r['id'] for r in records), primary,
                                     short or primary, emergency or short or primary))

        goals = [r for r in eligible if r['kind'] == 'GOAL']
        score = tuple(goals[-1]['data']['after']) if goals else (0, 0)
        if score != parse_score(slot.running_score):
            raise MissingEvidence('Slot score differs from its as-of evidence ledger')
        if slot.slot_type in ('goal_reaction', 'analysis'):
            goal = next((r for r in reversed(goals) if r['data']['player'] == slot.active_player and
                         r['data']['team'] == slot.active_team and tuple(r['data']['after']) == score), None)
            if goal is None:
                raise MissingEvidence('No matching, available canonical goal')
            d = goal['data']
            transition = classify_goal(d['before'], d['after'], d['minute'])
            team, name, category = d['team'], short_name(d['player']), transition.category
            outcomes = dict(equaliser="They're level!", deficit_reducer="They pull one back!",
                            opener="The opening goal!", go_ahead="They go in front!",
                            advantage_extended="They extend their advantage!")
            if slot.slot_type == 'goal_reaction':
                late = 'A late equaliser!' if transition.late and category == 'equaliser' else outcomes[category]
                add('goal.outcome', [goal], f'Goal! {name}! {late}', f'Goal! {name} scores!', f'Goal! {name}!')
                add('goal.team', [goal], f'{name} scores! {team} {outcomes[category][5:].lower()}'
                    if category in ('deficit_reducer', 'go_ahead', 'advantage_extended') else f'Goal! {name}! {late}',
                    f'Goal! {name}!', f'Goal! {name}!')
            else:
                minute = d['minute']
                if category == 'equaliser':
                    clauses = (['A late twist. Nothing separates the sides.',
                                'All square, with the closing minutes now crucial.',
                                'What a time to bring it back level.'] if transition.late else
                               ['Nothing separates the sides now.', 'That changes the balance of this match.',
                                'The advantage has gone. Both sides are level.'])
                elif category == 'deficit_reducer':
                    clauses = ['The gap is smaller. That changes the pressure.',
                               'Still behind, but closer now.', 'A route back into this game.']
                elif category == 'advantage_extended':
                    clauses = ['The task becomes harder for the other side.',
                               'A larger advantage. The response matters now.',
                               'That gives the side in front more breathing room.']
                else:
                    clauses = ['The other side now needs a response.', 'A new situation for both teams.',
                               'There is now a score to chase.']
                for i, text in enumerate(clauses):
                    add(f'analysis.{category}.{i}', [goal], text)
                deficits = [r for r in goals if r['available_ms'] <= goal['available_ms'] and
                            r['data']['after'][1-transition.side] - r['data']['after'][transition.side] >= 2]
                if category == 'equaliser' and deficits:
                    add('analysis.comeback', [goal, deficits[-1]], 'From two goals behind to level terms.',
                        'A two-goal deficit erased.')
                if minute >= 86 and category != 'equaliser':
                    add('analysis.late', [goal], 'Very little regulation time remains. Every decision matters.')
            return options
        if slot.slot_type in ('halftime_recap', 'fulltime_summary'):
            kind = 'HALFTIME' if slot.slot_type == 'halftime_recap' else 'FULLTIME'
            whistle = next((r for r in reversed(eligible) if r['kind'] == kind), None)
            if whistle is None:
                raise MissingEvidence('Whistle has not happened')
            title = 'Half time' if kind == 'HALFTIME' else 'Full time'
            add('whistle.score', [fixture, whistle],
                f'{title}. {format_score_speech(score, home, away)}.',
                f'{title}. {format_score_speech(score)}.', f'{title}.')
            return options
        if slot.active_event_type == 'INTRO':
            if slot.speaker == 'Ryan':
                venue = fixture['data']['venue']
                greeting = f'Welcome to {venue}.' if venue else 'Welcome to the match.'
                add('intro.fixture', [fixture], f'{greeting} {home} against {away}.',
                    f'{home} against {away}.', 'Welcome to the match.')
            else:
                add('intro.analyst', [], "Good to be here. Let's see how this develops.", "Let's see how this develops.")
            return options
        if slot.slot_type == 'story':
            wanted = set(slot.evidence_ids)
            if slot.dialogue_id:
                cited = [r for r in eligible if r['id'] in wanted]
                if not cited:
                    raise MissingEvidence('Discussion topic unavailable')
                formation = next((r for r in cited if r['kind']=='formation'),None)
                support = list(cited)
                latest = goals[-1] if goals else None
                if latest and latest not in support:
                    support.append(latest)
                if formation:
                    team = formation['data']['team']
                    shape = formation['data']['formation']
                    if shape.startswith('3-'):
                        question = f'{team} with three at the back. Your first thought?'
                        answer = "I'd try to stretch them. Make those gaps as wide as possible."
                        short_answer = "I'd stretch them and look for gaps."
                    else:
                        question = f"{team}'s shape, Aiden. Where would you look for space?"
                        answer = "I'd test the wide areas first. Make them defend the whole pitch."
                        short_answer = "I'd test the wide areas first."
                    short_question = f'{team}: where would you attack?'
                elif score[0] != score[1]:
                    trailing = home if score[0]<score[1] else away
                    gap = abs(score[0]-score[1])
                    if gap == 1:
                        question = f'Just one in it. Would you take more risks?'
                        short_question = 'Would you take more risks?'
                        answer = "I would, but I'd leave cover. There's no need to gamble everything."
                        short_answer = "I would, but I'd leave some cover."
                    elif slot.match_minute >= 45:
                        if latest and slot.start_ms-latest['available_ms'] < 15000:
                            question = f'The gap is {number_word(gap)} now. Your response?'
                            short_question = 'How would you respond to that?'
                            answer = "I'd keep looking for a way back. But the next chance has to count."
                            short_answer = "I'd keep looking for a way back."
                        else:
                            question = f'{trailing} still need {number_word(gap)}. What changes now?'
                            short_question = 'What would you change now?'
                            answer = "I'd be more adventurous. Get the next goal and the conversation changes."
                            short_answer = "I'd be more adventurous. They need a goal."
                    elif slot.match_minute >= 35:
                        question = 'Is the next goal the key, do you think?'
                        short_question = 'How important is the next goal?'
                        answer = "Very. I'd keep it simple and give yourself something to build on."
                        short_answer = "Very. I'd keep it simple for now."
                    else:
                        question = f'{trailing} need {number_word(gap)} goals. Time to gamble?'
                        short_question = 'Time to gamble, do you think?'
                        answer = "Not everything, no. I'd work towards the next goal first."
                        short_answer = "Not yet. I'd focus on the next goal."
                else:
                    question = 'Nothing between them. Where would you take a risk?'
                    short_question = 'Where would you take a risk?'
                    answer = "I'd commit someone forward, but keep cover. Don't give the other side an easy break."
                    short_answer = "I'd commit someone forward, with cover."
                if slot.speech_act == 'ask':
                    add('discussion.ask', support, question, short_question, short_question)
                else:
                    add('opinion.discussion.answer', support, answer, short_answer, short_answer)
                return options
            for record in eligible:
                if record['id'] not in wanted:
                    continue
                d = record['data']
                if record['kind'] == 'formation':
                    spoken = ', '.join(number_word(int(n)) for n in d['formation'].split('-'))
                    add(f"story.{record['id']}", [record], f"{d['team']} line up in a {spoken}.")
                elif record['kind'] == 'prior_result':
                    add(f"story.{record['id']}", [record],
                        f"An earlier result: {format_score_speech(d['score'],d['home'],d['away'])}.")
                elif record['kind'] == 'winning_run':
                    add(f"story.{record['id']}", [record],
                        f"{d['team']} came into this match with {number_word(d['wins'])} straight wins.",
                        f"{number_word(d['wins']).capitalize()} straight wins before today for {d['team']}.")
                    add(f"opinion.{record['id']}", [record],
                        f"With {number_word(d['wins'])} straight wins behind them, I'd expect {d['team']} to feel confident.",
                        f"I'd expect confidence after {number_word(d['wins'])} straight wins.")
                elif record['kind'] == 'goal_tally':
                    name, count = short_name(d['player']), d['count']
                    add(f"story.{record['id']}", [record],
                        f"{name} has scored {number_word(count)} goals in this match.",
                        f"{number_word(count).capitalize()} goals already for {name}.")
                    if count == 2:
                        add(f"opinion.{record['id']}", [record],
                            f"Two goals for {name}. Can another follow?", f"Can {name} find another?")
                elif record['kind'] == 'player':
                    position = {'GK': 'goalkeeper', 'CB': 'centre back', 'LB': 'left back', 'RB': 'right back',
                                'DM': 'defensive midfielder', 'CM': 'central midfielder', 'AM': 'attacking midfielder',
                                'LM': 'left midfielder', 'RM': 'right midfielder', 'LW': 'left winger',
                                'RW': 'right winger', 'CF': 'forward', 'ST': 'striker'}.get(d.get('position'))
                    if position:
                        add(f"story.{record['id']}", [record], f"{d['name']} is selected at {position} for {d['team']}.",
                            f"{d['name']}, the {d['team']} {position}.")
                    else:
                        add(f"story.{record['id']}", [record], f"{d['name']} is in the {d['team']} starting line-up.",
                            f"{d['name']}, in this {d['team']} side.")
            if not options:
                raise MissingEvidence('Story has no supported, available realization')
            return options
        live = [r for r in eligible if r['kind'] == slot.active_event_type and
                r['data']['player'] == (slot.active_player or '') and r['data']['team'] == slot.active_team]
        if not live:
            raise MissingEvidence('Live observation absent or expired')
        record = live[-1]
        d = record['data']
        name = short_name(d['player'])
        if record['kind'] in ('PASS', 'PROGRESSIVE_PASS'):
            receiver = short_name(d.get('receiver', ''))
            if not receiver:
                raise MissingEvidence('Pass receiver unknown')
            for i, text in enumerate((f'{name} to {receiver}.', f'{receiver} receives from {name}.',
                                      f'Across to {receiver}.', f'{name} finds {receiver}.')):
                add(f'pass.{i}', [record], text, f'{receiver}.')
        elif record['kind'] == 'BOX_ENTRY':
            add('box.entry', [record], f'{name} in the penalty area.', f'{name} in the box.', f'{name}!')
        elif record['kind'] in ('SHOT', 'SHOT_RELEASE'):
            add('shot.observed', [record], f"{name + ', ' if name else ''}towards goal!", f'{name or "Chance here"}!', 'Chance here!')
        elif record['kind'] in ('CONTROL_IN_ATTACK', 'POSSESSION_START', 'TURNOVER'):
            if not name:
                raise MissingEvidence('Observed ball owner is unknown')
            for i, text in enumerate((f'{name} on the ball.', f'Possession with {name}.',
                                      f'{name} has it.', f'{name}, in possession.')):
                add(f'control.{i}', [record], text, f'{name}.')
        if not options:
            raise MissingEvidence('Unsupported evidence type')
        return options

    def realize(self, slot, template_id):
        candidate = next((o for o in self.options(slot) if o.template_id == template_id), None)
        if candidate is None:
            raise MissingEvidence('Unknown or ineligible speech template')
        records = {r['id']: r for r in self.ledger.at(slot.start_ms)}
        return CommentaryUtterance(commentary_id=slot.commentary_id, speaker=slot.speaker,
            energy=slot.energy_target, emotion='excited' if slot.energy_target >= .7 else 'calm',
            target_duration_ms=slot.max_end_ms-slot.start_ms, primary=candidate.primary,
            short=candidate.short, emergency_short=candidate.emergency_short,
            used_fact_ids=[], grounding=dict(version=self.version, template_id=template_id,
                kind='opinion' if template_id.startswith('opinion.') else 'fact',
                dialogue_id=slot.dialogue_id, speech_act=slot.speech_act, reply_to=slot.reply_to,
                claim_ids=list(candidate.claim_ids), as_of_ms=slot.start_ms,
                sources=[dict(id=cid, source=records[cid]['source'], available_ms=records[cid]['available_ms'])
                         for cid in candidate.claim_ids]))

    def validate(self, utterance, slot):
        if utterance.grounding and utterance.grounding.get('version') == 'conversation-1':
            from backend.commentary.llm.conversation import validate
            return validate(self.context, utterance, slot)
        try:
            expected = self.realize(slot, utterance.grounding['template_id'])
            # A copied evidence citation cannot authorize altered factual prose.
            if utterance.model_dump() != expected.model_dump():
                return False, ['Grounded utterance differs from its controlled realization']
            return True, []
        except (MissingEvidence, KeyError, TypeError, ValueError) as exc:
            return False, [f'Grounding rejected: {exc}']

    @staticmethod
    def stable_choice(slot, options):
        digest = hashlib.sha256(slot.commentary_id.encode()).digest()
        return options[int.from_bytes(digest[:4], 'big') % len(options)].template_id
