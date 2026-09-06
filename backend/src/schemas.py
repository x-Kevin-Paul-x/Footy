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
    event: str  # e.g., 'MATCH_TICK', 'GOAL_SCORED', 'SEASON_END', 'LOG'
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class MatchSimulationRequest(BaseModel):
    match_id: Optional[str] = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    home_team_name: str = Field(default="Arsenal", min_length=1, max_length=100)
    away_team_name: str = Field(default="Chelsea", min_length=1, max_length=100)
    home_formation: str = Field(default="4-3-3", max_length=20)
    away_formation: str = Field(default="4-2-3-1", max_length=20)
    generate_video: bool = False
    max_steps: int = Field(default=1200, ge=100, le=5000)
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


class SimulationSettings(BaseModel):
    default_render_mode: Literal["3d", "2d"] = "3d"
    max_steps: int = Field(default=1200, ge=100, le=5000)
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
