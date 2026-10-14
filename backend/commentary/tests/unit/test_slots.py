"""
Unit tests for SlotAllocator.
"""

import pytest
from backend.commentary.schemas import (
    CommentarySlot,
    FootballSequence,
    EnrichedEvent,
    MatchContext,
    TTSCalibration,
)
from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.planning.slot_allocator import SlotAllocator
from backend.commentary.config import GOLDEN_TIMELINE_PATH


def test_slot_non_overlapping():
    if not GOLDEN_TIMELINE_PATH.exists():
        pytest.skip("Golden timeline not found")

    tl = TimelineAdapter(GOLDEN_TIMELINE_PATH)
    sa = SlotAllocator(tl)

    events = [
        EnrichedEvent(
            event_id="evt_001",
            type="GOAL",
            step=777,
            presentation_ms=80700,
            match_minute=24,
            team="Bournemouth",
            player="Misty Noble",
            facts={"score": "0-1", "scorer": "Misty Noble"},
        )
    ]
    seqs = [
        FootballSequence(
            sequence_id="seq_001",
            type="GOAL_SEQUENCE",
            team="Bournemouth",
            start_step=700,
            end_step=777,
            start_ms=75000,
            end_ms=80700,
            danger=1.0,
            importance=1.0,
            events=["Misty Noble scores"],
            outcome="GOAL",
        )
    ]
    mc = MatchContext(
        match_id="test",
        home_team="Burnley",
        away_team="Bournemouth",
        home_score=0,
        away_score=1,
        score_str="Burnley 0-1 Bournemouth",
    )

    slots = sa.allocate_slots(events, seqs, mc)
    assert len(slots) >= 2  # intro + goal slots
    for i in range(len(slots) - 1):
        assert slots[i].max_end_ms <= slots[i + 1].start_ms, f"Slot {slots[i].commentary_id} overlaps {slots[i+1].commentary_id}"
