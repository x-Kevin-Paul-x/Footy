"""
Native Google Research Football (GRF) 3D Simulation & Cinematic Broadcast Video Replay Bridge.
Executes authentic 11v11 MARL physics matches with Dual TiKick Actor Policies (Self-Play) via WSL2.
Renders extended 75-90s TV broadcast highlight videos with pre-match intros, slow-mo goal replays,
and half-time/full-time tactical studio boards.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from config import (
    RECORDINGS_DIR,
    TIKICK_CHECKPOINT_PATH,
    LOCAL_TIKICK_DIR,
    FOOTY_GRF_MAX_STEPS
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour helpers (deterministic kit colour palette)
# ---------------------------------------------------------------------------

_KIT_PALETTE = [
    "#e63946", "#2196f3", "#4caf50", "#ff9800", "#9c27b0",
    "#00bcd4", "#f44336", "#3f51b5", "#8bc34a", "#ff5722",
    "#009688", "#673ab7", "#ffc107", "#607d8b", "#e91e63",
]

def team_color_from_name(name: str) -> str:
    """Deterministic kit colour derived from team name (no DB migration needed)."""
    idx = int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % len(_KIT_PALETTE)
    return _KIT_PALETTE[idx]


# ---------------------------------------------------------------------------
# WSL script — runs inside the WSL Linux environment
# ---------------------------------------------------------------------------

WSL_GRF_SCRIPT = r"""
import os, sys, json, hashlib, time
import numpy as np
import torch
import cv2
import imageio

# Ensure TiKick import path
tikick_path = "{tikick_dir}"
if tikick_path not in sys.path:
    sys.path.insert(0, tikick_path)

import gfootball.env as football_env
from tmarl.networks.policy_network import PolicyNetwork
import gym


# ── model config ────────────────────────────────────────────────────────────
class TiKickModelConfig:
    hidden_size = 256
    gain = 0.01
    use_orthogonal = False
    activation_id = 1
    use_policy_active_masks = False
    use_naive_recurrent_policy = False
    use_recurrent_policy = True
    use_influence_policy = False
    influence_layer_N = 1
    use_policy_vhead = False
    recurrent_N = 1
    use_feature_normalization = True
    use_conv1d = False
    stacked_frames = 1
    layer_N = 3


def load_tikick(ckpt_path, device='cuda' if torch.cuda.is_available() else 'cpu'):
    obs_space = gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32')
    action_space = gym.spaces.Discrete(33)
    policy = PolicyNetwork(TiKickModelConfig(), obs_space, action_space, device=torch.device(device))
    state_dict = torch.load(ckpt_path, map_location=device)
    policy.load_state_dict(state_dict)
    policy.eval()
    return policy


# ── observation encoder ──────────────────────────────────────────────────────
def extract_features_268(raw_obs, num_agents=10, last_loffside=None, last_roffside=None):
    if last_loffside is None: last_loffside = np.zeros(11, dtype=np.float32)
    if last_roffside is None: last_roffside = np.zeros(11, dtype=np.float32)

    ally   = np.array(raw_obs[0]['left_team'])
    ally_d = np.array(raw_obs[0]['left_team_direction'])
    enemy  = np.array(raw_obs[0]['right_team'])
    enemy_d= np.array(raw_obs[0]['right_team_direction'])
    ball   = np.array(raw_obs[0]['ball'][:2])

    if raw_obs[0]['game_mode'] != 0:
        loffside = np.zeros(11, dtype=np.float32)
        roffside = np.zeros(11, dtype=np.float32)
    else:
        effective_ownball_team   = raw_obs[0]['ball_owned_team']
        effective_ownball_player = raw_obs[0]['ball_owned_player']
        if effective_ownball_team == -1:
            ally_dist  = np.linalg.norm(ball - ally,  axis=-1)
            enemy_dist = np.linalg.norm(ball - enemy, axis=-1)
            if np.min(ally_dist) < np.min(enemy_dist) and np.min(ally_dist) < 0.017:
                effective_ownball_team   = 0
                effective_ownball_player = np.argmin(ally_dist)
            elif np.min(enemy_dist) < np.min(ally_dist) and np.min(enemy_dist) < 0.017:
                effective_ownball_team   = 1
                effective_ownball_player = np.argmin(enemy_dist)

        if effective_ownball_team == 0:
            right_xs = np.sort([raw_obs[0]['right_team'][k][0] for k in range(1, 11)])
            loffside = np.zeros(11, dtype=np.float32)
            for k in range(1, 11):
                if raw_obs[0]['left_team'][k][0] > right_xs[-1] and k != effective_ownball_player and raw_obs[0]['left_team'][k][0] > 0.0:
                    loffside[k] = 1.0
            roffside = last_roffside
        elif effective_ownball_team == 1:
            left_xs = np.sort([raw_obs[0]['left_team'][k][0] for k in range(1, 11)])
            roffside = np.zeros(11, dtype=np.float32)
            for k in range(1, 11):
                if raw_obs[0]['right_team'][k][0] < left_xs[0] and k != effective_ownball_player and raw_obs[0]['right_team'][k][0] < 0.0:
                    roffside[k] = 1.0
            loffside = last_loffside
        else:
            loffside, roffside = last_loffside, last_roffside

    obs = []
    for a in range(num_agents):
        me       = ally[int(raw_obs[a]['active'])]
        ball_xy  = raw_obs[a]['ball'][:2]
        ball_dist= min(1.0, float(np.linalg.norm(me - ball_xy)))
        enemy_dist= np.linalg.norm(me - enemy, axis=-1)
        to_enemy = (enemy - me).copy()
        to_ally  = (ally  - me).copy()
        to_ball  = (ball_xy - me).copy()

        o = []
        o.extend(ally.flatten());  o.extend(ally_d.flatten())
        o.extend(enemy.flatten()); o.extend(enemy_d.flatten())
        o.extend(raw_obs[a]['ball']); o.extend(raw_obs[a]['ball_direction'])

        owned = raw_obs[a]['ball_owned_team']
        o.extend([1,0,0] if owned == -1 else ([0,1,0] if owned == 0 else [0,0,1]))

        active = [0]*11; active[raw_obs[a]['active']] = 1; o.extend(active)
        game_mode = [0]*7; game_mode[raw_obs[a]['game_mode']] = 1; o.extend(game_mode)

        o.extend(raw_obs[a]['sticky_actions'][:10])
        o.append(ball_dist)
        o.extend(raw_obs[a]['left_team_tired_factor'])
        o.extend(raw_obs[a]['left_team_yellow_card'])
        o.extend(raw_obs[a]['left_team_active'])
        o.extend(loffside); o.extend(roffside); o.extend(enemy_dist)

        to_ally[:,0] /= 2.0;  o.extend(to_ally.flatten())
        to_enemy[:,0] /= 2.0; o.extend(to_enemy.flatten())
        to_ball[0] /= 2.0;    o.extend(to_ball.flatten())

        steps_left = raw_obs[a]['steps_left']
        o.append(float(steps_left) / 3001.0)
        if steps_left > 1500:
            steps_left -= 1501
        o.append(min(float(steps_left), 300.0) / 300.0)

        score_ratio = (raw_obs[a]['score'][0] - raw_obs[a]['score'][1]) / 5.0
        score_ratio = max(-1.0, min(1.0, score_ratio))
        o.append(score_ratio)
        o.extend([0.0] * 27)
        obs.append(o)

    return np.array(obs, dtype=np.float32), loffside, roffside


