"""Historical-time boundaries and required/optional speech recovery."""

import json
import pytest
from backend.commentary.grounding import MissingEvidence
from backend.commentary.schemas import CommentaryScript, CommentarySlot, CommentaryUtterance
from backend.commentary.tts.worker import TTSWorker
from backend.commentary.tts.voice_profiles import clip_seed
from backend.commentary.understanding.broadcast_context import snapshot_evidence


def snapshot():
    return dict(match_id='current',run_id='run',trajectory_sha256='hash',
        kickoff_at='2026-10-15T15:00:00+00:00',frozen_at='2026-10-15T14:00:00+00:00',
        complete_history=True,results=[dict(match_id=str(i),run_id='run',home='Home',away='Elsewhere',
            score=[2,0],finished_at=f'2026-10-{day:02d}T17:00:00+00:00') for i,day in enumerate((1,5,10))])


def test_history_excludes_simultaneous_and_future_worker_results():
    s=snapshot()
    s['results'].append(dict(match_id='parallel',run_id='run',home='Home',away='Elsewhere',score=[0,9],
                             finished_at='2026-10-15T17:00:00+00:00'))
    records=snapshot_evidence(s,dict(match_id='current',home_team='Home',away_team='Away'),'hash','run')
    assert next(r for r in records if r['kind']=='winning_run')['data']['wins']==3
    assert not any('parallel' in r['source'] for r in records)
    s['complete_history']=False
    assert not any(r['kind']=='winning_run' for r in snapshot_evidence(s,dict(match_id='current',home_team='Home',away_team='Away'),'hash','run'))


@pytest.mark.parametrize('field,value',[('match_id','other'),('run_id','other'),('trajectory_sha256','other'),
                                       ('frozen_at','2026-10-15T18:00:00+00:00')])
def test_unbound_or_retrospective_snapshots_rejected(field,value):
    s=snapshot();s[field]=value
    with pytest.raises(MissingEvidence):
        snapshot_evidence(s,dict(match_id='current',home_team='Home',away_team='Away'),'hash','run')


def test_duplicate_history_rejected():
    s=snapshot();s['results'].append(s['results'][0])
    with pytest.raises(MissingEvidence):
        snapshot_evidence(s,dict(match_id='current',home_team='Home',away_team='Away'),'hash','run')


@pytest.mark.parametrize('kind,required',[('lead_in',False),('goal_reaction',True)])
def test_qwen_optional_omission_is_explicit_and_required_cannot_be_omitted(tmp_path,monkeypatch,kind,required):
    slot=CommentarySlot(commentary_id='x',start_ms=0,max_end_ms=800,window_seconds=.8,slot_type=kind)
    u=CommentaryUtterance(commentary_id='x',target_duration_ms=800,primary='Gerow!',short='Gerow!',emergency_short='Gerow!')
    script=CommentaryScript(match_id='current',utterances=[u])
    worker=TTSWorker(clips_dir=tmp_path/'clips')
    def fake_batch(*args,**kwargs):
        (tmp_path/'audio_clips_manifest.json').write_text('[]')
        (tmp_path/'tts_omissions.json').write_text(json.dumps([{'id':'x','reason':'No complete variant fits'}]))
    monkeypatch.setattr('backend.commentary.tts.worker.subprocess.run',fake_batch)
    monkeypatch.setattr(worker,'synthesize_clip',lambda *a:pytest.fail('Must not replace missing neural clips with SAPI'))
    if required:
        with pytest.raises(RuntimeError,match='Neural speech failed'):
            worker.synthesize_script(script,[slot],engine='qwen')
    else:
        assert worker.synthesize_script(script,[slot],engine='qwen')==[]
        assert worker.omissions[0]['id']=='x'


def test_seed_is_content_bound_and_independent_of_batch_order():
    original=clip_seed('a','Hello.','Ryan','primary')
    clip_seed('other','Different.','Aiden','primary')
    assert original==clip_seed('a','Hello.','Ryan','primary')
    assert original!=clip_seed('a','Hello!','Ryan','primary')
    assert original!=clip_seed('a','Hello.','Aiden','primary')


def test_script_checkpoint_is_reused_and_tampering_recompiled(tmp_path):
    from backend.commentary.orchestrator import CommentaryPipelineOrchestrator
    from backend.commentary.config import GOLDEN_TRACE_NPZ_PATH
    pipeline=CommentaryPipelineOrchestrator(trace_npz_path=GOLDEN_TRACE_NPZ_PATH,
        artifacts_dir=tmp_path/'artifacts',output_dir=tmp_path/'output')
    first=pipeline.run_pipeline(script_only=True,use_llm=False)
    assert first['cached_script'] is False
    assert pipeline.run_pipeline(script_only=True,use_llm=False)['cached_script'] is True
    compiled=tmp_path/'artifacts/commentary_script.compiled.json'
    payload=json.loads(compiled.read_text())
    payload['utterances'][0]['primary']='An invented record.'
    compiled.write_text(json.dumps(payload))
    assert pipeline.run_pipeline(script_only=True,use_llm=False)['cached_script'] is False
