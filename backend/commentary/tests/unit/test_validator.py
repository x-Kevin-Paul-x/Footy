"""
Unit tests for FactFirewallValidator and RepetitionDetector.
"""

import pytest
from backend.commentary.schemas import CommentarySlot, CommentaryUtterance, MatchContext
from backend.commentary.llm.validator import FactFirewallValidator, RepetitionDetector


def test_fact_firewall_accepts_valid():
    mc = MatchContext(
        match_id="test",
        home_team="Burnley",
        away_team="Bournemouth",
        home_score=2,
        away_score=4,
        score_str="Burnley 2-4 Bournemouth",
        allowed_facts={
            "fact_0001": "The home team is Burnley.",
            "fact_0029": "In minute 24, Misty Noble scored for Bournemouth, making the score 0-1.",
        },
    )
    val = FactFirewallValidator(mc)
    slot = CommentarySlot(
        commentary_id="com_010",
        start_ms=80700,
        max_end_ms=85300,
        window_seconds=4.6,
        slot_type="goal_reaction",
        running_score="0-1",
        active_player="Misty Noble",
    )
    utt = CommentaryUtterance(
        commentary_id="com_010",
        speaker="Ryan",
        energy=0.98,
        emotion="explosive joy",
        target_duration_ms=4600,
        primary="GOAL! Misty Noble finds the net, making it 0-1!",
        short="GOAL! Misty Noble scores - it is 0-1!",
        emergency_short="GOAL! Misty Noble!",
        used_fact_ids=["fact_0029"],
    )
    is_valid, errors = val.validate(utt, slot)
    assert is_valid, f"Validation failed with: {errors}"


def test_fact_firewall_rejects_hallucinated_facts():
    mc = MatchContext(
        match_id="test",
        home_team="Burnley",
        away_team="Bournemouth",
        home_score=2,
        away_score=4,
        score_str="Burnley 2-4 Bournemouth",
        allowed_facts={"fact_0001": "The home team is Burnley."},
    )
    val = FactFirewallValidator(mc)
    slot = CommentarySlot(
        commentary_id="com_010",
        start_ms=80700,
        max_end_ms=85300,
        window_seconds=4.6,
        slot_type="goal_reaction",
        running_score="0-1",
        active_player="Misty Noble",
    )
    utt = CommentaryUtterance(
        commentary_id="com_010",
        speaker="Ryan",
        energy=0.98,
        emotion="explosive joy",
        target_duration_ms=4600,
        primary="GOAL! They make it 7-3!",
        short="GOAL! 7-3!",
        emergency_short="GOAL!",
        used_fact_ids=["fact_9999"],  # Non-existent fact
    )
    is_valid, errors = val.validate(utt, slot)
    assert not is_valid
    assert any("Unknown cited fact ID" in e for e in errors)
    assert any("Illegal scoreline" in e for e in errors)


def test_repetition_detector():
    rep = RepetitionDetector(memory_window=3)
    is_rep1, _, _ = rep.check_repetition("There is space opening up here on the right wing.")
    assert not is_rep1
    is_rep2, _, _ = rep.check_repetition("Burnley moving possession calmly through midfield.")
    assert not is_rep2
    # Heavy reuse of 3-grams
    is_rep3, ratio, phrase = rep.check_repetition("There is space opening up here on the left flank.")
    assert is_rep3
    assert ratio >= 0.35
