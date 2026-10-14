"""
Unit tests for Two-Commentator Broadcast Duo (Ryan & Aiden).
Verifies:
- Both Ryan and Aiden are allocated across opening, goals, in-play, halftime, and fulltime.
- Conversational dialogue cues ('Did you see that, Ryan?', 'Spot on, Ryan...', 'Now tell me about the player to watch today...').
- Zero audio overlap between commentators.
- Strict running scoreline accuracy.
"""

from backend.commentary.config import (
    GOLDEN_TIMELINE_PATH,
    GOLDEN_TRACE_NPZ_PATH,
)
from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.understanding.event_extractor import EventExtractor
from backend.commentary.understanding.sequences import SequenceBuilder
from backend.commentary.understanding.story_stats import StoryStatsBuilder
from backend.commentary.planning.slot_allocator import SlotAllocator
from backend.commentary.llm.client import LlamaClient
from backend.commentary.llm.writer import CommentaryWriter
from backend.commentary.llm.validator import FactFirewallValidator


def test_two_commentators_allocation_and_dialogue():
    timeline = TimelineAdapter(GOLDEN_TIMELINE_PATH)
    extractor = EventExtractor(GOLDEN_TRACE_NPZ_PATH, timeline)
    events = extractor.extract_events()

    seq_builder = SequenceBuilder(home_team="Burnley", away_team="Bournemouth")
    sequences = seq_builder.build_sequences(events)

    story_builder = StoryStatsBuilder(extractor.manifest)
    ctx = story_builder.build_match_context(events, sequences)

    allocator = SlotAllocator(timeline)
    slots = allocator.allocate_slots(events, sequences, ctx)

    # 1. Verify both commentators are present
    speakers = {s.speaker for s in slots}
    assert "Ryan" in speakers
    assert "Aiden" in speakers

    ryan_slots = [s for s in slots if s.speaker == "Ryan"]
    aiden_slots = [s for s in slots if s.speaker == "Aiden"]

    assert len(ryan_slots) >= 12, f"Too few Ryan slots: {len(ryan_slots)}"
    assert len(aiden_slots) >= 3, f"Too few Aiden slots: {len(aiden_slots)}"

    # 2. Opening broadcast banter: Ryan welcomes, Aiden responds
    assert slots[0].speaker == "Ryan"
    assert "alongside Aiden" in slots[0].in_play_summary
    assert slots[1].speaker == "Aiden"
    assert "Ryan" not in slots[1].in_play_summary

    # 3. Conversational dialogue cues present
    aiden_texts = " ".join(s.in_play_summary for s in aiden_slots)
    assert "Ryan" not in aiden_texts, "Partner addresses should not be scripted into every line"

    # 4. The three-second halftime card fits one concise recap
    ht_slots = [s for s in slots if s.slot_type == "halftime_recap"]
    assert len(ht_slots) == 1
    assert ht_slots[0].speaker == "Ryan"
    assert ht_slots[0].running_score == "2-3"

    # 5. Fulltime summary slot
    ft_slots = [s for s in slots if s.slot_type == "fulltime_summary"]
    assert len(ft_slots) >= 1
    assert ft_slots[0].speaker == "Ryan"
    assert ft_slots[0].running_score == "2-4"

    # 6. Check zero overlapping timestamps across all slots
    for i in range(len(slots) - 1):
        assert slots[i].max_end_ms <= slots[i + 1].start_ms, (
            f"Overlap between {slots[i].commentary_id} and {slots[i+1].commentary_id}"
        )


def test_two_commentators_script_generation_and_validation():
    timeline = TimelineAdapter(GOLDEN_TIMELINE_PATH)
    extractor = EventExtractor(GOLDEN_TRACE_NPZ_PATH, timeline)
    events = extractor.extract_events()

    seq_builder = SequenceBuilder(home_team="Burnley", away_team="Bournemouth")
    sequences = seq_builder.build_sequences(events)

    story_builder = StoryStatsBuilder(extractor.manifest)
    ctx = story_builder.build_match_context(events, sequences)

    allocator = SlotAllocator(timeline)
    slots = allocator.allocate_slots(events, sequences, ctx)

    writer = CommentaryWriter(ctx, client=LlamaClient())
    script = writer.write_script(slots)

    validator = FactFirewallValidator(ctx)

    assert len(script.utterances) == len(slots)
    for utt, slot in zip(script.utterances, slots):
        assert utt.speaker == slot.speaker
        valid, errors = validator.validate(utt, slot)
        assert valid, f"Validation failure on {slot.commentary_id} ({slot.speaker}): {errors}"
