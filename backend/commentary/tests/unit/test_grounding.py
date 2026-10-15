"""Adversarial tests for the factual release boundary, not just a prompt."""

import copy
import json
import pytest

from backend.commentary.grounding import GroundedCompiler, MissingEvidence
from backend.commentary.llm.client import LlamaClient
from backend.commentary.llm.validator import FactFirewallValidator
from backend.commentary.schemas import CommentarySlot, EnrichedEvent
from backend.commentary.speech_text import classify_goal, format_score_speech
from backend.commentary.understanding.story_stats import StoryStatsBuilder


@pytest.fixture
def fixture():
    manifest = dict(match_id='grounding', home_team='Home', away_team='Away', home_score=1, away_score=2,
                    home_players=['Scott Britt'], away_players=['Sandra Gerow'],
                    home_formation='4-3-3', away_formation='4-4-2')
    events = [EnrichedEvent(event_id=str(i), type='GOAL', step=i*10, presentation_ms=i*10000,
                          match_minute=minute, team=team, player=name, facts={'score': score})
              for i, (minute, team, name, score) in enumerate([
                  (22, 'Away', 'Sandra Gerow', '0-1'), (25, 'Away', 'Sandra Gerow', '0-2'),
                  (51, 'Home', 'Scott Britt', '1-2')], 1)]
    return manifest, events


def goal_slot():
    return CommentarySlot(commentary_id='goal', start_ms=30000, max_end_ms=34300, window_seconds=4.3,
                          slot_type='goal_reaction', active_team='Home', active_player='Scott Britt',
                          running_score='1-2', match_minute=51)


@pytest.mark.parametrize('before,after,category', [
    ('0-0','1-0','opener'), ('0-2','1-2','deficit_reducer'), ('1-2','2-2','equaliser'),
    ('2-2','2-3','go_ahead'), ('1-2','1-3','advantage_extended'),
    ('3-4','4-4','equaliser'), ('10-10','11-10','go_ahead')])
def test_goal_semantics_and_symmetry(before, after, category):
    assert classify_goal(before,after).category == category
    assert classify_goal(before.split('-')[::-1],after.split('-')[::-1]).category == category


@pytest.mark.parametrize('before,after', [('0-0','2-0'),('2-1','1-1'),('1-1','2-2'),('1-1','1-1')])
def test_bad_score_transition_fails(before, after):
    with pytest.raises(ValueError): classify_goal(before,after)


def test_score_speech_binds_teams_and_handles_multi_digit():
    assert format_score_speech('0-1') == 'nil-one'
    assert format_score_speech('4-4') == 'four-all'
    assert format_score_speech('10-12','Home','Away') == 'Home ten, Away twelve'


def test_copied_citation_cannot_authorize_invented_sentence(fixture):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    compiler, slot = GroundedCompiler(ctx), goal_slot()
    utt = compiler.realize(slot,'goal.outcome')
    assert compiler.validate(utt,slot)[0]
    for field, invented in [('primary','Britt levels it!'), ('short','Home have won five in a row.'),
                            ('emergency_short','Britt completes a hat-trick!')]:
        changed = utt.model_copy(update={field: invented})
        assert not compiler.validate(changed,slot)[0]
    assert not FactFirewallValidator(ctx).validate(utt.model_copy(update={'grounding':None}),slot)[0]


def test_future_goal_cannot_supply_earlier_context(fixture):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    compiler = GroundedCompiler(ctx)
    assert all(r['available_ms'] <= 15000 for r in compiler.ledger.at(15000))
    with pytest.raises(MissingEvidence):
        compiler.options(goal_slot().model_copy(update={'start_ms':15000}))


def test_context_prefix_unchanged_when_future_result_changes(fixture):
    manifest, events = fixture
    first = GroundedCompiler(StoryStatsBuilder(manifest).build_match_context(events,[])).ledger.at(15000)
    alternative = copy.deepcopy(events)
    alternative[1].team, alternative[1].player, alternative[1].facts['score'] = 'Home','Scott Britt','1-1'
    alternative[2].facts['score'] = '2-1'
    second = GroundedCompiler(StoryStatsBuilder(manifest).build_match_context(alternative,[])).ledger.at(15000)
    assert first == second


def test_model_extra_prose_is_rejected_even_with_valid_template(fixture, monkeypatch):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    client = LlamaClient(); client._server_available = True
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self):
            return json.dumps({'choices':[{'message':{'content':json.dumps({
                'template_id':'goal.outcome','text':'Britt has broken a club record.'})}}]}).encode()
    monkeypatch.setattr('urllib.request.urlopen',lambda *args,**kwargs:Response())
    utt = client.generate_utterance(goal_slot(),ctx,[])
    assert client.last_failure == 'ValueError'
    assert 'record' not in utt.primary
    assert FactFirewallValidator(ctx).validate(utt,goal_slot())[0]


def test_unknown_streak_story_cannot_compile(fixture):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    slot = goal_slot().model_copy(update={'slot_type':'story','evidence_ids':['made-up-streak']})
    with pytest.raises(MissingEvidence): GroundedCompiler(ctx).options(slot)


def test_tampered_cross_match_and_team_binding_fail(fixture):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    ctx.evidence_records[0]['match_id'] = 'another-run'
    with pytest.raises(MissingEvidence): GroundedCompiler(ctx)
    events[2].team = 'Away'
    with pytest.raises(MissingEvidence): StoryStatsBuilder(manifest).build_match_context(events,[])


def test_goal_comment_does_not_call_deficit_reduction_an_equaliser(fixture):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    for option in GroundedCompiler(ctx).options(goal_slot()):
        assert 'level' not in option.primary.lower()
    analysis = goal_slot().model_copy(update={'slot_type':'analysis','start_ms':34550})
    for option in GroundedCompiler(ctx).options(analysis):
        assert 'ahead' not in option.primary.lower()


def test_current_match_goal_tally_is_past_only_and_superseded(fixture):
    manifest, events = fixture
    ctx = StoryStatsBuilder(manifest).build_match_context(events,[])
    compiler = GroundedCompiler(ctx)
    assert not any(r['kind']=='goal_tally' for r in compiler.ledger.at(15000))
    record=next(r for r in compiler.ledger.at(25000) if r['kind']=='goal_tally')
    assert record['data']['count']==2
    assert '1,2' in record['source']
    events.append(EnrichedEvent(event_id='4',type='GOAL',step=40,presentation_ms=40000,
        match_minute=65,team='Away',player='Sandra Gerow',facts={'score':'1-3'}))
    later=GroundedCompiler(StoryStatsBuilder(manifest).build_match_context(events,[]))
    assert next(r for r in later.ledger.at(45000) if r['kind']=='goal_tally')['data']['count']==3
    assert next(r for r in later.ledger.at(25000) if r['kind']=='goal_tally')['data']['count']==2
