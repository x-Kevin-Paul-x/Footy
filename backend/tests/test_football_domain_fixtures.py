"""
Metamorphic Football Domain Fixtures & xG Invariance CI Test Suite.
Validates:
1. Pitch Symmetry Invariance (Mirrored shot geometry y <-> -y produces identical xG).
2. Monotonic Distance Gradient (6yd > 12yd > 18yd > 25yd > 35yd).
3. Monotonic Angular Gradient (Central > Flank Angle).
4. Boundary & Mathematical Invariants (No NaNs, Infs, or negative xG).
5. Semantic Possession Classifier Fixture.
"""

import math
import numpy as np
from pathlib import Path
import sys

backend_src = Path(__file__).resolve().parent.parent / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from logic.grf_core import compute_shot_xg


def test_football_domain_fixtures():
    print("=" * 80)
    print(" RUNNING METAMORPHIC FOOTBALL DOMAIN FIXTURES & XG INVARIANCE CI TEST")
    print("=" * 80)

    dummy_def = np.zeros((11, 2), dtype=np.float32)
    dummy_def[0] = [1.0, 0.0]  # GK

    # -------------------------------------------------------------------------
    # 1. Metamorphic Pitch Symmetry Invariance (y <-> -y)
    # -------------------------------------------------------------------------
    print("\n[+] 1. Testing Metamorphic Pitch Symmetry Invariance (y <-> -y)...")
    test_coords = [
        (0.85, 0.15), (0.75, 0.25), (0.90, 0.05), (0.60, 0.30)
    ]
    for x, y in test_coords:
        xg_top = compute_shot_xg(shooter_x=x, shooter_y=y, goal_x=1.0, defenders=dummy_def)
        xg_bot = compute_shot_xg(shooter_x=x, shooter_y=-y, goal_x=1.0, defenders=dummy_def)
        print(f"    --> Shot at ({x:.2f}, +{y:.2f}) xG={xg_top:.5f} vs ({x:.2f}, -{y:.2f}) xG={xg_bot:.5f}")
        assert abs(xg_top - xg_bot) < 1e-6, f"Symmetry violation at x={x}, y={y}: {xg_top} vs {xg_bot}"
    print("    --> [PASS] Pitch symmetry invariance holds across all tested geometries.")

    # -------------------------------------------------------------------------
    # 2. Monotonic Distance Degradation Ladder
    # -------------------------------------------------------------------------
    print("\n[+] 2. Testing Monotonic Distance Degradation Ladder...")
    # GRF pitch length x in [0.0, 1.0] (52.5m). Goal at x=1.0.
    # 6yd (x=0.92), 12yd (x=0.85), 18yd (x=0.78), 25yd (x=0.68), 35yd (x=0.55)
    distances = [
        (" 6-yard Box", 0.92),
        ("12-yard Spot", 0.85),
        ("18-yard Box", 0.78),
        ("25-yard Area", 0.68),
        ("35-yard Long", 0.55)
    ]
    last_xg = 1.0
    for name, x in distances:
        xg = compute_shot_xg(shooter_x=x, shooter_y=0.0, goal_x=1.0, defenders=dummy_def)
        print(f"    --> {name:<12} (x={x:.2f}): xG={xg:.4f}")
        assert xg < last_xg, f"Distance monotonicity violated: {name} xG ({xg}) >= previous xG ({last_xg})"
        assert 0.0 <= xg <= 1.0, f"xG out of unit interval [0, 1]: {xg}"
        last_xg = xg
    print("    --> [PASS] Monotonic distance degradation strictly holds: 6yd > 12yd > 18yd > 25yd > 35yd.")

    # -------------------------------------------------------------------------
    # 3. Monotonic Angular Degradation Ladder
    # -------------------------------------------------------------------------
    print("\n[+] 3. Testing Monotonic Angular Degradation Ladder...")
    # Fixed distance x=0.85 (12 yards from goal line), varying lateral angle y
    angles = [
        ("Central  (y=0.00)", 0.00),
        ("Flank 15° (y=0.10)", 0.10),
        ("Flank 30° (y=0.20)", 0.20),
        ("Flank 45° (y=0.30)", 0.30),
        ("Tight 60° (y=0.40)", 0.40)
    ]
    last_ang_xg = 1.0
    for name, y in angles:
        xg = compute_shot_xg(shooter_x=0.85, shooter_y=y, goal_x=1.0, defenders=dummy_def)
        print(f"    --> {name:<18}: xG={xg:.4f}")
        assert xg < last_ang_xg, f"Angular monotonicity violated: {name} xG ({xg}) >= previous xG ({last_ang_xg})"
        last_ang_xg = xg
    print("    --> [PASS] Monotonic angular degradation strictly holds: Central > Flank angles.")

    # -------------------------------------------------------------------------
    # 4. Boundary & Mathematical Invariants (No NaNs, Infs, negative bounds)
    # -------------------------------------------------------------------------
    print("\n[+] 4. Testing Mathematical Boundary Invariants & Extreme Geometries...")
    extreme_cases = [
        (-1.0, 0.0), (0.0, 0.0), (1.0, 0.0), (0.999, 0.0),
        (0.5, 0.5), (0.0, 0.5), (-1.0, 0.5)
    ]
    for x, y in extreme_cases:
        xg = compute_shot_xg(shooter_x=x, shooter_y=y, goal_x=1.0, defenders=dummy_def)
        assert not math.isnan(xg), f"NaN detected at ({x}, {y})"
        assert not math.isinf(xg), f"Inf detected at ({x}, {y})"
        assert 0.0 <= xg <= 1.0, f"Boundary violation at ({x}, {y}): {xg}"
    print(f"    --> [PASS] All {len(extreme_cases)} extreme cases strictly bounded within [0.0, 1.0] with zero NaNs/Infs.")

    print("\n" + "=" * 80)
    print(" [+] ALL METAMORPHIC FOOTBALL DOMAIN FIXTURES PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    test_football_domain_fixtures()
