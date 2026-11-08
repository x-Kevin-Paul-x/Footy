"""Dialogue safety, causal context, linked replies and failure recovery."""
import copy
import pytest

from backend.commentary.schemas import CommentarySlot, EnrichedEvent
from backend.commentary.understanding.story_stats import StoryStatsBuilder
from backend.commentary.llm.conversation import packet, draft, validate, digest
from backend.commentary.grounding import MissingEvidence, GroundedCompiler
from backend.commentary.tts.batch_runner import drop_orphan_replies


@pytest.fixture
def conversation():
    manifest = dict(match_id='demo',home_team='Home',away_team='Away',home_score=0,away_score=1,
                    home_players=['Sam Home'],away_players=['Sam Away'])
    goal = EnrichedEvent(event_id='goal',type='GOAL',step=200,presentation_ms=20000,
        match_minute=22,team='Away',player='Sam Away',facts={'score':'0-1'})
    ctx = StoryStatsBuilder(manifest).build_match_context([goal],[])
    slot = CommentarySlot(commentary_id='q',start_ms=10000,max_end_ms=15000,window_seconds=5,
        slot_type='story',speaker='Ryan',running_score='0-0',evidence_ids=['fixture'],
        dialogue_id='d',speech_act='ask')
    return ctx,slot


class Client:
    def __init__(self, accepted=True, extra=None):
        self.accepted,self.extra = accepted,extra
        self.requests = []
    def request_json(self,system,data,schema,**kwargs):
        self.requests.append((system,data))
        if 'proposal' in data:
            return dict(accepted=self.accepted,unsupported=[] if self.accepted else ['Invented observation'],claim_ids=['fixture'])
        return dict(text=self.extra or 'How would you approach this?')


def test_prompt_never_sees_final_score_future_goal_or_full_match_context(conversation):
    ctx,slot = conversation
    data = packet(ctx,slot,[])
    assert data['running_score'] == [0,0]
    assert [r['id'] for r in data['evidence']] == ['fixture']
    before = copy.deepcopy(data)
    ctx.away_score = 20
    ctx.score_str = '0-20'
    assert packet(ctx,slot,[]) == before


def test_original_prose_requires_separate_review_and_bound_evidence(conversation):
    ctx,slot = conversation
    client = Client()
    utt = draft(client,ctx,slot,[])
    assert len(client.requests) == 2
    assert validate(ctx,utt,slot) == (True,[])
    assert GroundedCompiler(ctx).validate(utt,slot)[0]
    assert utt.grounding['speech_act'] == 'ask'


@pytest.mark.parametrize('field,text',[('primary','A club record for Home.'),
    ('short','Away lead two to nil.'),('emergency_short','Sam scored a hat-trick.')])
def test_copied_review_does_not_authorize_changed_variants(conversation,field,text):
    ctx,slot = conversation
    utt = draft(Client(),ctx,slot,[]).model_copy(update={field:text})
    assert not validate(ctx,utt,slot)[0]


def test_independent_rejection_cannot_be_overridden_by_writer(conversation):
    ctx,slot = conversation
    client = Client(accepted=False)
    with pytest.raises(MissingEvidence,match='Invented observation'):
        draft(client,ctx,slot,[])
    assert len(client.requests) == 4  # One repair, then fallback.


def test_hard_gate_rejects_false_score_even_when_model_says_accepted(conversation):
    ctx,slot = conversation
    with pytest.raises(MissingEvidence,match='incorrect'):
        draft(Client(extra='Home lead two to nil.'),ctx,slot,[])


@pytest.mark.parametrize('text',['Four nil.','4-0.','Four to nil.','Aiden: Your thoughts?'])
def test_unapproved_verbal_scores_and_speaker_labels_cannot_pass_review(conversation,text):
    ctx,slot = conversation
    slot.speech_act = 'call'
    with pytest.raises(MissingEvidence):
        draft(Client(extra=text),ctx,slot,[])


def test_future_claim_ids_cannot_be_cited(conversation):
    ctx,slot = conversation
    class Future(Client):
        def request_json(self,*args,**kwargs):
            return dict(text='An opening goal.',claim_ids=['goal'])
    with pytest.raises(MissingEvidence,match='Invalid dialogue JSON'):
        draft(Future(),ctx,slot,[])


def test_critical_goal_call_cannot_switch_to_generative_prose(conversation):
    ctx,slot = conversation
    slot.slot_type = 'goal_reaction'
    with pytest.raises(MissingEvidence,match='Critical event'):
        draft(Client(),ctx,slot,[])


def test_evidence_change_invalidates_recorded_review(conversation):
    ctx,slot = conversation
    utt = draft(Client(),ctx,slot,[])
    ctx.evidence_records[0]['data']['home'] = 'Changed'
    assert not validate(ctx,utt,slot)[0]


def test_actual_prior_variants_and_reply_identity_are_supplied(conversation):
    ctx,slot = conversation
    opener = draft(Client(),ctx,slot,[])
    answer = slot.model_copy(update=dict(commentary_id='a',speaker='Aiden',start_ms=15250,
        max_end_ms=20250,reply_to='q',speech_act='answer'))
    data = packet(ctx,answer,[opener])
    assert data['reply_to'] == 'q'
    assert data['recent'][0]['possible_spoken_texts'] == [opener.primary,opener.short,opener.emergency_short]


def test_cached_answer_is_dropped_when_question_has_no_audio():
    answer = dict(clip_id='a',requested_start_ms=2000)
    slots = {'q':{},'a':{'reply_to':'q'}}
    omissions = []
    assert drop_orphan_replies([answer],slots,omissions) == []
    assert omissions[0]['id'] == 'a'
    opener = dict(clip_id='q',requested_start_ms=1000)
    assert drop_orphan_replies([answer,opener],slots,[]) == [opener,answer]


def test_digest_cannot_hide_wrong_identity(conversation):
    ctx,slot = conversation
    utt = draft(Client(),ctx,slot,[])
    utt.speaker = 'Aiden'
    utt.grounding['digest'] = digest(utt,slot,packet(ctx,slot,[])['evidence'])
    assert not validate(ctx,utt,slot)[0]


def test_question_and_answer_fall_back_together(conversation,monkeypatch):
    from backend.commentary.llm.writer import CommentaryWriter
    ctx,question = conversation
    answer = question.model_copy(update=dict(commentary_id='a',speaker='Aiden',start_ms=15250,
        max_end_ms=19500,reply_to='q',speech_act='answer'))
    first = draft(Client(),ctx,question,[])
    def generation(client,context,slot,recent):
        if slot.speech_act=='ask':
            return first
        raise MissingEvidence('Unrelated reply')
    monkeypatch.setattr('backend.commentary.llm.writer.draft',generation)
    client = Client()
    client.is_server_online = lambda: True
    writer = CommentaryWriter(ctx,client)
    result = writer.write_script([answer,question])
    assert [u.commentary_id for u in result.utterances] == ['q','a']
    assert all(u.grounding['version']=='evidence-1' for u in result.utterances)
    assert writer.diagnostics['dialogue_accepted']==0
    assert writer.diagnostics['factual_fallbacks']==2
    assert result.utterances[0].primary.endswith('?')
    assert "I'd" in result.utterances[1].primary
