"""
Unit tests for deterministic Event Extraction.
"""

import pytest
import numpy as np
from pathlib import Path

from backend.commentary.schemas import EnrichedEvent
from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.config import GOLDEN_TIMELINE_PATH


def test_enriched_event_schema():
    evt = EnrichedEvent(
        event_id="evt_0001",
        type="PASS",
        step=100,
        presentation_ms=12000,
        match_minute=3,
        team="Burnley",
        player="William Ruggiero",
        position=[0.1, -0.2],
        importance=0.4,
        danger=0.3,
        facts={"passer": "William Ruggiero", "receiver": "Jimmy Bigler"},
    )
    assert evt.event_id == "evt_0001"
    assert evt.type == "PASS"
    assert evt.importance == 0.4
    assert evt.facts["passer"] == "William Ruggiero"


def test_timeline_adapter_basic():
    if not GOLDEN_TIMELINE_PATH.exists():
        pytest.skip("Golden timeline not found")

    tl = TimelineAdapter(GOLDEN_TIMELINE_PATH)
    assert tl.total_duration_seconds == 310.7
    assert tl.fps == 10.0
    assert tl.minute_to_pts(1) == 3.0
    assert tl.minute_to_pts(90) == 303.3
    assert tl.event_to_pts("1") == 80.7
    assert tl.event_to_ms("1") == 80700
