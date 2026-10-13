"""GPU speech synthesis with content-addressed caches and hard deadlines."""
import argparse, hashlib, json, subprocess, sys, time, wave
from pathlib import Path
root = Path(__file__).resolve().parents[3]
if str(root) not in sys.path: sys.path.insert(0, str(root))
from backend.commentary.config import ARTIFACTS_DIR, CLIPS_DIR, TTS_MODELS_DIR, DEFAULT_VOICE

def get_wav_duration_seconds(path):
    with wave.open(str(path), "rb") as f: return f.getnframes()/f.getframerate()

def cache_signature(utterance, slot):
    payload = {"version":3, "utterance":utterance, "speaker":slot.get("speaker"),
        "energy":slot.get("energy_target"), "type":slot.get("slot_type"),
        "budget_ms":slot["max_end_ms"]-slot["start_ms"],
        "model":str(TTS_MODELS_DIR), "weights_mtime":(TTS_MODELS_DIR/"model.safetensors").stat().st_mtime_ns
            if (TTS_MODELS_DIR/"model.safetensors").exists() else 0}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def get_instruction_for_slot(slot, emotion=""):
    kind = slot.get("slot_type")
    if slot.get("speaker") == "Aiden":
        return "Warm, thoughtful British football analyst. Conversational and measured; concise natural phrasing."
    if kind == "goal_reaction":
        return "Excited British football commentator. Immediate clear goal call, energetic but not screaming. No long pauses."
    if kind in ("lead_in","shot_call","attack"):
        return "British live football commentator. Brisk, rising anticipation. Say the words immediately and keep pauses short."
    return "British football broadcaster. Clear, relaxed conversational rhythm. No theatrical pauses."

def trim_silence(audio, sample_rate):
    import numpy as np
    audio = np.asarray(audio, dtype=np.float32).flatten()
    # Keep 15ms at each boundary, and avoid clipping soft consonants.
    active = np.flatnonzero(np.abs(audio) > max(.001, float(np.max(np.abs(audio)))*.008))
    if not len(active): raise ValueError("Speech model produced silence")
    margin = int(sample_rate*.015)
    return audio[max(0, active[0]-margin):min(len(audio),active[-1]+margin+1)]

def run_batch_tts(script_path, slots_path, output_dir=CLIPS_DIR, voice=DEFAULT_VOICE, device="auto", limit=None):
    import torch, soundfile as sf
    from qwen_tts import Qwen3TTSModel
    if device == "auto": device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        # Availability alone does not guarantee support for the GPU architecture.
        (torch.ones((2,2),device="cuda") @ torch.ones((2,2),device="cuda")).cpu()
    elif device == "cpu": torch.set_num_threads(min(8, __import__("os").cpu_count() or 1))
    utterances = json.loads(Path(script_path).read_text(encoding="utf-8-sig"))["utterances"]
    slots = {s["commentary_id"]:s for s in json.loads(Path(slots_path).read_text(encoding="utf-8-sig"))}
    if limit: utterances = sorted(utterances,key=lambda u:slots[u["commentary_id"]].get("priority",1), reverse=True)[:limit]
    output_dir.mkdir(parents=True,exist_ok=True)
    records, pending = [], []
    for u in utterances:
        s = slots[u["commentary_id"]]
        wav = output_dir / (u["commentary_id"]+".wav")
        meta = wav.with_suffix(".json")
        signature = cache_signature(u,s)
        if wav.exists() and meta.exists():
            cached = json.loads(meta.read_text())
            duration = get_wav_duration_seconds(wav)*1000
            if cached.get("signature")==signature and 0 < duration <= s["max_end_ms"]-s["start_ms"]:
                record = cached["record"]
                record.update(requested_start_ms=s["start_ms"],max_end_ms=s["max_end_ms"],pts_offset_seconds=s["start_ms"]/1000)
                records.append(record)
                continue
        pending.append((u,s,signature))
    print(f"TTS device={device}; cached={len(records)}; pending={len(pending)}", flush=True)
    started=time.monotonic()
    model = None
    if pending:
        model=Qwen3TTSModel.from_pretrained(str(TTS_MODELS_DIR),device_map=device,
            dtype=torch.float32 if device=="cpu" else torch.bfloat16, attn_implementation="sdpa")
    for i,(u,s,signature) in enumerate(pending):
        budget=(s["max_end_ms"]-s["start_ms"])/1000
        wav=output_dir/(u["commentary_id"]+".wav")
        accepted=None
        for variant in ("primary","short","emergency_short"):
            text=u[variant]
            # Skip obviously impossible prose rather than generating wasted audio.
            if variant!="emergency_short" and len(text.split()) > max(2, budget*2.8): continue
            print(f"[{i+1}/{len(pending)}] {u['commentary_id']} {s['speaker']} {variant}: {text}",flush=True)
            with torch.inference_mode():
                audio,sr=model.generate_custom_voice(text=text,language="English",speaker=s["speaker"].lower(),
                    instruct=get_instruction_for_slot(s), max_new_tokens=600)
            audio=trim_silence(audio[0],sr)
            duration=len(audio)/sr
            tempo=1.0
            if duration <= budget:
                sf.write(str(wav),audio,sr,subtype="PCM_16")
                accepted=(variant,text,tempo)
                break
            if duration/budget <= 1.10:
                raw=wav.with_name(wav.stem+"_raw.wav")
                sf.write(str(raw),audio,sr,subtype="PCM_16")
                tempo=min(1.10,duration/budget+.005)
                subprocess.run(["ffmpeg","-y","-v","error","-i",str(raw),"-af",f"atempo={tempo:.5f}",
                    "-ar","24000","-ac","1",str(wav)],check=True)
                raw.unlink()
                if get_wav_duration_seconds(wav) <= budget:
                    accepted=(variant,text,tempo)
                    break
        if not accepted: raise RuntimeError(f"No complete speech variant fits {u['commentary_id']} ({budget:.2f}s); not delaying the goal.")
        variant,text,tempo=accepted
        record={"clip_id":u["commentary_id"],"requested_start_ms":s["start_ms"],"max_end_ms":s["max_end_ms"],
            "variant_used":variant,"actual_duration_ms":round(get_wav_duration_seconds(wav)*1000),
            "speaker":s["speaker"],"energy":s["energy_target"],"slot_type":s["slot_type"],
            "priority":s.get("priority",1),"file_path":str(wav),"pts_offset_seconds":s["start_ms"]/1000,
            "atempo_applied":tempo}
        wav.with_suffix(".json").write_text(json.dumps({"signature":signature,"text":text,"record":record},indent=2),encoding="utf-8")
        records.append(record)
    records.sort(key=lambda c:c["requested_start_ms"])
    (output_dir.parent/"audio_clips_manifest.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    (output_dir.parent/"tts_run.json").write_text(json.dumps({"device":device,"torch":torch.__version__,
        "gpu":torch.cuda.get_device_name() if device=="cuda" else None,"seconds":time.monotonic()-started,
        "clips":len(records)},indent=2),encoding="utf-8")
    return records

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--script-path",type=Path,default=ARTIFACTS_DIR/"commentary_script.json")
    p.add_argument("--slots-path",type=Path,default=ARTIFACTS_DIR/"commentary_plan.json")
    p.add_argument("--output-dir",type=Path,default=CLIPS_DIR)
    p.add_argument("--voice",default=DEFAULT_VOICE)
    p.add_argument("--device",default="auto",choices=["auto","cpu","cuda"])
    p.add_argument("--limit",type=int)
    run_batch_tts(**vars(p.parse_args()))
