"""Regressions for the actual timing, cache and factual failures."""
import json, wave
from pathlib import Path
import numpy as np
import pytest
from backend.commentary.schemas import AudioClip, MatchContext, CommentarySlot, CommentaryUtterance
from backend.commentary.audio.processor import AudioProcessor
from backend.commentary.tts.batch_runner import cache_signature
from backend.commentary.llm.validator import FactFirewallValidator
from backend.commentary.understanding.timeline_adapter import TimelineAdapter

def test_native_goal_timestamp_is_crossing_not_replay(tmp_path):
    p=tmp_path/"timeline.json"
    p.write_text(json.dumps({"fps":10,"native_redraw":True,"events_pts_map":{"step_100":13},
        "segments":[{"segment_type":"intro","pts_end_seconds":3},
                    {"segment_type":"goal_replay","source_step_start":100,"pts_start_seconds":13.2,"pts_end_seconds":13.2}]}))
    tl=TimelineAdapter(p)
    assert tl.step_to_pts(100)==13
    assert tl.step_to_pts(101)==13.2

def test_cache_changes_with_text_voice_and_budget():
    slot={"speaker":"Ryan","energy_target":.5,"slot_type":"buildup","start_ms":1000,"max_end_ms":3000}
    u={"primary":"Noble has it."}
    sig=cache_signature(u,slot)
    assert sig!=cache_signature({"primary":"Hite has it."},slot)
    assert sig!=cache_signature(u,{**slot,"speaker":"Aiden"})
    assert sig!=cache_signature(u,{**slot,"max_end_ms":3100})

def write_wave(path, seconds, rate=48000):
    data=np.ones((round(seconds*rate),2),dtype=np.int16)*1000
    with wave.open(str(path),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes(data.tobytes())

def clip(path, cid, start, end):
    return AudioClip(clip_id=cid,requested_start_ms=start,max_end_ms=end,actual_duration_ms=1000,
        file_path=str(path),pts_offset_seconds=start/1000)

def test_adjacent_clips_are_not_delayed(tmp_path, monkeypatch):
    a,b=tmp_path/"a.wav",tmp_path/"b.wav"
    write_wave(a,1);write_wave(b,1)
    proc=AudioProcessor(4)
    def copy(src,dst): dst.write_bytes(src.read_bytes()); return True
    monkeypatch.setattr(proc,"resample_clip_to_48k",copy)
    p,_=proc.assemble_master_track([clip(a,"a",1000,2000),clip(b,"b",2000,3000)],tmp_path/"master.wav")
    with wave.open(str(p),"rb") as f: values=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16).reshape(-1,2)
    assert values[96000,0]!=0  # exactly 2s, rather than waiting another 250ms

def test_oversized_audio_is_rejected_not_shifted(tmp_path, monkeypatch):
    a=tmp_path/"a.wav";write_wave(a,1.1)
    proc=AudioProcessor(4)
    monkeypatch.setattr(proc,"resample_clip_to_48k",lambda src,dst:dst.write_bytes(src.read_bytes()))
    with pytest.raises(ValueError,match="deadline"):
        proc.assemble_master_track([clip(a,"a",1000,2000)],tmp_path/"master.wav")

def test_future_fact_and_emergency_score_are_rejected():
    context=MatchContext(match_id="x",home_team="Home",away_team="Away",home_score=2,away_score=4,
        score_str="2-4",allowed_facts={"f":"Final score 2-4"},fact_available_ms={"f":10000})
    slot=CommentarySlot(commentary_id="s",start_ms=1000,max_end_ms=3000,window_seconds=2,
        slot_type="buildup",running_score="0-0",allowed_fact_ids=["f"])
    u=CommentaryUtterance(commentary_id="s",target_duration_ms=2000,primary="Possession.",
        short="Possession.",emergency_short="Four-nil!",used_fact_ids=["f"])
    valid,errors=FactFirewallValidator(context).validate(u,slot)
    assert not valid
    assert any("Future fact" in e for e in errors)
    assert any("Illegal scoreline" in e for e in errors)
