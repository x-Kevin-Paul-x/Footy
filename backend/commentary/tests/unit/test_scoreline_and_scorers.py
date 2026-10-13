"""
Unit tests verifying strict scoreline progression, active scorer attribution,
and anti-spoiler guarantees across the Burnley vs Bournemouth golden match.
"""

from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.understanding.event_extractor import EventExtractor
from backend.commentary.understanding.sequences import SequenceBuilder
from backend.commentary.understanding.story_stats import StoryStatsBuilder
from backend.commentary.planning.slot_allocator import SlotAllocator
from backend.commentary.config import (
    GOLDEN_TIMELINE_PATH,
    GOLDEN_TRACE_NPZ_PATH,
)


def test_scorer_attribution_and_scoreline_progression():
    timeline = TimelineAdapter(GOLDEN_TIMELINE_PATH)
    extractor = EventExtractor(GOLDEN_TRACE_NPZ_PATH, timeline)
    events = extractor.extract_events()

    seq_builder = SequenceBuilder(home_team="Burnley", away_team="Bournemouth")
    sequences = seq_builder.build_sequences(events)

    story_builder = StoryStatsBuilder(extractor.manifest)
    ctx = story_builder.build_match_context(events, sequences)

    allocator = SlotAllocator(timeline)
    slots = allocator.allocate_slots(events, sequences, ctx)

    # 1. Verify all 6 goal reaction slots
    goal_slots = [s for s in slots if s.slot_type == "goal_reaction"]
    assert len(goal_slots) == 6, f"Expected 6 goal reaction slots, got {len(goal_slots)}"

    expected_goals = [
        {"scorer": "Misty Noble", "team": "Bournemouth", "score": "0-1"},
        {"scorer": "William Ruggiero", "team": "Burnley", "score": "1-1"},
        {"scorer": "Jimmy Bigler", "team": "Burnley", "score": "2-1"},
        {"scorer": "Christina Hite", "team": "Bournemouth", "score": "2-2"},
        {"scorer": "Howard Seibert", "team": "Bournemouth", "score": "2-3"},
        {"scorer": "Edward Crespo", "team": "Bournemouth", "score": "2-4"},
    ]

    for gs, expected in zip(goal_slots, expected_goals):
        assert gs.active_player == expected["scorer"], f"Slot {gs.commentary_id} has wrong scorer {gs.active_player}, expected {expected['scorer']}"
        assert gs.active_team == expected["team"], f"Slot {gs.commentary_id} has wrong team {gs.active_team}, expected {expected['team']}"
        assert gs.running_score == expected["score"], f"Slot {gs.commentary_id} has wrong score {gs.running_score}, expected {expected['score']}"

    # 2. Verify no slot before minute 80 mentions score 2-4
    for s in slots:
        if s.match_minute < 80:
            assert s.running_score != "2-4", f"Slot {s.commentary_id} in minute {s.match_minute} has premature score 2-4!"

    # 3. Verify zero overlaps between consecutive slots (gap_ms >= 0)
    for i in range(len(slots) - 1):
        s1 = slots[i]
        s2 = slots[i + 1]
        gap_ms = s2.start_ms - s1.max_end_ms
        assert gap_ms >= 0, f"Slots {s1.commentary_id} and {s2.commentary_id} overlap: {gap_ms}ms"
