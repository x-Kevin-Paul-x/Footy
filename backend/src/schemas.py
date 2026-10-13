from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional, Literal

class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    budget: float
    weekly_budget: float
    transfer_budget: float
    wage_budget: float

class PlayerRead(BaseModel):
    jersey_number: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    position: str
    team_id: Optional[int] = None
    potential: int
    wage: float
    contract_length: int
    squad_role: str

class SeasonReportSummary(BaseModel):
    id: int
    season: int
    champion: str
    created_at: str

class TransferReportSummary(BaseModel):
    id: int
    season: int
    created_at: str

class SimulationStatusResponse(BaseModel):
    status: str
    message: str
    run_id: Optional[str] = None
    job_id: Optional[str] = None
    status_url: Optional[str] = None


class SimulationSubmission(BaseModel):
    season_year: int = Field(default=2026, ge=2000, le=2200)
    render_mode: Literal['2d', '3d'] = '3d'
    seasons: Optional[int] = Field(default=None, ge=1, le=10)


class EvaluationSubmission(BaseModel):
    models: List[str] = Field(default_factory=lambda: ['dqn_best.pt'], min_length=1, max_length=4)
    episodes: int = Field(default=10, ge=1, le=500)
    teams: int = Field(default=6, ge=4, le=20)
    season_length: int = Field(default=20, ge=1, le=100)
    fast_mode: Literal[True] = True
    seed: int = Field(default=1000, ge=0, le=2**31-1000)
    seeds: Optional[List[int]] = Field(default=None, min_length=1, max_length=500)


class JobResponse(BaseModel):
    job_id: str
    kind: str
    run_id: Optional[str] = None
    status: Literal['queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted']
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    cancel_requested: bool = False
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class SaveStateItem(BaseModel):
    save_id: str
    filename: str
    created_at: str
    size_bytes: int

class SaveStateResponse(BaseModel):
    status: str
    message: str
    save_id: Optional[str] = None

class WebSocketEventFrame(BaseModel):
    schema_version: Literal['1'] = '1'
    sequence: int = 0
    timestamp: Optional[str] = None
    event: str  # e.g., 'MATCH_TICK', 'GOAL_SCORED', 'SEASON_END', 'LOG'
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class MatchSimulationRequest(BaseModel):
    run_id: Optional[str] = Field(default=None, max_length=128, pattern=r'^[A-Za-z0-9_.-]+$')
    match_id: Optional[str] = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    home_team_name: str = Field(default="Arsenal", min_length=1, max_length=100)
    away_team_name: str = Field(default="Chelsea", min_length=1, max_length=100)
    home_formation: str = Field(default="4-3-3", max_length=20)
    away_formation: str = Field(default="4-2-3-1", max_length=20)
    generate_video: bool = False
    max_steps: int = Field(default=3200, ge=100, le=5000)
    record_grf_states: Optional[bool] = None
    record_dump: bool = True
    render_mode: Literal["3d", "2d", "auto"] = "3d"


class MatchSimulationResponse(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    possession: Dict[str, float]
    shots: Dict[str, int]
    xg: Dict[str, float]
    timeline: List[Dict[str, Any]]
    video_url: Optional[str] = None
    render_mode_used: Optional[str] = None
    render_source: Optional[str] = None
    match_complete: Optional[bool] = None
    native_steps_left: Optional[int] = None
    video_status: Optional[str] = None


class SimulationSettings(BaseModel):
    default_render_mode: Literal["3d", "2d"] = "3d"
    max_steps: int = Field(default=3200, ge=100, le=5000)
    active_model: str = Field(default="dqn_best.pt", pattern=r"^[A-Za-z0-9_.-]+\.pt$")


class MatchRenderRequest(BaseModel):
    match_id: Optional[str] = Field(default=None, max_length=128)
    render_mode: Literal["3d", "2d", "auto"] = "auto"
    force: bool = False


class MatchRenderResponse(BaseModel):
    match_id: str
    status: str
    video_url: Optional[str] = None
    render_mode_used: Optional[str] = None
    message: Optional[str] = None
