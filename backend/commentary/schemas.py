"""
Typed schemas for Footy AI Broadcast Commentary Pipeline.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class EnrichedEvent(BaseModel):
    """A granular, facts-only football event deterministically extracted from simulation."""
    event_id: str
    type: str  # POSSESSION_START, PASS, CARRY, BOX_ENTRY, SHOT, GOAL, etc.
    step: int
    presentation_ms: int
    match_minute: int
    team: str
    player: str
    position: List[float] = Field(default_factory=list)  # [x, y] or [x, y, z]
    importance: float = 0.0
    danger: float = 0.0
    facts: Dict[str, Any] = Field(default_factory=dict)


class FootballSequence(BaseModel):
    """A narrative sequence grouping continuous possessions or attacks."""
    sequence_id: str
    type: str  # BUILDUP, PROGRESSIVE_ATTACK, COUNTER_ATTACK, DANGEROUS_ATTACK, SHOT_SEQUENCE, GOAL_SEQUENCE
    team: str
    start_step: int
    end_step: int
    start_ms: int
    end_ms: int
    importance: float = 0.0
    danger: float = 0.0
    events: List[str] = Field(default_factory=list)  # Descriptive event strings
    fact_ids: List[str] = Field(default_factory=list)  # Linked event IDs
    outcome: str = "IN_PLAY"  # GOAL, SHOT_SAVED, SHOT_OFF_TARGET, TURNOVER, HALFTIME, FULLTIME
    score_before: str = "0-0"
    score_after: str = "0-0"


class DangerComponents(BaseModel):
    """Raw metric values used to calculate composite danger."""
    field_progression: float = 0.0
    box_proximity: float = 0.0
    ball_speed: float = 0.0
    defenders_bypassed: float = 0.0
    shot_xg: float = 0.0
    composite_danger: float = 0.0
    importance: float = 0.0


class MatchStoryline(BaseModel):
    """Algorithmically derived high-level storyline fact."""
    story_id: str
    title: str
    text: str
    fact_ids: List[str] = Field(default_factory=list)


class MatchContext(BaseModel):
    """The factual ground-truth database provided to LLM Director & Writer."""
    match_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    venue: str = ""
    score_str: str
    xg: List[float] = Field(default_factory=list)
    possession: List[float] = Field(default_factory=list)
    shots: List[int] = Field(default_factory=list)
    shots_on_target: List[int] = Field(default_factory=list)
    home_players: List[str] = Field(default_factory=list)
    away_players: List[str] = Field(default_factory=list)
    storylines: List[MatchStoryline] = Field(default_factory=list)
    allowed_facts: Dict[str, str] = Field(default_factory=dict)  # fact_id -> human-readable factual claim
    event_to_fact_id: Dict[str, str] = Field(default_factory=dict)  # event_id -> fact_id
    fact_available_ms: Dict[str, int] = Field(default_factory=dict)
    evidence_records: List[Dict[str, Any]] = Field(default_factory=list)


class CommentarySlot(BaseModel):
    """A deterministically timed speech candidate window owned by Python."""
    commentary_id: str
    start_ms: int
    max_end_ms: int
    window_seconds: float
    slot_type: Literal[
        "lead_in",
        "shot_call",
        "analysis",
        "goal_reaction",
        "attack",
        "buildup",
        "stoppage",
        "halftime_recap",
        "fulltime_summary",
        "story",
    ]
    sequence_id: Optional[str] = None
    speaker: str = "Ryan"
    priority: int = 1
    active_facts: Dict[str, Any] = Field(default_factory=dict)
    energy_target: float = 0.5  # 0.0 to 1.0
    target_words: int = 15
    match_minute: int = 1
    running_score: str = "0-0"
    score_lead: str = "Level at 0-0"
    active_event_type: Optional[str] = None
    active_team: Optional[str] = None
    active_player: Optional[str] = None
    in_play_summary: str = ""
    allowed_fact_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class CommentaryUtterance(BaseModel):
    """A generated commentary line with multi-length variants and fact citations."""
    commentary_id: str
    speaker: str = "Ryan"
    energy: float = 0.5
    emotion: str = "neutral"
    target_duration_ms: int
    primary: str
    short: str
    emergency_short: str
    used_fact_ids: List[str] = Field(default_factory=list)
    grounding: Optional[Dict[str, Any]] = None


class CommentaryScript(BaseModel):
    """The complete, validated commentary script before LLM is killed."""
    match_id: str
    utterances: List[CommentaryUtterance] = Field(default_factory=list)
    generated_at: str = ""
    model_version: str = "Qwen3.5-9B-Q4_K_M"


class AudioClip(BaseModel):
    """Synthesized speech clip artifact."""
    clip_id: str
    requested_start_ms: int
    max_end_ms: int
    variant_used: Literal["primary", "short", "emergency_short"] = "primary"
    actual_duration_ms: int
    speaker: str = "Ryan"
    slot_type: str = "buildup"
    priority: int = 1
    energy: float = 0.5
    file_path: str
    pts_offset_seconds: float
    atempo_applied: float = 1.0


class AudioManifest(BaseModel):
    """Manifest of all synthesized and resampled audio clips."""
    match_id: str
    clips: List[AudioClip] = Field(default_factory=list)
    total_commentary_duration_seconds: float = 0.0
    master_track_path: str = ""


class TTSCalibration(BaseModel):
    """Empirical speaking-rate calibration per voice."""
    voice: str = "Ryan"
    calm_wps: float = 2.45
    normal_wps: float = 2.75
    excited_wps: float = 3.15
    goal_wps: float = 3.40
    calibrated_at: str = "default_bootstrap"
