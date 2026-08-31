"""
Canonical GRF & TiKick Match Engine Interface for Footy.
Integrates Footy squad attributes, managerial tactics, and formations
with physics-accurate 3D Multi-Agent Reinforcement Learning simulation.
"""

import logging
from typing import Any, Dict, List, Optional
from config import FOOTY_GRF_MAX_STEPS
from logic.footy_grf_adapter import FootyGRFAdapter, FORMATION_COORDINATES, GRFTeamTactics
from logic.grf_native_runner import GRFNativeRunner

logger = logging.getLogger("footy.engine.grf")


class FootyMatchSimulator:
    """
    High-fidelity Match Simulation Engine using Google Research Football & TiKick 11v11 MARL.
    Acts as the canonical bridge between Footy domain objects and the native GRF runner.
    """

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.runner = GRFNativeRunner()

    def is_available(self) -> bool:
        """Check if GRF environment and TiKick weights are ready in WSL."""
        return self.runner.is_available()

    def simulate(
        self,
        home_team: Any,
        away_team: Any,
        max_steps: int = FOOTY_GRF_MAX_STEPS,
        render_video: bool = False,
        match_id: Optional[str] = None,
        home_formation: Optional[str] = None,
        away_formation: Optional[str] = None,
        home_lineup: Optional[List[Any]] = None,
        away_lineup: Optional[List[Any]] = None,
        seed_val: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute full 11v11 match simulation.
        Translates Footy team/player attributes and formations into simulation parameters.
        """
        h_tactics = FootyGRFAdapter.build_team_tactics(
            home_team, lineup=home_lineup, formation=home_formation
        )
        a_tactics = FootyGRFAdapter.build_team_tactics(
            away_team, lineup=away_lineup, formation=away_formation
        )

        h_players = [p.name for p in h_tactics.roster]
        a_players = [p.name for p in a_tactics.roster]

        return self.runner.simulate(
            home_team=h_tactics.team_name,
            away_team=a_tactics.team_name,
            max_steps=max_steps,
            home_players=h_players,
            away_players=a_players,
            home_formation=h_tactics.formation,
            away_formation=a_tactics.formation,
            match_id=match_id,
            seed_val=seed_val,
            render_video=render_video,
        )
