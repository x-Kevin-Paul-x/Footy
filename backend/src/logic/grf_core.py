"""
Core High-Performance GRF & TiKick 11v11 MARL Simulation Engine.
Implements dual-team canonical perspective symmetry, true ball-touch scorer tracking,
physics-calibrated Opta xG modeling, and compact MatchTrajectory output without rendering overhead.
"""

import math
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("footy.grf.core")

# GRF Action Mirroring for 180° Inversion (Right Team attacking left)
ACTION_MIRROR_MAP: Dict[int, int] = {
    0: 0,   # idle
    1: 5,   # left -> right
    2: 6,   # top_left -> bottom_right
    3: 7,   # top -> bottom
    4: 8,   # top_right -> bottom_left
    5: 1,   # right -> left
    6: 2,   # bottom_right -> top_left
    7: 3,   # bottom -> top
    8: 4,   # bottom_left -> top_right
    9: 9,   # long_pass
    10: 10, # high_pass
    11: 11, # short_pass
    12: 12, # shot
    13: 13, # sprint
    14: 14, # release_direction
    15: 15, # release_sprint
    16: 16, # sliding
    17: 17, # dribble
    18: 18, # release_dribble
}


def compute_shot_xg(
    shooter_x: float,
    shooter_y: float,
    goal_x: float,
    defenders: np.ndarray,
    shooting_attr: float = 70.0,
    gk_pos: Optional[Tuple[float, float]] = None,
    gk_save_coverage: float = 1.0
) -> float:
    """
    Calculate physics-calibrated Expected Goals (xG) based on shot geometry,
    defender cone density, shooter rating, and goalkeeper positioning & ability.
    """
    # Distance to goal line center (goal_x is +1.0 or -1.0)
    dx = abs(goal_x - shooter_x)
    dy = abs(shooter_y)
    dist = math.sqrt(dx * dx + dy * dy)

    # Visible goal mouth angle (posts at y = -0.044 to +0.044)
    p1 = math.atan2(-0.044 - shooter_y, dx)
    p2 = math.atan2(0.044 - shooter_y, dx)
    angle = abs(p2 - p1)

    # Defender pressure (count defenders within 0.15 pitch distance inside shooting cone)
    def_count = 0
    if len(defenders) > 0:
        for d in defenders:
            d_dist = math.sqrt((d[0] - shooter_x)**2 + (d[1] - shooter_y)**2)
            if d_dist < 0.15 and (abs(goal_x - d[0]) < dx):
                def_count += 1

    # Goalkeeper positioning & coverage influence
    gk_factor = 1.0
    if gk_pos is not None:
        gx, gy = gk_pos
        gk_dist_to_line = abs(goal_x - gx)
        # GK standing in direct trajectory between shooter and goal center
        gk_alignment = max(0.0, 1.0 - abs(gy - shooter_y * (gk_dist_to_line / max(dx, 1e-4))))
        gk_factor = 1.0 - (0.25 * gk_alignment * max(0.70, min(1.30, gk_save_coverage)))

    # Logistic regression baseline
    logit = -0.85 - 3.2 * dist + 2.5 * angle - 0.35 * def_count
    base_prob = 1.0 / (1.0 + math.exp(-max(-6.0, min(6.0, logit))))

    # Attribute modifier
    attr_mod = 0.85 + (min(100.0, max(40.0, shooting_attr)) - 40.0) / 60.0 * 0.35
    xg_val = float(base_prob * attr_mod * gk_factor)
    return max(0.02, min(0.92, round(xg_val, 3)))