# ── Colour & Team Helpers ───────────────────────────────────────────────────
_KIT_PALETTE = [
    "#e63946","#2196f3","#4caf50","#ff9800","#9c27b0",
    "#00bcd4","#f44336","#3f51b5","#8bc34a","#ff5722",
    "#009688","#673ab7","#ffc107","#607d8b","#e91e63",
]

def team_color_from_name(name):
    idx = int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % len(_KIT_PALETTE)
    return _KIT_PALETTE[idx]

def team_abbr(name):
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][:2]).upper()
    return name[:3].upper()

def hex_to_bgr(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)

def text_color_for_bg(bgr):
    b, g, r = bgr
    lum = 0.299*r + 0.587*g + 0.114*b
    return (255,255,255) if lum < 140 else (15,15,15)


# ── Cinematic Studio Broadcast Overlays ──────────────────────────────────────
def draw_hud(frame, home_team, away_team, score, match_min, step, max_steps,
             home_bgr, away_bgr, goal_banner, is_second_half):
    annotated = frame.copy()
    h_img, w_img = annotated.shape[:2]

    # Floating Modern Top-Left TV Pill HUD (Premier League / UCL style)
    px, py = 32, 24
    pw, ph = 370, 38

    overlay = annotated.copy()
    cv2.rectangle(overlay, (px, py), (px + pw, py + ph), (14, 18, 26), -1)
    cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)
    cv2.rectangle(annotated, (px, py), (px + pw, py + ph), (55, 68, 85), 1)

    # Home Team Pill
    h_abbr = team_abbr(home_team)
    cv2.rectangle(annotated, (px + 2, py + 2), (px + 62, py + ph - 2), home_bgr, -1)
    htc = text_color_for_bg(home_bgr)
    cv2.putText(annotated, h_abbr, (px + 10, py + 26), cv2.FONT_HERSHEY_DUPLEX, 0.62, htc, 2, cv2.LINE_AA)

    # Score
    cv2.putText(annotated, str(score[0]), (px + 76, py + 28), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated, "-", (px + 100, py + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 175, 195), 1, cv2.LINE_AA)
    cv2.putText(annotated, str(score[1]), (px + 120, py + 28), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

    # Away Team Pill
    a_abbr = team_abbr(away_team)
    cv2.rectangle(annotated, (px + 144, py + 2), (px + 204, py + ph - 2), away_bgr, -1)
    atc = text_color_for_bg(away_bgr)
    cv2.putText(annotated, a_abbr, (px + 152, py + 26), cv2.FONT_HERSHEY_DUPLEX, 0.62, atc, 2, cv2.LINE_AA)

    # Clock & Half Indicator
    half_tag = "2ND" if is_second_half else "1ST"
    clock_str = f"{half_tag}  {match_min:02d}:00"
    cv2.rectangle(annotated, (px + 208, py + 2), (px + pw - 2, py + ph - 2), (24, 30, 42), -1)
    cv2.putText(annotated, clock_str, (px + 222, py + 26), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 220, 255), 1, cv2.LINE_AA)

    # Floating Goal Celebration Banner
    if goal_banner:
        bx1, bx2 = w_img // 2 - 280, w_img // 2 + 280
        by1, by2 = h_img - 78, h_img - 24

        gov = annotated.copy()
        cv2.rectangle(gov, (bx1, by1), (bx2, by2), (10, 15, 24), -1)
        cv2.addWeighted(gov, 0.88, annotated, 0.12, 0, annotated)

        cv2.rectangle(annotated, (bx1, by1), (bx1 + 8, by2), (0, 215, 255), -1)
        cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (0, 215, 255), 2)
        cv2.putText(annotated, goal_banner, (bx1 + 24, by1 + 37), cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)

    return annotated


