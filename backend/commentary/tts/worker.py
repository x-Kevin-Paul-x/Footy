"""
Phase 9-10: Qwen3-TTS Worker & Duration Fitting.
Synthesizes native 24 kHz mono speech clips.
Implements cascading length fallback: primary -> short -> emergency_short.
Uses FFmpeg atempo micro-adjustment (±3-8%) only when close.
"""

import os
import sys
import json
import wave
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Literal, List

from backend.commentary.schemas import (
    CommentaryUtterance,
    CommentarySlot,
    CommentaryScript,
    AudioClip,
)
from backend.commentary.config import (
    CLIPS_DIR,
    TTS_MODELS_DIR,
    TTS_VENV_DIR,
    NATIVE_TTS_SAMPLE_RATE,
    DEFAULT_VOICE,
)


def get_wav_duration_seconds(filepath: Path) -> float:
    """Read exact duration of a WAV file in seconds."""
    if not filepath.exists():
        return 0.0
    with wave.open(str(filepath), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


class TTSWorker:
    """Synthesizes speech clips with cascading length variants and VRAM safety."""

    def __init__(self, voice: str = DEFAULT_VOICE, clips_dir: Path = CLIPS_DIR):
        self.voice = voice
        self.clips_dir = clips_dir
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.omissions = []

    def synthesize_script(
        self,
        script: CommentaryScript,
        slots: List[CommentarySlot],
        engine: str = "auto",
        qwen_limit: Optional[int] = None,
    ) -> List[AudioClip]:
        """
        Synthesize speech clips for an entire script.
        If engine == 'qwen' or ('auto' with Qwen-TTS available):
          Invokes batch_runner.py using .venv-tts, cleanly unloading the model afterwards.
        Falls back to per-clip speech synthesizer if Qwen is not available or errors.
        """
        python_exe = TTS_VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        slot_map = {s.commentary_id: s for s in slots}
        slots = [slot_map[u.commentary_id] for u in script.utterances]
        batch_script = Path(__file__).resolve().parent / "batch_runner.py"

        use_qwen = False
        if engine == "qwen":
            use_qwen = True
        elif engine == "auto":
            if python_exe.exists() and (TTS_MODELS_DIR / "model.safetensors").exists():
                use_qwen = True

        if use_qwen:
            try:
                print("Running neural synthesis via Qwen3-TTS batch runner...")
                script_path = self.clips_dir.parent / 'commentary_script.json'
                slots_path = self.clips_dir.parent / 'commentary_plan.json'
                script_path.write_text(script.model_dump_json(indent=2), encoding='utf-8')
                slots_path.write_text(json.dumps([s.model_dump() for s in slots]), encoding='utf-8')
                cmd = [
                    str(python_exe),
                    str(batch_script),
                    "--voice", self.voice,
                    "--device", "auto",
                    "--script-path", str(script_path),
                    "--slots-path", str(slots_path),
                    "--output-dir", str(self.clips_dir),
                ]
                if qwen_limit:
                    cmd.extend(["--limit", str(qwen_limit)])

                subprocess.run(cmd, check=True)
                manifest_path = self.clips_dir.parent / "audio_clips_manifest.json"
                if manifest_path.exists():
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        raw_clips = json.load(f)
                    clips = [AudioClip(**c) for c in raw_clips]
                    omission_path = self.clips_dir.parent / 'tts_omissions.json'
                    self.omissions = json.loads(omission_path.read_text()) if omission_path.exists() else []
                    omitted_ids = {o['id'] for o in self.omissions}
                    expected_ids = {u.commentary_id for u in script.utterances}
                    if any(slot_map[cid].slot_type in ('goal_reaction','halftime_recap','fulltime_summary') for cid in omitted_ids):
                        raise RuntimeError('A required speech slot cannot be omitted')
                    if ({c.clip_id for c in clips} | omitted_ids == expected_ids and
                            len(clips)+len(omitted_ids) == len(expected_ids) and
                            not ({c.clip_id for c in clips} & omitted_ids)):
                        return sorted(clips, key=lambda c:c.requested_start_ms)
                    if not qwen_limit:
                        raise RuntimeError('Neural clip set is incomplete or contains unexpected IDs')
                    if len(clips) == len(script.utterances):
                        return clips
                    print(f"Batch runner produced {len(clips)}/{len(script.utterances)} clips. Completing remaining with fallback...")
                    existing_cids = {c.clip_id for c in clips}
                    for utt, slot in zip(script.utterances, slots):
                        if utt.commentary_id not in existing_cids:
                            clips.append(self.synthesize_clip(utt, slot))
                    return sorted(clips, key=lambda c: c.requested_start_ms)
            except Exception as e:
                if use_qwen:
                    raise RuntimeError('Neural speech failed; refusing to silently replace the two voices with SAPI') from e
                print(f"Qwen3-TTS batch runner error: {e}. Falling back to standard speech engine...")

        clips = []
        for utt, slot in zip(script.utterances, slots):
            clip = self.synthesize_clip(utt, slot)
            clips.append(clip)
        return clips

    def _synthesize_windows_tts_fallback(self, text: str, output_path: Path, rate: int = 0) -> bool:
        """Fallback local TTS using Windows SpeechSynthesizer with English voice selection."""
        if sys.platform != 'win32':
            raise RuntimeError('Windows speech fallback is unavailable; configure the Qwen TTS engine on this platform')
        ps_script = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = {rate}
$v = $s.GetInstalledVoices() | Where-Object {{ $_.Enabled -and ($_.VoiceInfo.Culture.Name -like 'en-GB*' -or $_.VoiceInfo.Culture.Name -like 'en-US*') }} | Select-Object -First 1
if ($v) {{ $s.SelectVoice($v.VoiceInfo.Name) }}
$s.SetOutputToWaveFile('{output_path.resolve()}')
$s.Speak('{text.replace("'", "''")}')
$s.Dispose()
"""
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return output_path.exists() and output_path.stat().st_size > 44

    def _apply_atempo(self, input_wav: Path, output_wav: Path, tempo: float) -> bool:
        """Applies minor atempo speed adjustment using FFmpeg."""
        tempo = max(0.90, min(1.10, tempo))
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_wav),
            "-filter:a", f"atempo={tempo:.3f}",
            "-ar", str(NATIVE_TTS_SAMPLE_RATE),
            "-ac", "1",
            str(output_wav),
        ]
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0

    def synthesize_clip(
        self,
        utterance: CommentaryUtterance,
        slot: CommentarySlot,
    ) -> AudioClip:
        """
        Synthesizes utterance into a clip.
        Tries primary -> short -> emergency_short to fit within slot.window_seconds.
        """
        cid = utterance.commentary_id
        target_sec = slot.window_seconds
        target_ms = int(target_sec * 1000)

        variants = [
            ("primary", utterance.primary),
            ("short", utterance.short),
            ("emergency_short", utterance.emergency_short),
        ]

        best_variant = "primary"
        best_wav = self.clips_dir / f"{cid}.wav"
        temp_wav = self.clips_dir / f"{cid}_temp.wav"
        actual_dur_sec = 0.0
        atempo_applied = 1.0

        for var_name, text in variants:
            if not text.strip():
                continue

            # Calculate speaking rate for fallback (-1 to +4)
            sapi_rate = 0
            if slot.energy_target >= 0.90:
                sapi_rate = 3
            elif slot.energy_target >= 0.70:
                sapi_rate = 1

            success = self._synthesize_windows_tts_fallback(text, temp_wav, rate=sapi_rate)
            if not success:
                continue

            dur = get_wav_duration_seconds(temp_wav)
            best_variant = var_name
            actual_dur_sec = dur

            # If it fits with at least 0.2s margin, accept immediately
            if dur <= target_sec:
                temp_wav.replace(best_wav)
                break
            else:
                # If this was the last variant and slightly oversized, check atempo
                if var_name == "emergency_short":
                    ratio = dur / max(0.5, target_sec)
                    if 1.0 < ratio <= 1.10:
                        tempo = ratio
                        self._apply_atempo(temp_wav, best_wav, tempo)
                        atempo_applied = tempo
                        actual_dur_sec = get_wav_duration_seconds(best_wav)
                        temp_wav.unlink(missing_ok=True)
                        if actual_dur_sec <= target_sec:
                            break

        if not best_wav.exists() or get_wav_duration_seconds(best_wav) > target_sec:
            raise RuntimeError(f'No speech variant fits {cid}; refusing timing drift')

        actual_dur_ms = int(get_wav_duration_seconds(best_wav) * 1000)
        pts_offset_sec = slot.start_ms / 1000.0

        clip = AudioClip(
            clip_id=cid,
            requested_start_ms=slot.start_ms,
            max_end_ms=slot.max_end_ms,
            variant_used=best_variant,
            actual_duration_ms=actual_dur_ms,
            speaker=slot.speaker,
            slot_type=slot.slot_type,
            priority=slot.priority,
            energy=slot.energy_target,
            file_path=str(best_wav),
            pts_offset_seconds=pts_offset_sec,
            atempo_applied=atempo_applied,
        )
        best_wav.with_suffix('.json').write_text(json.dumps({
            'engine':'sapi','text':getattr(utterance,best_variant),'record':clip.model_dump(),
        },indent=2),encoding='utf-8')
        return clip
