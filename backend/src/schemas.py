from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional

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
    match_id: Optional[str] = None
    home_team_name: str = "Arsenal"
    away_team_name: str = "Chelsea"
    home_formation: str = "4-3-3"
    away_formation: str = "4-2-3-1"
    generate_video: bool = False
    max_steps: int = 3000
    record_grf_states: Optional[bool] = None
    record_dump: bool = False
    render_mode: str = "auto"


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

