"""
High-Level Orchestrator for Footy AI Broadcast Commentary Pipeline.
Connects Phases -1 through 13 with intermediate artifact caching and clean VRAM handoffs.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from backend.commentary.config import (
    ARTIFACTS_DIR,
    OUTPUT_DIR,
    GOLDEN_VIDEO_PATH,
    GOLDEN_TIMELINE_PATH,
    GOLDEN_VERIFICATION_PATH,
    GOLDEN_TRACE_NPZ_PATH,
    GOLDEN_GOALS_JSON_PATH,
)
from backend.commentary.inspect_artifacts import inspect_match_artifacts
from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.understanding.event_extractor import EventExtractor
from backend.commentary.understanding.sequences import SequenceBuilder
from backend.commentary.understanding.story_stats import StoryStatsBuilder
from backend.commentary.planning.slot_allocator import SlotAllocator
from backend.commentary.llm.director import CommentaryDirector
from backend.commentary.llm.writer import CommentaryWriter
from backend.commentary.llm.server_manager import LlamaServerManager
from backend.commentary.tts.worker import TTSWorker
from backend.commentary.audio.processor import AudioProcessor
from backend.commentary.audio.ambient_bed import AmbientBedManager
from backend.commentary.audio.mixer import mix_commentary_and_ambience
from backend.commentary.audio.multiplexer import VideoMultiplexer
from backend.commentary.schemas import AudioManifest, CommentaryScript
from backend.commentary.grounding import GroundedCompiler
from backend.commentary.quality import audit_commentary


class CommentaryPipelineOrchestrator:
    """End-to-end executor for match understanding, scriptwriting, TTS and video muxing."""

    def __init__(
        self,
        video_path: Path = GOLDEN_VIDEO_PATH,
        timeline_path: Path = GOLDEN_TIMELINE_PATH,
        verification_path: Path = GOLDEN_VERIFICATION_PATH,
        trace_npz_path: Path = GOLDEN_TRACE_NPZ_PATH,
        goals_json_path: Path = GOLDEN_GOALS_JSON_PATH,
        artifacts_dir: Path = ARTIFACTS_DIR,
        output_dir: Path = OUTPUT_DIR,
        context_path: Optional[Path] = None,
    ):
        self.video_path = video_path
        self.timeline_path = timeline_path
        self.verification_path = verification_path
        self.trace_npz_path = trace_npz_path
        self.goals_json_path = goals_json_path
        self.artifacts_dir = artifacts_dir
        self.output_dir = output_dir
        self.context_path = context_path

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_pipeline(
        self,
        voice: str = "Ryan",
        skip_mux: bool = False,
        tts_engine: str = "auto",
        qwen_tts_limit: Optional[int] = None,
        script_only: bool = False,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        status_path = self.artifacts_dir / 'run_status.json'
        status_path.write_text(json.dumps({'status': 'running', 'started_at': time.time()}))
        try:
            result = self._run_pipeline(voice, skip_mux, tts_engine, qwen_tts_limit, script_only, use_llm)
            status_path.write_text(json.dumps(result, indent=2))
            return result
        except Exception as exc:
            status_path.write_text(json.dumps({'status': 'failed', 'error': str(exc),
                                               'error_type': type(exc).__name__}, indent=2))
            raise

    def _run_pipeline(self, voice, skip_mux, tts_engine, qwen_tts_limit, script_only, use_llm):
        t0 = time.time()
        print("=== Step 1: Phase -1 Artifact Inspection ===")
        artifact_report = inspect_match_artifacts(
            video_path=self.video_path,
            timeline_path=self.timeline_path,
            verification_path=self.verification_path,
            trace_npz_path=self.trace_npz_path,
            goals_json_path=self.goals_json_path,
            output_dir=self.artifacts_dir,
        )

        print("=== Step 2: Phase 0 Presentation Timeline Adapter ===")
        timeline = TimelineAdapter(self.timeline_path)

        print("=== Step 3: Phase 1 Deterministic Event Extraction ===")
        extractor = EventExtractor(self.trace_npz_path, timeline)
        events = extractor.extract_events()
        events_json = self.artifacts_dir / "events_enriched.json"
        with open(events_json, "w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in events], f, indent=2)

        print("=== Step 4: Phase 2 Sequence Building ===")
        seq_builder = SequenceBuilder(home_team=extractor.home_team, away_team=extractor.away_team)
        sequences = seq_builder.build_sequences(events)
        seqs_json = self.artifacts_dir / "sequences.json"
        with open(seqs_json, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in sequences], f, indent=2)

        print("=== Step 5: Phase 4 Match Context & Storylines ===")
        extra_evidence = []
        if self.context_path:
            from backend.commentary.understanding.broadcast_context import snapshot_evidence
            snapshot = json.loads(self.context_path.read_text(encoding='utf-8-sig'))
            extra_evidence = snapshot_evidence(snapshot, extractor.manifest,
                hashlib.sha256(self.trace_npz_path.read_bytes()).hexdigest(), self.trace_npz_path.parent.name)
            (self.artifacts_dir/'broadcast_context_snapshot.json').write_text(json.dumps(snapshot,indent=2))
        story_builder = StoryStatsBuilder(extractor.manifest, extra_evidence)
        match_context = story_builder.build_match_context(events, sequences)
        ctx_json = self.artifacts_dir / "match_context.json"
        with open(ctx_json, "w", encoding="utf-8") as f:
            json.dump(match_context.model_dump(), f, indent=2)

        print("=== Step 6: Phase 5 Deterministic Slot Allocation ===")
        allocator = SlotAllocator(timeline)
        slots = allocator.allocate_slots(events, sequences, match_context)
        slots_json = self.artifacts_dir / "commentary_plan.json"
        with open(slots_json, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in slots], f, indent=2)

        # Resume only a script matching this exact context, plan and writer code.
        scripts = [Path(__file__).parent / name for name in ('grounding.py','speech_text.py','schemas.py')]
        scripts += list((Path(__file__).parent/'llm').glob('*.py'))
        signature_data = dict(context=match_context.model_dump(), plan=[s.model_dump() for s in slots], use_llm=use_llm,
                              code={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in scripts})
        signature = hashlib.sha256(json.dumps(signature_data,sort_keys=True).encode()).hexdigest()
        (self.artifacts_dir/'commentary_plan.allocated.json').write_text(json.dumps([s.model_dump() for s in slots],indent=2))
        signature_path = self.artifacts_dir/'script_signature.json'
        script_path = self.artifacts_dir/'commentary_script.compiled.json'
        cached = None
        if signature_path.exists() and script_path.exists():
            try:
                cache_metadata = json.loads(signature_path.read_text())
                if (cache_metadata.get('signature') == signature and
                        cache_metadata.get('compiled_sha256') == hashlib.sha256(script_path.read_bytes()).hexdigest()):
                    cached = CommentaryScript.model_validate_json(script_path.read_text())
                    compiler = GroundedCompiler(match_context)
                    slot_map = {s.commentary_id:s for s in slots}
                    if not all(compiler.validate(u, slot_map[u.commentary_id])[0] for u in cached.utterances):
                        cached = None
            except (ValueError, KeyError):
                cached = None

        print("=== Step 7: Phase 6-8 Qwen3.5 Director & Writer (with Fact Firewall) ===")
        server_mgr = LlamaServerManager()
        server_started = False
        if cached is None and use_llm and server_mgr.is_binary_ready() and server_mgr.is_model_ready():
            print("Launching local Qwen3.5-9B llama-server on GPU...")
            server_started = server_mgr.start_server()

        try:
            director = CommentaryDirector(match_context)
            directed_slots = director.direct_slots(slots)
            writer = CommentaryWriter(match_context)
            if not use_llm:
                writer.client._server_available = False
            script = cached or writer.write_script(directed_slots)
            if cached is None:
                (self.artifacts_dir / 'writer_diagnostics.json').write_text(json.dumps(writer.diagnostics, indent=2), encoding='utf-8')
            (self.artifacts_dir/'sentence_provenance.json').write_text(json.dumps([
                dict(id=u.commentary_id, primary=u.primary, short=u.short, emergency_short=u.emergency_short,
                     **u.grounding) for u in script.utterances],indent=2))
            kept_ids = {u.commentary_id for u in script.utterances}
            directed_slots = [s for s in directed_slots if s.commentary_id in kept_ids]
            slots_json.write_text(json.dumps([s.model_dump() for s in directed_slots],indent=2))
            script_json = self.artifacts_dir / "commentary_script.json"
            with open(script_json, "w", encoding="utf-8") as f:
                json.dump(script.model_dump(), f, indent=2)
            script_path.write_text(script.model_dump_json(indent=2),encoding='utf-8')
            signature_path.write_text(json.dumps({'signature':signature,
                'compiled_sha256':hashlib.sha256(script_path.read_bytes()).hexdigest()}))
        finally:
            if server_started:
                print("Stopping llama-server and releasing VRAM before TTS...")
                server_mgr.stop_server()

        if script_only:
            return dict(status='script_ready', match_id=match_context.match_id,
                        slots=len(directed_slots), script=str(script_json), cached_script=cached is not None)

        print("=== Step 8: Phase 9-10 Speech Synthesis (Multi-Variant Duration Fitting) ===")
        worker = TTSWorker(voice=voice, clips_dir=self.artifacts_dir / 'clips')
        clips = worker.synthesize_script(
            script=script,
            slots=directed_slots,
            engine=tts_engine,
            qwen_limit=qwen_tts_limit,
        )
        voiced_ids = {c.clip_id for c in clips}
        if any(s.slot_type in ('goal_reaction','halftime_recap','fulltime_summary') and
               s.commentary_id not in voiced_ids for s in directed_slots):
            raise RuntimeError('Required commentary is missing')
        directed_slots = [s for s in directed_slots if s.commentary_id in voiced_ids]
        script.utterances = [u for u in script.utterances if u.commentary_id in voiced_ids]
        slots_json.write_text(json.dumps([s.model_dump() for s in directed_slots],indent=2))
        script_json.write_text(script.model_dump_json(indent=2),encoding='utf-8')

        print("=== Step 9: Phase 11 Audio Assembly (48kHz Master Timeline) ===")
        processor = AudioProcessor(master_duration_seconds=timeline.total_duration_seconds)
        commentary_track_path = self.artifacts_dir / "commentary_track.wav"
        commentary_track_path, total_speech_sec = processor.assemble_master_track(clips, commentary_track_path)

        manifest = AudioManifest(
            match_id=match_context.match_id,
            clips=clips,
            total_commentary_duration_seconds=total_speech_sec,
            master_track_path=str(commentary_track_path),
        )
        manifest_json = self.artifacts_dir / "audio_manifest.json"
        with open(manifest_json, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)

        print("=== Step 10: Phase 12 Ambient Stadium Bed & Voice Ducking ===")
        ambient_mgr = AmbientBedManager(duration_seconds=timeline.total_duration_seconds)
        ambient_track_path = self.artifacts_dir / "stadium_ambient.wav"
        ambient_track_path = ambient_mgr.generate_ducked_ambient_track(clips, ambient_track_path)

        print("=== Step 11: Audio Mixing (Speech + Ambient Bed) ===")
        master_audio_path = self.artifacts_dir / "commentary_master.wav"
        master_audio_path = mix_commentary_and_ambience(commentary_track_path, ambient_track_path, master_audio_path)

        final_mp4_path = None
        validation_report = {}
        if not skip_mux and self.video_path.exists():
            print("=== Step 12: Phase 13 FFmpeg Multiplexing ===")
            final_mp4_path = self.output_dir / f"{self.video_path.stem}-commentary.mp4"
            VideoMultiplexer.mux(self.video_path, master_audio_path, final_mp4_path)
            validation_report = VideoMultiplexer.validate_mp4(final_mp4_path)
            print(f"Multiplexed broadcast video written to: {final_mp4_path}")

        elapsed = round(time.time() - t0, 2)
        quality = audit_commentary(self.artifacts_dir, timeline, self.video_path if final_mp4_path else None, final_mp4_path)
        print(f"=== Pipeline completed successfully in {elapsed}s ===")

        return {
            "status": "success",
            "elapsed_seconds": elapsed,
            "match_id": match_context.match_id,
            "score": match_context.score_str,
            "total_slots": len(slots),
            "total_clips": len(clips),
            "total_speech_seconds": total_speech_sec,
            "speech_density_pct": round((total_speech_sec / timeline.total_duration_seconds) * 100, 1),
            "output_video": str(final_mp4_path) if final_mp4_path else None,
            "output_audio": str(master_audio_path),
            "validation_report": validation_report,
            "quality_report": quality,
        }
