"""
Unit tests for Danger & Excitement Engine.
"""

import pytest
import numpy as np
from backend.commentary.understanding.danger import DangerEngine


def test_danger_calculation_bounds():
    engine = DangerEngine()
    coords = np.zeros((22, 2))
    ball_pos = np.array([0.0, 0.0, 0.0])
    ball_dir = np.array([0.02, 0.0, 0.0])

    res = engine.evaluate_step(
        step=500,
        ball_coord=ball_pos,
        ball_dir=ball_dir,
        team_idx=1,
        player_coords=coords,
        xg_val=0.15,
        minute=15,
    )
    assert 0.0 <= res.composite_danger <= 1.0
    assert 0.0 <= res.importance <= 1.0
    assert res.field_progression == 0.5
    assert res.shot_xg > 0.0


def test_danger_on_goal():
    engine = DangerEngine()
    res = engine.evaluate_step(
        step=777,
        ball_coord=np.array([1.0, 0.0, 0.0]),
        ball_dir=np.array([0.05, 0.0, 0.0]),
        team_idx=1,
        player_coords=np.zeros((22, 2)),
        is_goal=True,
    )
    assert res.composite_danger == 1.0
    assert res.importance == 1.0


def test_mirrored_archive_preserves_danger():
    coords=np.array([[.1,.2]]*22)
    original=DangerEngine().evaluate_step(10,np.array([.8,.1,0]),np.array([.03,0,0]),0,coords)
    mirrored=DangerEngine(home_attack_sign=-1).evaluate_step(10,np.array([-.8,-.1,0]),np.array([-.03,0,0]),0,-coords)
    assert original == mirrored
    own_half=DangerEngine().evaluate_step(10,np.array([-.8,.1,0]),np.zeros(3),0,coords)
    assert original.field_progression > own_half.field_progression