def draw_player_tag(frame, sx, sy, player_name, team_bgr):
    h, w = frame.shape[:2]
    if not (20 < sx < w - 80 and 30 < sy < h - 40):
        return

    tag_text = player_name.split('(')[0].strip()
    (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_DUPLEX, 0.45, 1)

    bx1 = sx - tw // 2 - 8
    bx2 = sx + tw // 2 + 8
    by1 = sy - th - 12
    by2 = sy

    overlay = frame.copy()
    cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (15, 18, 26), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (60, 70, 85), 1)
    cv2.rectangle(frame, (bx1, by1), (bx1 + 4, by2), team_bgr, -1)
    cv2.putText(frame, tag_text, (bx1 + 8, by2 - 4), cv2.FONT_HERSHEY_DUPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    pts = np.array([[sx - 4, by2], [sx + 4, by2], [sx, by2 + 5]], np.int32)
    cv2.fillPoly(frame, [pts], (240, 240, 240))


def draw_replay_frame(raw_frame, home_team, away_team, score, match_min, step, total_steps,
                      home_bgr, away_bgr, is_second_half, zoom_factor=1.35):
    # Crops and zooms into the goal area with a TV replay watermark badge
    h, w = raw_frame.shape[:2]
    new_w, new_h = int(w / zoom_factor), int(h / zoom_factor)
    x1 = (w - new_w) // 2
    y1 = (h - new_h) // 2
    cropped = raw_frame[y1:y1+new_h, x1:x1+new_w]
    zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    # Draw regular scoreboard HUD on zoomed view
    annotated = draw_hud(zoomed, home_team, away_team, score, match_min, step, total_steps,
                         home_bgr, away_bgr, None, is_second_half)

    # Replay Watermark Badge (Top-Right)
    rx, ry = w - 210, 24
    rw, rh = 180, 36
    overlay = annotated.copy()
    cv2.rectangle(overlay, (rx, ry), (rx + rw, ry + rh), (15, 20, 30), -1)
    cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)
    cv2.rectangle(annotated, (rx, ry), (rx + rw, ry + rh), (220, 50, 50), 2)

    # Red REC dot + REPLAY text
    cv2.circle(annotated, (rx + 20, ry + 18), 6, (0, 0, 255), -1)
    cv2.putText(annotated, f"REPLAY  {match_min}'", (rx + 35, ry + 25), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    return annotated


def draw_pre_match_card(w=1280, h=720, home_team="", away_team="",
                        home_players=None, away_players=None,
                        home_formation="4-3-3", away_formation="4-2-3-1",
                        home_bgr=(50,50,220), away_bgr=(220,50,50)):
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (18, 22, 32)

    # Top Broadcast Title Banner
    cv2.rectangle(canvas, (0, 0), (w, 80), (10, 14, 22), -1)
    cv2.putText(canvas, "PREMIER LEAGUE  *  MATCHDAY BROADCAST",
                (w//2 - 280, 50), cv2.FONT_HERSHEY_DUPLEX, 0.78, (0, 220, 255), 2, cv2.LINE_AA)

    # Team Headers with Formation Badges
    cv2.rectangle(canvas, (50, 105), (w//2 - 25, 175), home_bgr, -1)
    cv2.rectangle(canvas, (w//2 + 25, 105), (w - 50, 175), away_bgr, -1)

    htc = text_color_for_bg(home_bgr)
    atc = text_color_for_bg(away_bgr)

    cv2.putText(canvas, home_team.upper(), (70, 152), cv2.FONT_HERSHEY_DUPLEX, 0.85, htc, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"[{home_formation}]", (w//2 - 130, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.58, htc, 2, cv2.LINE_AA)

    cv2.putText(canvas, away_team.upper(), (w//2 + 45, 152), cv2.FONT_HERSHEY_DUPLEX, 0.85, atc, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"[{away_formation}]", (w - 150, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.58, atc, 2, cv2.LINE_AA)

    # Lineups Columns
    cv2.putText(canvas, "STARTING XI", (70, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 220, 255), 2)
    cv2.putText(canvas, "STARTING XI", (w//2 + 45, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 220, 255), 2)

    hp = home_players[:11] if home_players else [f"{home_team} Player {i+1}" for i in range(11)]
    ap = away_players[:11] if away_players else [f"{away_team} Player {i+1}" for i in range(11)]

    for idx, p in enumerate(hp):
        y = 255 + idx * 36
        num_str = f"{idx+1}." if idx > 0 else "1 (GK)"
        cv2.putText(canvas, f"{num_str:6s} {p}", (70, y), cv2.FONT_HERSHEY_DUPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)

    for idx, p in enumerate(ap):
        y = 255 + idx * 36
        num_str = f"{idx+1}." if idx > 0 else "1 (GK)"
        cv2.putText(canvas, f"{num_str:6s} {p}", (w//2 + 45, y), cv2.FONT_HERSHEY_DUPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)

    return canvas


def draw_studio_stats_card(w=1280, h=720, title="HALF TIME", home_team="", away_team="",
                           score=(0,0), h_poss=50.0, a_poss=50.0, h_shots=0, a_shots=0,
                           home_bgr=(50,50,220), away_bgr=(220,50,50), events=None,
                           motm_player=None):
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (16, 20, 28)

    # Header
    cv2.rectangle(canvas, (0, 0), (w, 80), (10, 14, 20), -1)
    cv2.putText(canvas, title, (w//2 - 90, 52), cv2.FONT_HERSHEY_DUPLEX, 0.88, (0, 220, 255), 2, cv2.LINE_AA)

    # Team Panels
    cv2.rectangle(canvas, (80, 105), (w//2 - 80, 185), home_bgr, -1)
    cv2.rectangle(canvas, (w//2 + 80, 105), (w - 80, 185), away_bgr, -1)
    cv2.rectangle(canvas, (w//2 - 75, 105), (w//2 + 75, 185), (10, 14, 20), -1)

    htc = text_color_for_bg(home_bgr)
    atc = text_color_for_bg(away_bgr)

    cv2.putText(canvas, home_team.upper(), (100, 156), cv2.FONT_HERSHEY_DUPLEX, 0.85, htc, 2, cv2.LINE_AA)
    cv2.putText(canvas, away_team.upper(), (w//2 + 100, 156), cv2.FONT_HERSHEY_DUPLEX, 0.85, atc, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"{score[0]} - {score[1]}", (w//2 - 50, 160), cv2.FONT_HERSHEY_DUPLEX, 1.05, (255, 255, 255), 2, cv2.LINE_AA)

    # Stats Table
    stat_rows = [
        ("Possession", f"{h_poss:.1f}%", f"{a_poss:.1f}%"),
        ("Total Shots", str(h_shots), str(a_shots)),
        ("Shots on Target", str(max(score[0], h_shots // 2)), str(max(score[1], a_shots // 2))),
        ("Expected Goals (xG)", f"{score[0]*0.75:.2f}", f"{score[1]*0.75:.2f}")
    ]

    for idx, (label, val_l, val_r) in enumerate(stat_rows):
        y = 250 + idx * 52
        cv2.rectangle(canvas, (80, y - 32), (w - 80, y + 14), (24, 30, 42), -1)
        cv2.putText(canvas, val_l, (120, y), cv2.FONT_HERSHEY_DUPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, label, (w//2 - 90, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (180, 200, 220), 2, cv2.LINE_AA)
        cv2.putText(canvas, val_r, (w - 180, y), cv2.FONT_HERSHEY_DUPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)

    # Goals Timeline
    if events:
        goals = [e for e in events if e.get("type") == "goal"]
        if goals:
            cv2.putText(canvas, "MATCH TIMELINE", (80, 490), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (16, 185, 129), 2)
            for idx, g in enumerate(goals[:3]):
                gy = 525 + idx * 30
                cv2.putText(canvas, f"{g.get('minute')}' - {g.get('player')} ({g.get('team', '').upper()})",
                            (80, gy), cv2.FONT_HERSHEY_DUPLEX, 0.58, (240, 240, 240), 1, cv2.LINE_AA)

    # Man of the Match (Full Time Only)
    if motm_player and title == "FULL TIME":
        mx, my = w//2 + 40, 480
        cv2.rectangle(canvas, (mx, my), (w - 80, my + 130), (28, 35, 50), -1)
        cv2.rectangle(canvas, (mx, my), (w - 80, my + 130), (0, 215, 255), 2)
        cv2.putText(canvas, "MAN OF THE MATCH", (mx + 20, my + 38), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, motm_player, (mx + 20, my + 82), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)

    return canvas


# ── Shared Env Factory ───────────────────────────────────────────────────────
def make_env(seed_val, render):
    extra = {'action_set': 'full', 'random_seed': seed_val}
    return football_env.create_environment(
        env_name="11_vs_11_kaggle",
        stacked=False,
        representation='raw',
        rewards='scoring',
        write_goal_dumps=False,
        write_full_episode_dumps=False,
        logdir='/tmp/grf_dumps',
        render=render,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10,
        other_config_options=extra,
    )


TEAM_ROSTERS = {
    'arsenal': ['Raya (GK)', 'White', 'Saliba', 'Gabriel', 'Timber', 'Rice', 'Partey', 'Odegaard', 'Saka', 'Havertz', 'Martinelli'],
    'aston villa': ['Martinez (GK)', 'Cash', 'Konsa', 'Torres', 'Digne', 'Onana', 'Tielemans', 'McGinn', 'Bailey', 'Watkins', 'Rogers'],
    'chelsea': ['Sanchez (GK)', 'James', 'Fofana', 'Colwill', 'Cucurella', 'Caicedo', 'Fernandez', 'Palmer', 'Madueke', 'Jackson', 'Neto'],
    'manchester city': ['Ederson (GK)', 'Walker', 'Dias', 'Akanji', 'Gvardiol', 'Rodri', 'Kovacic', 'De Bruyne', 'Foden', 'Haaland', 'Doku'],
    'liverpool': ['Alisson (GK)', 'Alexander-Arnold', 'Konate', 'Van Dijk', 'Robertson', 'Gravenberch', 'Mac Allister', 'Szoboszlai', 'Salah', 'Nunez', 'Diaz'],
    'manchester united': ['Onana (GK)', 'Dalot', 'De Ligt', 'Martinez', 'Mazraoui', 'Mainoo', 'Casemiro', 'Fernandes', 'Garnacho', 'Hojlund', 'Rashford'],
    'tottenham': ['Vicario (GK)', 'Porro', 'Romero', 'Van de Ven', 'Udogie', 'Sarr', 'Bentancur', 'Maddison', 'Kulusevski', 'Solanke', 'Son'],
    'newcastle': ['Pope (GK)', 'Livramento', 'Schar', 'Burn', 'Hall', 'Guimaraes', 'Tonali', 'Joelinton', 'Murphy', 'Isak', 'Gordon'],
}

def default_roster(team_name, players, is_home):
    if players and len(players) >= 11:
        return list(players)
    tl = team_name.lower().strip()
    for k, v in TEAM_ROSTERS.items():
        if k in tl or tl in k:
            return list(v)
    return (
        [f"{team_name} GK"] +
        [f"{team_name} Defender {i}" for i in range(1, 5)] +
        [f"{team_name} Midfielder {i}" for i in range(1, 5)] +
        [f"{team_name} Forward {i}" for i in range(1, 3)]
    )


def open_writer(output_mp4, fps=15):
    os.makedirs(os.path.dirname(output_mp4) or '.', exist_ok=True)
    return imageio.get_writer(output_mp4, fps=fps, codec='libx264',
                               pixelformat='yuv420p', quality=8)


# ─────────────────────────────────────────────────────────────────────────────
# Direct Live TiKick Simulation & 3D Broadcast Rendering
# ─────────────────────────────────────────────────────────────────────────────
def simulate_and_render_live_match(match_id, home_team, away_team, output_mp4,
                                   progress_file, ckpt_path, max_steps,
                                   home_players, away_players, home_bgr, away_bgr):

    try:
        with open(progress_file, "w") as pf:
            json.dump({"status": "initializing", "progress": 3,
                       "stage": "Loading 3D Match Simulation...", "completed": False}, pf)
    except Exception:
        pass

    seed_val = int(hashlib.md5(f"match_{match_id}".encode()).hexdigest()[:8], 16) % 100000
    np.random.seed(seed_val)
    torch.manual_seed(seed_val)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_t = torch.device(device)
    policy = load_tikick(ckpt_path, device=device)

    env = make_env(seed_val, render=True)
    raw_obs = env.reset()

    hp = default_roster(home_team, home_players, True)
    ap = default_roster(away_team, away_players, False)

    writer = open_writer(output_mp4, fps=15)

    # 1. Pre-Match Intro Card (3 seconds = 45 frames)
    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=hp, away_players=ap, home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    num_agents = 10
    avail_size = 20

    left_rnn_states = torch.zeros((num_agents, 1, 256), dtype=torch.float32, device=device_t)
    left_masks = torch.ones((num_agents, 1), dtype=torch.float32, device=device_t)
    left_avail = torch.zeros((num_agents, 33), dtype=torch.float32, device=device_t)
    left_avail[:, :avail_size] = 1.0
    left_loffside = np.zeros(11, dtype=np.float32)
    left_roffside = np.zeros(11, dtype=np.float32)

    right_rnn_states = torch.zeros((num_agents, 1, 256), dtype=torch.float32, device=device_t)
    right_masks = torch.ones((num_agents, 1), dtype=torch.float32, device=device_t)
    right_avail = torch.zeros((num_agents, 33), dtype=torch.float32, device=device_t)
    right_avail[:, :avail_size] = 1.0
    right_loffside = np.zeros(11, dtype=np.float32)
    right_roffside = np.zeros(11, dtype=np.float32)

    curr_score = [0, 0]
    last_score = [0, 0]
    left_poss = right_poss = 0
    shots_h = shots_a = 0
    events = []
    goal_banner = None
    goal_banner_cd = 0
    raw_replay_buffer = []
    last_scorer = None

    for step in range(max_steps):
        # TiKick GPU Inference for both teams
        left_obs_raw = raw_obs[0:num_agents]
        left_obs_vec, left_loffside, left_roffside = extract_features_268(
            left_obs_raw, num_agents, left_loffside, left_roffside
        )
        left_obs_t = torch.tensor(left_obs_vec, dtype=torch.float32, device=device_t)

        right_obs_raw = raw_obs[num_agents:num_agents*2]
        right_obs_vec, right_loffside, right_roffside = extract_features_268(
            right_obs_raw, num_agents, right_loffside, right_roffside
        )
        right_obs_t = torch.tensor(right_obs_vec, dtype=torch.float32, device=device_t)

        with torch.no_grad():
            left_actions, _, left_next_rnn = policy(
                left_obs_t, left_rnn_states, left_masks, left_avail, deterministic=True
            )
            right_actions, _, right_next_rnn = policy(
                right_obs_t, right_rnn_states, right_masks, right_avail, deterministic=True
            )

        left_act_list = left_actions.cpu().numpy().flatten().astype(np.int32).tolist()
        right_act_list = right_actions.cpu().numpy().flatten().astype(np.int32).tolist()
        combined_actions = left_act_list + right_act_list

        raw_next_obs, _, done, _ = env.step(combined_actions)

        left_rnn_states = left_next_rnn
        right_rnn_states = right_next_rnn

        curr_score = list(raw_next_obs[0]['score'])
        ball_owned = raw_next_obs[0]['ball_owned_team']
        if ball_owned == 0: left_poss += 1
        elif ball_owned == 1: right_poss += 1

        match_min = max(1, min(90, int((step / max(max_steps, 1)) * 90)))
        is_second_half = step > (max_steps // 2)

        # Genuine Goal Detection
        just_scored = False
        if curr_score[0] > last_score[0]:
            shots_h += 1
            active_p = int(raw_next_obs[0].get('active', 8))
            if active_p == 0: active_p = 8
            scorer = hp[min(active_p, len(hp)-1)].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            last_scorer = scorer
            just_scored = True
            events.append({
                "minute": match_min, "type": "goal", "team": "home",
                "player": scorer, "details": f"Goal! {scorer} scores for {home_team}!"
            })
        elif curr_score[1] > last_score[1]:
            shots_a += 1
            active_p = int(raw_next_obs[10].get('active', 9))
            if active_p == 0: active_p = 9
            scorer = ap[min(active_p, len(ap)-1)].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            last_scorer = scorer
            just_scored = True
            events.append({
                "minute": match_min, "type": "goal", "team": "away",
                "player": scorer, "details": f"Goal! {scorer} scores for {away_team}!"
            })

        # Render frame
        frame = env.render(mode='rgb_array')
        if frame is not None:
            raw_replay_buffer.append(frame.copy())
            if len(raw_replay_buffer) > 40:
                raw_replay_buffer.pop(0)

            banner = goal_banner if goal_banner_cd > 0 else None
            annotated = draw_hud(frame, home_team, away_team, curr_score,
                                 match_min, step, max_steps,
                                 home_bgr, away_bgr, banner, is_second_half)
            writer.append_data(annotated)

            # Genuine Goal Celebration Linger (2.5s) + Real Action Slow-Mo Replay (3.5s)
            if just_scored:
                # 1. Live Celebration Linger on the ball in net / goal scene (2.5s = 38 frames)
                for _ in range(38):
                    writer.append_data(annotated)

                # 2. Slow-Motion Action Replay with Zoom & TV Replay Watermark (~3.5s = 50 frames)
                if len(raw_replay_buffer) >= 15:
                    replay_slice = raw_replay_buffer[-25:]
                    for rf in replay_slice:
                        replay_annotated = draw_replay_frame(
                            rf, home_team, away_team, curr_score, match_min, step, max_steps,
                            home_bgr, away_bgr, is_second_half, zoom_factor=1.35
                        )
                        writer.append_data(replay_annotated)
                        writer.append_data(replay_annotated)

                    final_replay = draw_replay_frame(
                        replay_slice[-1], home_team, away_team, curr_score, match_min, step, max_steps,
                        home_bgr, away_bgr, is_second_half, zoom_factor=1.35
                    )
                    for _ in range(15):
                        writer.append_data(final_replay)

            if goal_banner_cd > 0:
                goal_banner_cd -= 1
                if goal_banner_cd == 0:
                    goal_banner = None

        # 2. Half-Time Broadcast Studio Board (4 seconds = 60 frames)
        if step == (max_steps // 2):
            tot_p = max(1, left_poss + right_poss)
            ht_events = [e for e in events if e.get("minute", 0) <= 45]
            ht_card = draw_studio_stats_card(
                w=1280, h=720, title="HALF TIME", home_team=home_team, away_team=away_team,
                score=curr_score, h_poss=(left_poss/tot_p)*100, a_poss=(right_poss/tot_p)*100,
                h_shots=shots_h, a_shots=shots_a,
                home_bgr=home_bgr, away_bgr=away_bgr, events=ht_events
            )
            for _ in range(60):
                writer.append_data(ht_card)

        if step % 50 == 0 or step == max_steps - 1:
            pct = min(98, 5 + int((step / max(max_steps-1, 1)) * 93))
            try:
                with open(progress_file, "w") as pf:
                    json.dump({"status": "rendering", "progress": pct, "step": step,
                               "total_steps": max_steps, "match_minute": match_min,
                               "stage": f"Broadcasting 3D Match • {match_min}'/90'...",
                               "score": curr_score, "completed": False}, pf)
            except Exception:
                pass

        raw_obs = raw_next_obs
        if done:
            break

    # 3. Full-Time Final Whistle Studio Recap (5 seconds = 75 frames)
    tot_p = max(1, left_poss + right_poss)
    motm = last_scorer or (hp[8] if curr_score[0] >= curr_score[1] else ap[9])
    ft_card = draw_studio_stats_card(
        w=1280, h=720, title="FULL TIME", home_team=home_team, away_team=away_team,
        score=curr_score, h_poss=(left_poss/tot_p)*100, a_poss=(right_poss/tot_p)*100,
        h_shots=shots_h, a_shots=shots_a,
        home_bgr=home_bgr, away_bgr=away_bgr, events=events,
        motm_player=motm
    )
    for _ in range(75):
        writer.append_data(ft_card)

    writer.close()
    env.close()

    video_url = f"/recordings/{os.path.basename(output_mp4)}"
    try:
        with open(progress_file, "w") as pf:
            json.dump({"status": "completed", "progress": 100, "step": max_steps,
                       "total_steps": max_steps, "match_minute": 90,
                       "stage": "3D Match Broadcast Complete!",
                       "video_url": video_url, "score": curr_score, "completed": True}, pf)
    except Exception:
        pass

    result = {
        "match_id": str(match_id),
        "home_team": home_team, "away_team": away_team,
        "score": curr_score,
        "possession": [round((left_poss/tot_p)*100, 1), round((right_poss/tot_p)*100, 1)],
        "shots": [shots_h, shots_a],
        "events": events,
        "video_url": video_url,
    }
    print("MATCH_RESULT_JSON:" + json.dumps(result))


# ─────────────────────────────────────────────────────────────────────────────
# Replay Render from Native GRF .dump File
# ─────────────────────────────────────────────────────────────────────────────
def render_from_native_dump(match_id, home_team, away_team, output_mp4,
                            progress_file, home_players, away_players,
                            home_bgr, away_bgr, dump_file):
    from gfootball.env import script_helpers, config, football_env
    helper = script_helpers.ScriptHelpers()
    replay = helper.load_dump(dump_file)
    total_steps = len(replay)

    cfg = config.Config(replay[0]['debug']['config'])
    cfg['players'] = helper._ScriptHelpers__build_players(dump_file, cfg['players'])
    cfg['render_resolution_x'] = 1280
    cfg['render_resolution_y'] = 720
    cfg['real_time'] = False
    cfg['physics_steps_per_frame'] = 10

    env = football_env.FootballEnv(cfg)
    env.render()
    env.reset()

    hp = default_roster(home_team, home_players, True)
    ap = default_roster(away_team, away_players, False)

    writer = open_writer(output_mp4, fps=15)

    # 1. Pre-Match Card (3 seconds = 45 frames)
    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=hp, away_players=ap, home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    curr_score = [0, 0]
    last_score = [0, 0]
    left_poss = right_poss = 0
    shots_h = shots_a = 0
    events = []
    goal_banner = None
    goal_banner_cd = 0
    raw_replay_buffer = []
    last_scorer = None

    for step in range(total_steps):
        obs, rew, done, info = env.step([])
        raw_o = obs[0] if isinstance(obs, list) else obs

        curr_score = list(raw_o['score'])
        ball_owned = raw_o['ball_owned_team']
        if ball_owned == 0: left_poss += 1
        elif ball_owned == 1: right_poss += 1

        match_min = max(1, min(90, int((step / max(total_steps, 1)) * 90)))
        is_second_half = step > (total_steps // 2)

        # Genuine goal detection directly from replayed exact physics
        just_scored = False
        if curr_score[0] > last_score[0]:
            shots_h += 1
            active_p = int(raw_o.get('active', 8))
            if active_p == 0: active_p = 8
            scorer = hp[min(active_p, len(hp)-1)].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            last_scorer = scorer
            just_scored = True
            events.append({
                "minute": match_min, "type": "goal", "team": "home",
                "player": scorer, "details": f"Goal! {scorer} scores for {home_team}!"
            })
        elif curr_score[1] > last_score[1]:
            shots_a += 1
            active_p = int(raw_o.get('active', 9))
            if active_p == 0: active_p = 9
            scorer = ap[min(active_p, len(ap)-1)].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            last_scorer = scorer
            just_scored = True
            events.append({
                "minute": match_min, "type": "goal", "team": "away",
                "player": scorer, "details": f"Goal! {scorer} scores for {away_team}!"
            })

        frame = env.render(mode='rgb_array')
        if frame is not None:
            raw_replay_buffer.append(frame.copy())
            if len(raw_replay_buffer) > 40:
                raw_replay_buffer.pop(0)

            banner = goal_banner if goal_banner_cd > 0 else None
            annotated = draw_hud(frame, home_team, away_team, curr_score,
                                 match_min, step, total_steps,
                                 home_bgr, away_bgr, banner, is_second_half)
            writer.append_data(annotated)

            # Goal celebration linger + slow-mo replay of the actual goal
            if just_scored:
                for _ in range(38):
                    writer.append_data(annotated)
                if len(raw_replay_buffer) >= 15:
                    replay_slice = raw_replay_buffer[-25:]
                    for rf in replay_slice:
                        replay_annotated = draw_replay_frame(
                            rf, home_team, away_team, curr_score, match_min, step, total_steps,
                            home_bgr, away_bgr, is_second_half, zoom_factor=1.35
                        )
                        writer.append_data(replay_annotated)
                        writer.append_data(replay_annotated)
                    final_replay = draw_replay_frame(
                        replay_slice[-1], home_team, away_team, curr_score, match_min, step, total_steps,
                        home_bgr, away_bgr, is_second_half, zoom_factor=1.35
                    )
                    for _ in range(15):
                        writer.append_data(final_replay)

            if goal_banner_cd > 0:
                goal_banner_cd -= 1
                if goal_banner_cd == 0:
                    goal_banner = None

        # Half-Time Card
        if step == (total_steps // 2):
            tot_p = max(1, left_poss + right_poss)
            ht_events = [e for e in events if e.get("minute", 0) <= 45]
            ht_card = draw_studio_stats_card(
                w=1280, h=720, title="HALF TIME", home_team=home_team, away_team=away_team,
                score=curr_score, h_poss=(left_poss/tot_p)*100, a_poss=(right_poss/tot_p)*100,
                h_shots=shots_h, a_shots=shots_a,
                home_bgr=home_bgr, away_bgr=away_bgr, events=ht_events
            )
            for _ in range(60):
                writer.append_data(ht_card)

        if step % 50 == 0 or step == total_steps - 1:
            pct = min(98, 5 + int((step / max(total_steps-1, 1)) * 93))
            try:
                with open(progress_file, "w") as pf:
                    json.dump({"status": "rendering", "progress": pct, "step": step,
                               "total_steps": total_steps, "match_minute": match_min,
                               "stage": f"Replaying 3D Broadcast • {match_min}'/90'...",
                               "score": curr_score, "completed": False}, pf)
            except Exception:
                pass

        if done: break

    # Full-Time Card
    tot_p = max(1, left_poss + right_poss)
    motm = last_scorer or (hp[8] if curr_score[0] >= curr_score[1] else ap[9])
    ft_card = draw_studio_stats_card(
        w=1280, h=720, title="FULL TIME", home_team=home_team, away_team=away_team,
        score=curr_score, h_poss=(left_poss/tot_p)*100, a_poss=(right_poss/tot_p)*100,
        h_shots=shots_h, a_shots=shots_a,
        home_bgr=home_bgr, away_bgr=away_bgr, events=events,
        motm_player=motm
    )
    for _ in range(75):
        writer.append_data(ft_card)

    writer.close()
    env.close()

    video_url = f"/recordings/{os.path.basename(output_mp4)}"
    try:
        with open(progress_file, "w") as pf:
            json.dump({"status": "completed", "progress": 100, "step": total_steps,
                       "total_steps": total_steps, "match_minute": 90,
                       "stage": "3D Match Replay Complete!",
                       "video_url": video_url, "score": curr_score, "completed": True}, pf)
    except Exception:
        pass

    result = {
        "match_id": str(match_id),
        "home_team": home_team, "away_team": away_team,
        "score": curr_score,
        "possession": [round((left_poss/tot_p)*100, 1), round((right_poss/tot_p)*100, 1)],
        "shots": [shots_h, shots_a],
        "events": events,
        "video_url": video_url,
    }
    print("MATCH_RESULT_JSON:" + json.dumps(result))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def run_match(match_id, home_team, away_team, render_video, max_steps, output_mp4,
              ckpt_path, progress_file, home_players=None, away_players=None,
              home_color=None, away_color=None, trace_file=None):

    home_color = home_color or team_color_from_name(home_team)
    away_color = away_color or team_color_from_name(away_team)
    home_bgr   = hex_to_bgr(home_color)
    away_bgr   = hex_to_bgr(away_color)

    # Replay from native .dump file if available
    dump_candidate = trace_file if trace_file and trace_file.endswith(".dump") else None
    if not dump_candidate:
        default_dump = f"/mnt/c/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/reports/recordings/trace_{match_id}.dump"
        if os.path.exists(default_dump):
            dump_candidate = default_dump

    if render_video and dump_candidate and os.path.exists(dump_candidate):
        render_from_native_dump(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            output_mp4=output_mp4,
            progress_file=progress_file,
            home_players=home_players,
            away_players=away_players,
            home_bgr=home_bgr,
            away_bgr=away_bgr,
            dump_file=dump_candidate
        )
        return

    # Fallback to direct live simulation & rendering
    simulate_and_render_live_match(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        output_mp4=output_mp4,
        progress_file=progress_file,
        ckpt_path=ckpt_path,
        max_steps=max_steps,
        home_players=home_players,
        away_players=away_players,
        home_bgr=home_bgr,
        away_bgr=away_bgr
    )


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    run_match(
        match_id    = args["match_id"],
        home_team   = args["home_team"],
        away_team   = args["away_team"],
        render_video= args["render_video"],
        max_steps   = args.get("max_steps", 1200),
        output_mp4  = args["output_mp4"],
        ckpt_path   = args["ckpt_path"],
        progress_file=args["progress_file"],
        home_players = args.get("home_players"),
        away_players = args.get("away_players"),
        home_color  = args.get("home_color"),
        away_color  = args.get("away_color"),
        trace_file  = args.get("trace_file"),
    )
"""


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def to_wsl_path(win_path: Path) -> str:
    resolved = win_path.resolve()
    drive = resolved.drive.replace(":", "").lower()
    rest  = str(resolved.relative_to(resolved.anchor)).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


# ---------------------------------------------------------------------------
# GRFNativeRunner
# ---------------------------------------------------------------------------

class GRFNativeRunner:
    def __init__(self):
        self.wsl_python   = "/root/venv_baller/bin/python3"
        self.local_ckpt   = TIKICK_CHECKPOINT_PATH
        self.local_tikick = LOCAL_TIKICK_DIR
        self.max_steps    = FOOTY_GRF_MAX_STEPS

    _cached_available = None
    _last_check_time = 0.0

    def is_available(self, force_recheck: bool = False) -> bool:
        import time
        now = time.time()
        if not force_recheck and GRFNativeRunner._cached_available is not None and (now - GRFNativeRunner._last_check_time) < 60.0:
            return GRFNativeRunner._cached_available
        try:
            res = subprocess.run(
                ["wsl", "-u", "root", self.wsl_python, "-c",
                 "import gfootball, torch; print('OK')"],
                capture_output=True, text=True, timeout=10
            )
            GRFNativeRunner._cached_available = "OK" in res.stdout
            GRFNativeRunner._last_check_time = now
            return GRFNativeRunner._cached_available
        except Exception:
            GRFNativeRunner._cached_available = False
            GRFNativeRunner._last_check_time = now
            return False

    def run_match(
        self,
        match_id:     str,
        home_team:    str,
        away_team:    str,
        render_video: bool = False,
        max_steps:    Optional[int] = None,
        home_players: Optional[List[str]] = None,
        away_players: Optional[List[str]] = None,
        home_color:   Optional[str] = None,
        away_color:   Optional[str] = None,
    ) -> Dict[str, Any]:

        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        steps = max_steps or self.max_steps

        filename        = f"match_{match_id}.mp4" if not str(match_id).startswith("match_") else f"{match_id}.mp4"
        output_mp4_win  = RECORDINGS_DIR / filename
        output_mp4_wsl  = to_wsl_path(output_mp4_win)

        trace_win = RECORDINGS_DIR / f"trace_{match_id}.npz"
        trace_wsl = to_wsl_path(trace_win)

        ckpt_wsl   = to_wsl_path(self.local_ckpt)
        tikick_wsl = to_wsl_path(self.local_tikick)

        prog_file_win = RECORDINGS_DIR / f"progress_{match_id}.json"
        prog_file_wsl = to_wsl_path(prog_file_win)

        _home_color = home_color or team_color_from_name(home_team)
        _away_color = away_color or team_color_from_name(away_team)

        script_content   = WSL_GRF_SCRIPT.replace("{tikick_dir}", tikick_wsl)
        script_file_win  = RECORDINGS_DIR / f"run_render_{match_id}.py"
        script_file_win.write_text(script_content, encoding="utf-8")
        script_file_wsl  = to_wsl_path(script_file_win)

        match_args = {
            "match_id":      str(match_id),
            "home_team":     home_team,
            "away_team":     away_team,
            "render_video":  render_video,
            "max_steps":     steps,
            "output_mp4":    output_mp4_wsl,
            "ckpt_path":     ckpt_wsl,
            "progress_file": prog_file_wsl,
            "home_players":  home_players,
            "away_players":  away_players,
            "home_color":    _home_color,
            "away_color":    _away_color,
            "trace_file":    trace_wsl,
        }
        args_json = json.dumps(match_args)

        cmd = [
            "wsl", "-u", "root", "bash", "-c",
            f'xvfb-run -a -s "-screen 0 1280x720x24" {self.wsl_python} {script_file_wsl} \'{args_json}\''
        ]

        logger.info("GRF native renderer: rendering 3D broadcast for match=%s", match_id)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        finally:
            try:
                if script_file_win.exists():
                    script_file_win.unlink()
            except Exception:
                pass

        if "MATCH_RESULT_JSON:" in res.stdout:
            json_str = res.stdout.split("MATCH_RESULT_JSON:")[1].splitlines()[0]
            return json.loads(json_str)

        logger.error("GRF Renderer error:\nSTDOUT: %s\nSTDERR: %s", res.stdout, res.stderr)
        raise RuntimeError(f"Native GRF render execution failed: {res.stderr or res.stdout}")

    def simulate(
        self,
        home_team,
        away_team,
        max_steps:    Optional[int] = None,
        render_video: bool = False,
        match_id:     Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adapter delegating single-match simulations to the batch runner.
        """
        from logic.grf_batch_runner import GRFBatchRunner
        batch_runner = GRFBatchRunner()
        return batch_runner.simulate(
            home_team=home_team,
            away_team=away_team,
            max_steps=max_steps or self.max_steps,
            render_video=render_video,
            match_id=match_id
        )
