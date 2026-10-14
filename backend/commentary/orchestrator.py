"""
High-Level Orchestrator for Footy AI Broadcast Commentary Pipeline.
Connects Phases -1 through 13 with intermediate artifact caching and clean VRAM handoffs.
"""

import json
import time
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
from backend.commentary.schemas import AudioManifest
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
    ):
        self.video_path = video_path
        self.timeline_path = timeline_path
        self.verification_path = verification_path
        self.trace_npz_path = trace_npz_path
        self.goals_json_path = goals_json_path
        self.artifacts_dir = artifacts_dir
        self.output_dir = output_dir

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_pipeline(
        self,
        voice: str = "Ryan",
        skip_mux: bool = False,
        tts_engine: str = "auto",
        qwen_tts_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
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
        story_builder = StoryStatsBuilder(extractor.manifest)
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

        print("=== Step 7: Phase 6-8 Qwen3.5 Director & Writer (with Fact Firewall) ===")
        server_mgr = LlamaServerManager()
        server_started = False
        if server_mgr.is_binary_ready() and server_mgr.is_model_ready():
            print("Launching local Qwen3.5-9B llama-server on GPU...")
            server_started = server_mgr.start_server()

        try:
            director = CommentaryDirector(match_context)
            directed_slots = director.direct_slots(slots)
            writer = CommentaryWriter(match_context)
            script = writer.write_script(directed_slots)
            (self.artifacts_dir / 'writer_diagnostics.json').write_text(json.dumps(writer.diagnostics, indent=2), encoding='utf-8')
            script_json = self.artifacts_dir / "commentary_script.json"
            with open(script_json, "w", encoding="utf-8") as f:
                json.dump(script.model_dump(), f, indent=2)
        finally:
            if server_started:
                print("Stopping llama-server and releasing VRAM before TTS...")
                server_mgr.stop_server()

        print("=== Step 8: Phase 9-10 Speech Synthesis (Multi-Variant Duration Fitting) ===")
        worker = TTSWorker(voice=voice, clips_dir=self.artifacts_dir / 'clips')
        clips = worker.synthesize_script(
            script=script,
            slots=directed_slots,
            engine=tts_engine,
            qwen_limit=qwen_tts_limit,
        )

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
            final_mp4_path = self.output_dir / "burnley-2-4-bournemouth-commentary.mp4"
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
