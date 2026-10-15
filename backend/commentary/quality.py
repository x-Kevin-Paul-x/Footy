"""Audit deadlines, spoken onset, factual alternatives and copied video packets."""
import json, subprocess, wave
from pathlib import Path
import numpy as np
from backend.commentary.schemas import CommentarySlot, CommentaryScript, MatchContext, AudioClip
from backend.commentary.llm.validator import FactFirewallValidator

def video_packet_hash(path):
    result=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-map","0:v:0","-c","copy",
        "-f","hash","-hash","sha256","pipe:1"],capture_output=True,text=True,check=True)
    return result.stdout.strip()

def audit_commentary(artifacts_dir, timeline, source_video=None, output_video=None):
    p=Path(artifacts_dir)
    slots=[CommentarySlot(**s) for s in json.loads((p/"commentary_plan.json").read_text(encoding="utf-8-sig"))]
    script=CommentaryScript.model_validate_json((p/"commentary_script.json").read_text(encoding="utf-8-sig"))
    context=MatchContext.model_validate_json((p/"match_context.json").read_text(encoding="utf-8-sig"))
    clips=[AudioClip(**c) for c in json.loads((p/"audio_clips_manifest.json").read_text(encoding="utf-8-sig"))]
    if not (context.match_id==script.match_id==timeline.match_id): raise ValueError("Match ID mismatch")
    if {s.commentary_id for s in slots}!={c.clip_id for c in clips}: raise ValueError("Missing speech clips")
    validator=FactFirewallValidator(context)
    utterances={u.commentary_id:u for u in script.utterances}
    durations, onsets={},{}
    for s in slots:
        valid,errors=validator.validate(utterances[s.commentary_id],s)
        if not valid: raise ValueError(f"Unverified speech {s.commentary_id}: {errors}")
        clip = next(c for c in clips if c.clip_id == s.commentary_id)
        metadata_path = Path(clip.file_path).with_suffix('.json')
        if utterances[s.commentary_id].grounding is not None:
            if not metadata_path.exists():
                raise ValueError('Grounded audio has no selected-text provenance')
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            if metadata.get('text') != getattr(utterances[s.commentary_id],clip.variant_used):
                raise ValueError('Actual selected speech text differs from validated variant')
    for clip in clips:
        with wave.open(clip.file_path,"rb") as f:
            values=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16).reshape(-1,f.getnchannels())
            sr=f.getframerate()
        durations[clip.clip_id]=len(values)*1000/sr
        samples=np.max(np.abs(values.astype(np.float32)/32768),axis=1)
        active=np.flatnonzero(samples>max(.003,float(np.max(samples))*.02))
        onsets[clip.clip_id]=float(active[0])*1000/sr if len(active) else float("inf")
        if clip.requested_start_ms+durations[clip.clip_id]>clip.max_end_ms+.001:
            raise ValueError(f"Overflow {clip.clip_id}")
    ordered=sorted(clips,key=lambda c:c.requested_start_ms)
    for a,b in zip(ordered,ordered[1:]):
        if a.requested_start_ms+durations[a.clip_id]>b.requested_start_ms+.001:
            raise ValueError("Overlapping speech")
    events=json.loads((p/"events_enriched.json").read_text(encoding="utf-8-sig"))
    goal_events=[e for e in events if e["type"]=="GOAL"]
    rows=[]
    for e in goal_events:
        s=next(s for s in slots if s.slot_type=="goal_reaction" and s.start_ms==e["presentation_ms"])
        if s.active_player!=e["player"]: raise ValueError("Wrong scorer")
        clip=next(c for c in clips if c.clip_id==s.commentary_id)
        lead=[a for a in slots if a.slot_type in ("lead_in","shot_call","attack") and
              a.active_team==e['team'] and 0<e["presentation_ms"]-a.start_ms<=4000]
        rows.append({"scorer":e["player"],"score":s.running_score,"crossing_seconds":s.start_ms/1000,
            "goal_voice_onset_ms":round(onsets[clip.clip_id],1),
            "buildup_seconds":lead[-1].start_ms/1000 if lead else None})
    report={"match_id":context.match_id,"clips":len(clips),"overflow_clips":0,"overlap_clips":0,
        "all_script_variants_valid":True,"speech_seconds":round(sum(durations.values())/1000,2),
        "goals":rows,"all_goals_have_buildup":all(r["buildup_seconds"] is not None for r in rows)}
    gaps = [dict(start_seconds=round((a.requested_start_ms+durations[a.clip_id])/1000,3),
                 end_seconds=b.requested_start_ms/1000,
                 duration_seconds=round((b.requested_start_ms-a.requested_start_ms-durations[a.clip_id])/1000,3))
            for a,b in zip(ordered,ordered[1:])]
    report['speech_gaps_over_eight_seconds'] = [g for g in gaps if g['duration_seconds'] > 8]
    report['maximum_inter_clip_speech_gap_seconds'] = max((g['duration_seconds'] for g in gaps),default=0)
    report['grounded_clips'] = sum(u.grounding is not None for u in script.utterances)
    report['story_clips'] = sum(s.slot_type == 'story' for s in slots)
    omissions = p/'tts_omissions.json'
    report['optional_audio_omissions'] = json.loads(omissions.read_text()) if omissions.exists() else []
    report['factual_validation_scope'] = 'Controlled text and evidence provenance; not an audio listening score'
    report['buildup_definition'] = 'Observed same-team attack/shot cue within four seconds; no requirement to know the future scorer'
    if source_video and output_video:
        report["original_video_packets_preserved"]=video_packet_hash(source_video)==video_packet_hash(output_video)
        if not report["original_video_packets_preserved"]: raise ValueError("Video was changed")
    (p/"quality_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
