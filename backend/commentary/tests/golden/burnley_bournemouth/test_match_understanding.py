"""
Golden match integration test for Burnley 2-4 Bournemouth (match_2026_20_3).
Verifies exact ground-truth recreation:
- 6 goals and exact scorers
- Exact presentation timestamps
- Goal lead-in and reaction alignment
- 310.7 second video duration
"""

import pytest
from backend.commentary.config import (
    GOLDEN_TRACE_NPZ_PATH,
    GOLDEN_TIMELINE_PATH,
)
from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.understanding.event_extractor import EventExtractor
from backend.commentary.understanding.sequences import SequenceBuilder
from backend.commentary.understanding.story_stats import StoryStatsBuilder
from backend.commentary.planning.slot_allocator import SlotAllocator


def test_burnley_bournemouth_golden_pipeline():
    assert GOLDEN_TRACE_NPZ_PATH.exists(), f"Missing trace NPZ at {GOLDEN_TRACE_NPZ_PATH}"
    assert GOLDEN_TIMELINE_PATH.exists(), f"Missing timeline JSON at {GOLDEN_TIMELINE_PATH}"

    # 1. Timeline
    tl = TimelineAdapter(GOLDEN_TIMELINE_PATH)
    assert tl.total_duration_seconds == 310.7
    assert tl.fps == 10.0

    # 2. Event Extraction
    ee = EventExtractor(GOLDEN_TRACE_NPZ_PATH, tl)
    events = ee.extract_events()
    assert len(events) > 80

    goals = [e for e in events if e.type == "GOAL"]
    assert len(goals) == 6

    expected_goals = [
        ("Bournemouth", "Misty Noble", 80700, "0-1"),
        ("Burnley", "William Ruggiero", 89500, "1-1"),
        ("Burnley", "Jimmy Bigler", 108500, "2-1"),
        ("Bournemouth", "Christina Hite", 125400, "2-2"),
        ("Bournemouth", "Howard Seibert", 151800, "2-3"),
        ("Bournemouth", "Edward Crespo", 274000, "2-4"),
    ]

    for g, exp in zip(goals, expected_goals):
        assert g.team == exp[0]
        assert g.player == exp[1]
        assert g.presentation_ms == exp[2]
        assert g.facts.get("score") == exp[3]

    # 3. Sequences
    sb = SequenceBuilder(home_team="Burnley", away_team="Bournemouth")
    seqs = sb.build_sequences(events)
    goal_seqs = [s for s in seqs if s.type == "GOAL_SEQUENCE"]
    assert len(goal_seqs) == 6

    # 4. Match Context & Fact Whitelist
    ss = StoryStatsBuilder(ee.manifest)
    mc = ss.build_match_context(events, seqs)
    assert mc.home_score == 2
    assert mc.away_score == 4
    assert len(mc.allowed_facts) > 25

    # 5. Slot Allocator
    sa = SlotAllocator(tl)
    slots = sa.allocate_slots(events, seqs, mc)
    assert len(slots) >= 25

    # Check zero overlaps
    for i in range(len(slots) - 1):
        assert slots[i].max_end_ms <= slots[i + 1].start_ms, (
            f"Overlap detected: {slots[i].commentary_id} ends at {slots[i].max_end_ms}ms, "
            f"but {slots[i+1].commentary_id} starts at {slots[i+1].start_ms}ms"
        )

    # A fitting window is a budget, not the duration of the selected speech.
    # Density and quiet gaps are measured from rendered clips in quality.py.
    assert max(s.window_seconds for s in slots) <= 6, 'Avoid uninterrupted long monologues'

    # Check exact goal reactions start at goal timestamps
    rxn_slots = [s for s in slots if s.slot_type == "goal_reaction"]
    assert len(rxn_slots) == 6
    for rxn, exp in zip(rxn_slots, expected_goals):
        assert rxn.start_ms == exp[2], f"Goal reaction start {rxn.start_ms}ms does not match goal PTS {exp[2]}ms"

    # Anticipation is selected from observations, including attacks which do
    # not become goals. It must not require hindsight about the future scorer.
    attacks = [s for s in slots if s.slot_type in ('attack','shot_call')]
    assert attacks
    for attack in attacks:
        observed = [e for e in events if e.presentation_ms == attack.start_ms and
                    e.team == attack.active_team and e.player == attack.active_player and
                    e.type == attack.active_event_type]
        assert observed, 'Anticipation must cite an observation already available at its anchor'
        for goal in goals:
            if attack.start_ms < goal.presentation_ms:
                assert attack.max_end_ms <= goal.presentation_ms, 'Live buildup cannot delay a goal call'