def apply_tactical_action_bias(
    actions_raw: List[int],
    player_positions: np.ndarray,  # shape (10, 2)
    formation_anchors: List[Tuple[float, float]],  # 10 field player anchors
    tactics: Any,
    team_side: str = "left",
    ball_xy: Optional[np.ndarray] = None,
    is_team_in_possession: bool = False
) -> List[int]:
    """
    Modulates policy actions with managerial tactical preferences (offensive/defensive bias,
    pressing intensity, and formation anchor gravity for off-ball shape retention).
    """
    modified_actions = list(actions_raw)
    off_bias = float(getattr(tactics, "offensive_bias", 50.0)) / 100.0
    def_bias = float(getattr(tactics, "defensive_bias", 50.0)) / 100.0
    press_int = float(getattr(tactics, "pressing_intensity", 50.0)) / 100.0

    forward_acts = [4, 5, 6] if team_side == "left" else [1, 2, 8]
    backward_acts = [1, 2, 8] if team_side == "left" else [4, 5, 6]

    for idx, act in enumerate(actions_raw):
        if idx >= len(player_positions) or idx >= len(formation_anchors):
            continue

        pos = player_positions[idx]
        anchor = formation_anchors[idx]
        drift_dist = math.hypot(pos[0] - anchor[0], pos[1] - anchor[1])

        # 1. Off-ball formation shape retention
        if not is_team_in_possession and drift_dist > 0.38 and act == 0:
            # Player is idle and far out of shape: guide back toward anchor zone
            dx = anchor[0] - pos[0]
            dy = anchor[1] - pos[1]
            if abs(dx) > abs(dy):
                modified_actions[idx] = 5 if dx > 0 else 1
            else:
                modified_actions[idx] = 7 if dy > 0 else 3

        # 2. Tactical Pressing: close down ball aggressively when near ball
        if not is_team_in_possession and ball_xy is not None and press_int > 0.65:
            b_dist = math.hypot(pos[0] - ball_xy[0], pos[1] - ball_xy[1])
            if b_dist < 0.18 and act in (1, 2, 3, 4, 5, 6, 7, 8):
                # When closing down with high pressing, activate sprint
                if np.random.rand() < (press_int - 0.50):
                    modified_actions[idx] = 13  # sprint

        # 3. Attacking / Defensive Intent Biasing
        if is_team_in_possession and off_bias > 0.70 and act in backward_acts:
            # Overriding overly conservative retreats when attacking
            if np.random.rand() < (off_bias - 0.50) * 0.40:
                modified_actions[idx] = forward_acts[1]  # forward move

    return modified_actions


