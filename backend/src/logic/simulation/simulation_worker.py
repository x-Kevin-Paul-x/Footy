"""
Footy Simulation Worker: Worker Adapter for GRFMatchExecutor.
Consolidates single-match runs and batch/WSL executors into GRFMatchExecutor.
"""

from typing import Dict, Any, Optional, Union
from .match_executor import (
    ReplayMode,
    SimulationSpec,
    SimulationTransition,
    CanonicalMatchResult,
    GRFMatchExecutor,
)


class SimulationWorker(GRFMatchExecutor):
    """
    Worker adapter inheriting from canonical GRFMatchExecutor.
    Maintains 100% backward compatibility for all existing callers and tests.
    """

    def __init__(
        self,
        fixture: Union[SimulationSpec, Dict[str, Any]],
        max_steps: int = 1200,
        replay_mode: ReplayMode = ReplayMode.FULL_STATE
    ):
        super().__init__(fixture, max_steps=max_steps, replay_mode=replay_mode)


__all__ = [
    "ReplayMode",
    "SimulationSpec",
    "SimulationTransition",
    "CanonicalMatchResult",
    "GRFMatchExecutor",
    "SimulationWorker",
]
