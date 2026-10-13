"""
Phase 3: Danger & Importance Engine.
Calculates deterministic danger components and composite excitement curves.
Weights are loaded from config.py and all component values are preserved.
"""

from typing import List, Dict, Any, Tuple
import numpy as np

from backend.commentary.schemas import DangerComponents
from backend.commentary.config import (
    DANGER_WEIGHTS,
    PITCH_X_MIN,
    PITCH_X_MAX,
    PENALTY_BOX_X_HOME,
    PENALTY_BOX_X_AWAY,
    PENALTY_BOX_Y_HALF_WIDTH,
)


class DangerEngine:
    """Computes transparent, component-level danger and commentary importance."""

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DANGER_WEIGHTS

    def evaluate_step(
        self,
        step: int,
        ball_coord: np.ndarray,
        ball_dir: np.ndarray,
        team_idx: int,  # 0 = Burnley (attacks x -> -1.0), 1 = Bournemouth (attacks x -> +1.0)
        player_coords: np.ndarray,  # (22, 2)
        xg_val: float = 0.0,
        is_goal: bool = False,
        minute: int = 1,
        score_diff: int = 0,
    ) -> DangerComponents:
        bx, by = float(ball_coord[0]), float(ball_coord[1])
        speed = float(np.linalg.norm(ball_dir[:2])) if ball_dir is not None else 0.0

        if is_goal:
            return DangerComponents(
                field_progression=1.0,
                box_proximity=1.0,
                ball_speed=1.0,
                defenders_bypassed=1.0,
                shot_xg=1.0,
                composite_danger=1.0,
                importance=1.0,
            )

        # 1. Field progression (0.0 to 1.0)
        # Burnley attacks left (x -> -1.0), Bournemouth attacks right (x -> +1.0)
        if team_idx == 0:
            # Burnley attacking
            prog = max(0.0, min(1.0, (1.0 - bx) / 2.0))
        elif team_idx == 1:
            # Bournemouth attacking
            prog = max(0.0, min(1.0, (bx + 1.0) / 2.0))
        else:
            prog = 0.2

        # 2. Box proximity (0.0 to 1.0)
        target_goal_x = -1.0 if team_idx == 0 else 1.0
        dist_to_goal = np.hypot(bx - target_goal_x, by)
        # Closer to goal = higher score (max dist is ~2.0 across pitch)
        box_prox = max(0.0, min(1.0, 1.0 - (dist_to_goal / 1.5)))

        # 3. Ball speed (0.0 to 1.0)
        # typical GRF speeds range 0.0 to ~0.08 per step
        norm_speed = max(0.0, min(1.0, speed / 0.05))

        # 4. Defenders bypassed (0.0 to 1.0)
        defenders_bypassed = 0.0
        if player_coords is not None and team_idx in (0, 1):
            def_start = 11 if team_idx == 0 else 0
            def_end = 22 if team_idx == 0 else 11
            def_xs = player_coords[def_start:def_end, 0]
            if team_idx == 0:
                # Burnley attacking left: defenders behind ball if def_x > bx
                bypassed = np.sum(def_xs > bx)
            else:
                # Bournemouth attacking right: defenders behind ball if def_x < bx
                bypassed = np.sum(def_xs < bx)
            defenders_bypassed = float(bypassed / 10.0)

        # 5. Shot xG (0.0 to 1.0)
        shot_component = min(1.0, xg_val * 3.5) if xg_val > 0 else 0.0

        # Composite danger via configured weights
        w = self.weights
        composite = (
            w.get("field_progression", 0.25) * prog
            + w.get("box_proximity", 0.25) * box_prox
            + w.get("ball_speed", 0.15) * norm_speed
            + w.get("defenders_bypassed", 0.15) * defenders_bypassed
            + w.get("shot_xg", 0.20) * shot_component
        )
        composite = round(max(0.0, min(1.0, float(composite))), 3)

        # Importance calculation (combines danger with match context: close game, late minutes)
        time_factor = 0.5 + 0.5 * (minute / 90.0)  # Later in game = more important
        closeness_factor = 1.0 if abs(score_diff) <= 1 else 0.8
        importance = round(min(1.0, composite * time_factor * closeness_factor), 3)

        return DangerComponents(
            field_progression=round(prog, 3),
            box_proximity=round(box_prox, 3),
            ball_speed=round(norm_speed, 3),
            defenders_bypassed=round(defenders_bypassed, 3),
            shot_xg=round(shot_component, 3),
            composite_danger=composite,
            importance=importance,
        )