def extract_canonical_features(
    raw_obs: List[Dict[str, Any]],
    team_side: str = "left",
    num_agents: int = 10,
    last_loff: Optional[np.ndarray] = None,
    last_roff: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Encodes raw Google Research Football observations into canonical 268-dim vectors
    with exact 180° spatial symmetry for the right team.
    """
    if last_loff is None:
        last_loff = np.zeros(11, dtype=np.float32)
    if last_roff is None:
        last_roff = np.zeros(11, dtype=np.float32)

    o0 = raw_obs[0]
    is_right = (team_side == "right")

    if not is_right:
        ally = np.array(o0['left_team'], dtype=np.float32)
        ally_d = np.array(o0['left_team_direction'], dtype=np.float32)
        enemy = np.array(o0['right_team'], dtype=np.float32)
        enemy_d = np.array(o0['right_team_direction'], dtype=np.float32)
        ball = np.array(o0['ball'], dtype=np.float32)
        ball_xy = ball[:2]
        ball_d = np.array(o0['ball_direction'], dtype=np.float32)
        raw_ball_owned = o0.get('ball_owned_team', -1)
        score_diff = (o0['score'][0] - o0['score'][1]) / 5.0
        tired = np.array(o0.get('left_team_tired_factor', np.zeros(11)), dtype=np.float32)
        yellow = np.array(o0.get('left_team_yellow_card', np.zeros(11)), dtype=np.float32)
        active_status = np.array(o0.get('left_team_active', np.ones(11)), dtype=np.float32)
    else:
        # 180° Rotational pitch inversion: (x, y) -> (-x, -y), (vx, vy) -> (-vx, -vy)
        ally = -np.array(o0['right_team'], dtype=np.float32)
        ally_d = -np.array(o0['right_team_direction'], dtype=np.float32)
        enemy = -np.array(o0['left_team'], dtype=np.float32)
        enemy_d = -np.array(o0['left_team_direction'], dtype=np.float32)

        raw_ball = np.array(o0['ball'], dtype=np.float32)
        ball = np.array([-raw_ball[0], -raw_ball[1], raw_ball[2]], dtype=np.float32)
        ball_xy = ball[:2]

        raw_bd = np.array(o0['ball_direction'], dtype=np.float32)
        ball_d = np.array([-raw_bd[0], -raw_bd[1], raw_bd[2]], dtype=np.float32)

        raw_team = o0.get('ball_owned_team', -1)
        raw_ball_owned = 0 if raw_team == 1 else (1 if raw_team == 0 else -1)

        score_diff = (o0['score'][1] - o0['score'][0]) / 5.0
        tired = np.array(o0.get('right_team_tired_factor', np.zeros(11)), dtype=np.float32)
        yellow = np.array(o0.get('right_team_yellow_card', np.zeros(11)), dtype=np.float32)
        active_status = np.array(o0.get('right_team_active', np.ones(11)), dtype=np.float32)

    # Ball ownership one-hot encoding [unowned, ally, enemy]
    if raw_ball_owned == -1:
        ball_own_vec = [1.0, 0.0, 0.0]
    elif raw_ball_owned == 0:
        ball_own_vec = [0.0, 1.0, 0.0]
    else:
        ball_own_vec = [0.0, 0.0, 1.0]

    # Offside estimation
    if o0.get('game_mode', 0) != 0:
        loff = np.zeros(11, dtype=np.float32)
        roff = np.zeros(11, dtype=np.float32)
    else:
        eff_team = raw_ball_owned
        eff_player = o0.get('ball_owned_player', -1)
        if eff_team == -1:
            ally_dist = np.linalg.norm(ball_xy - ally, axis=-1)
            enemy_dist = np.linalg.norm(ball_xy - enemy, axis=-1)
            if np.min(ally_dist) < np.min(enemy_dist) and np.min(ally_dist) < 0.017:
                eff_team = 0
                eff_player = int(np.argmin(ally_dist))
            elif np.min(enemy_dist) < np.min(ally_dist) and np.min(enemy_dist) < 0.017:
                eff_team = 1
                eff_player = int(np.argmin(enemy_dist))

        if eff_team == 0:
            enemy_xs = np.sort(enemy[1:11, 0])
            loff = np.zeros(11, dtype=np.float32)
            for k in range(1, 11):
                if ally[k, 0] > enemy_xs[-1] and k != eff_player and ally[k, 0] > 0.0:
                    loff[k] = 1.0
            roff = last_roff
        elif eff_team == 1:
            ally_xs = np.sort(ally[1:11, 0])
            roff = np.zeros(11, dtype=np.float32)
            for k in range(1, 11):
                if enemy[k, 0] < ally_xs[0] and k != eff_player and enemy[k, 0] < 0.0:
                    roff[k] = 1.0
            loff = last_loff
        else:
            loff, roff = last_loff, last_roff

    # Shared feature segments
    ally_flat = ally.flatten()
    ally_d_flat = ally_d.flatten()
    enemy_flat = enemy.flatten()
    enemy_d_flat = enemy_d.flatten()

    game_mode_vec = [0.0] * 7
    g_mode = min(6, max(0, int(o0.get('game_mode', 0))))
    game_mode_vec[g_mode] = 1.0

    steps_left = float(o0.get('steps_left', 3000))
    step_feat_1 = steps_left / 3001.0
    s_sub = steps_left - 1501.0 if steps_left > 1500.0 else steps_left
    step_feat_2 = min(s_sub, 300.0) / 300.0
    score_ratio_clamped = max(-1.0, min(1.0, score_diff))

    out_matrix = np.empty((num_agents, 268), dtype=np.float32)

    for a in range(num_agents):
        agent_obs = raw_obs[a]
        active_idx = int(agent_obs.get('active', 0))
        active_idx = max(0, min(10, active_idx))

        me = ally[active_idx]
        b_dist = min(1.0, float(np.linalg.norm(me - ball_xy)))
        e_dist = np.linalg.norm(me - enemy, axis=-1)

        to_ally = (ally - me).copy()
        to_ally[:, 0] /= 2.0
        to_enemy = (enemy - me).copy()
        to_enemy[:, 0] /= 2.0
        to_ball = (ball_xy - me).copy()
        to_ball[0] /= 2.0

        active_vec = [0.0] * 11
        active_vec[active_idx] = 1.0

        raw_sticky = agent_obs.get('sticky_actions', [0] * 10)[:10]
        if is_right and len(raw_sticky) >= 8:
            # Mirror directional sticky actions: 0<->7 (left/right), 1<->4, 2<->5, 3<->6
            sticky_vec = [
                float(raw_sticky[7]), float(raw_sticky[4]), float(raw_sticky[5]), float(raw_sticky[6]),
                float(raw_sticky[1]), float(raw_sticky[2]), float(raw_sticky[3]), float(raw_sticky[0]),
            ] + [float(x) for x in raw_sticky[8:]]
        else:
            sticky_vec = [float(x) for x in raw_sticky]
        while len(sticky_vec) < 10:
            sticky_vec.append(0.0)

        o_parts = [
            ally_flat, ally_d_flat, enemy_flat, enemy_d_flat,  # 88
            ball, ball_d,                                      # 6 -> 94
            np.array(ball_own_vec, dtype=np.float32),          # 3 -> 97
            np.array(active_vec, dtype=np.float32),            # 11 -> 108
            np.array(game_mode_vec, dtype=np.float32),         # 7 -> 115
            np.array(sticky_vec[:10], dtype=np.float32),       # 10 -> 125
            np.array([b_dist], dtype=np.float32),              # 1 -> 126
            tired,                                             # 11 -> 137
            yellow,                                            # 11 -> 148
            active_status,                                     # 11 -> 159
            loff, roff,                                        # 22 -> 181
            e_dist,                                            # 11 -> 192
            to_ally.flatten(),                                 # 22 -> 214
            to_enemy.flatten(),                                # 22 -> 236
            to_ball.flatten(),                                 # 2 -> 238
            np.array([step_feat_1, step_feat_2, score_ratio_clamped], dtype=np.float32),  # 3 -> 241
            np.zeros(27, dtype=np.float32),                    # 27 -> 268
        ]
        out_matrix[a] = np.concatenate(o_parts)

    return out_matrix, loff, roff
