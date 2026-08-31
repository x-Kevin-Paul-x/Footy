"""
Standalone 3D Cinematic Broadcast & Replay Video Renderer.
Renders TV-quality 720p HD highlights from pre-computed MatchTrajectory (.npz)
or native GRF episode (.dump) files without invoking neural network policy models.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

try:
    import cv2
    import imageio
except ImportError:
    cv2 = None
    imageio = None

from logic.grf_trajectory import MatchTrajectory, MatchManifest

# Deterministic kit palette
_KIT_PALETTE = [
    "#e63946", "#2196f3", "#4caf50", "#ff9800", "#9c27b0",
    "#00bcd4", "#f44336", "#3f51b5", "#8bc34a", "#ff5722",
    "#009688", "#673ab7", "#ffc107", "#607d8b", "#e91e63",
]


def team_color_from_name(name: str) -> str:
    idx = int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % len(_KIT_PALETTE)
    return _KIT_PALETTE[idx]


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip('#')
    if len(h) != 6:
        return (50, 50, 200)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def text_color_for_bg(bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
    b, g, r = bgr
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return (255, 255, 255) if lum < 140 else (15, 15, 15)


def team_abbr(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][:2]).upper()
    return name[:3].upper()


def draw_hud(
    frame: np.ndarray,
    home_team: str,
    away_team: str,
    score: Tuple[int, int],
    match_min: int,
    home_bgr: Tuple[int, int, int],
    away_bgr: Tuple[int, int, int],
    goal_banner: Optional[str] = None,
    is_second_half: bool = False
) -> np.ndarray:
    annotated = frame.copy()
    h_img, w_img = annotated.shape[:2]

    # Floating Modern Top-Left TV Pill HUD
    px, py = 32, 24
    pw, ph = 370, 38

    overlay = annotated.copy()
    cv2.rectangle(overlay, (px, py), (px + pw, py + ph), (14, 18, 26), -1)
    cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)
    cv2.rectangle(annotated, (px, py), (px + pw, py + ph), (55, 68, 85), 1)

    # Home Pill
    h_abbr = team_abbr(home_team)
    cv2.rectangle(annotated, (px + 2, py + 2), (px + 62, py + ph - 2), home_bgr, -1)
    htc = text_color_for_bg(home_bgr)
    cv2.putText(annotated, h_abbr, (px + 10, py + 26), cv2.FONT_HERSHEY_DUPLEX, 0.62, htc, 2, cv2.LINE_AA)

    # Score
    cv2.putText(annotated, str(score[0]), (px + 76, py + 28), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated, "-", (px + 100, py + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 175, 195), 1, cv2.LINE_AA)
    cv2.putText(annotated, str(score[1]), (px + 120, py + 28), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

    # Away Pill
    a_abbr = team_abbr(away_team)
    cv2.rectangle(annotated, (px + 144, py + 2), (px + 204, py + ph - 2), away_bgr, -1)
    atc = text_color_for_bg(away_bgr)
    cv2.putText(annotated, a_abbr, (px + 152, py + 26), cv2.FONT_HERSHEY_DUPLEX, 0.62, atc, 2, cv2.LINE_AA)

    # Clock
    half_tag = "2ND" if is_second_half else "1ST"
    clock_str = f"{half_tag}  {match_min:02d}:00"
    cv2.rectangle(annotated, (px + 208, py + 2), (px + pw - 2, py + ph - 2), (24, 30, 42), -1)
    cv2.putText(annotated, clock_str, (px + 222, py + 26), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 220, 255), 1, cv2.LINE_AA)

    # Goal Banner
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


def draw_replay_frame(
    raw_frame: np.ndarray,
    home_team: str,
    away_team: str,
    score: Tuple[int, int],
    match_min: int,
    home_bgr: Tuple[int, int, int],
    away_bgr: Tuple[int, int, int],
    is_second_half: bool,
    zoom_factor: float = 1.35
) -> np.ndarray:
    h, w = raw_frame.shape[:2]
    new_w, new_h = int(w / zoom_factor), int(h / zoom_factor)
    x1 = (w - new_w) // 2
    y1 = (h - new_h) // 2
    cropped = raw_frame[y1:y1 + new_h, x1:x1 + new_w]
    zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    annotated = draw_hud(zoomed, home_team, away_team, score, match_min, home_bgr, away_bgr, None, is_second_half)

    # Replay Watermark Badge (Top-Right)
    rx, ry = w - 210, 24
    rw, rh = 180, 36
    overlay = annotated.copy()
    cv2.rectangle(overlay, (rx, ry), (rx + rw, ry + rh), (15, 20, 30), -1)
    cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)
    cv2.rectangle(annotated, (rx, ry), (rx + rw, ry + rh), (220, 50, 50), 2)
    cv2.circle(annotated, (rx + 20, ry + 18), 6, (0, 0, 255), -1)
    cv2.putText(annotated, f"REPLAY  {match_min}'", (rx + 35, ry + 25), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    return annotated


def draw_pre_match_card(
    w: int = 1280,
    h: int = 720,
    home_team: str = "",
    away_team: str = "",
    home_players: Optional[List[str]] = None,
    away_players: Optional[List[str]] = None,
    home_formation: str = "4-3-3",
    away_formation: str = "4-2-3-1",
    home_bgr: Tuple[int, int, int] = (50, 50, 220),
    away_bgr: Tuple[int, int, int] = (220, 50, 50)
) -> np.ndarray:
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (18, 22, 32)

    cv2.rectangle(canvas, (0, 0), (w, 80), (10, 14, 22), -1)
    cv2.putText(canvas, "FOOTY 3D BROADCAST  *  MATCHDAY PRESENTATION",
                (w // 2 - 290, 50), cv2.FONT_HERSHEY_DUPLEX, 0.78, (0, 220, 255), 2, cv2.LINE_AA)

    cv2.rectangle(canvas, (50, 105), (w // 2 - 25, 175), home_bgr, -1)
    cv2.rectangle(canvas, (w // 2 + 25, 105), (w - 50, 175), away_bgr, -1)

    htc = text_color_for_bg(home_bgr)
    atc = text_color_for_bg(away_bgr)

    cv2.putText(canvas, home_team.upper(), (70, 152), cv2.FONT_HERSHEY_DUPLEX, 0.85, htc, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"[{home_formation}]", (w // 2 - 130, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.58, htc, 2, cv2.LINE_AA)

    cv2.putText(canvas, away_team.upper(), (w // 2 + 45, 152), cv2.FONT_HERSHEY_DUPLEX, 0.85, atc, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"[{away_formation}]", (w - 150, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.58, atc, 2, cv2.LINE_AA)

    cv2.putText(canvas, "STARTING XI", (70, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 220, 255), 2)
    cv2.putText(canvas, "STARTING XI", (w // 2 + 45, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 220, 255), 2)

    hp = home_players[:11] if home_players else [f"{home_team} Player {i+1}" for i in range(11)]
    ap = away_players[:11] if away_players else [f"{away_team} Player {i+1}" for i in range(11)]

    for idx, p in enumerate(hp):
        y = 255 + idx * 36
        num_str = f"{idx+1}." if idx > 0 else "1 (GK)"
        cv2.putText(canvas, f"{num_str:6s} {p}", (70, y), cv2.FONT_HERSHEY_DUPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)

    for idx, p in enumerate(ap):
        y = 255 + idx * 36
        num_str = f"{idx+1}." if idx > 0 else "1 (GK)"
        cv2.putText(canvas, f"{num_str:6s} {p}", (w // 2 + 45, y), cv2.FONT_HERSHEY_DUPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)

    return canvas


def draw_studio_stats_card(
    w: int = 1280,
    h: int = 720,
    title: str = "HALF TIME",
    home_team: str = "",
    away_team: str = "",
    score: Tuple[int, int] = (0, 0),
    h_poss: float = 50.0,
    a_poss: float = 50.0,
    h_shots: int = 0,
    a_shots: int = 0,
    h_sot: int = 0,
    a_sot: int = 0,
    h_xg: float = 0.0,
    a_xg: float = 0.0,
    home_bgr: Tuple[int, int, int] = (50, 50, 220),
    away_bgr: Tuple[int, int, int] = (220, 50, 50),
    events: Optional[List[Dict[str, Any]]] = None,
    motm_player: Optional[str] = None
) -> np.ndarray:
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (16, 20, 28)

    cv2.rectangle(canvas, (0, 0), (w, 80), (10, 14, 20), -1)
    cv2.putText(canvas, title, (w // 2 - 90, 52), cv2.FONT_HERSHEY_DUPLEX, 0.88, (0, 220, 255), 2, cv2.LINE_AA)

    cv2.rectangle(canvas, (80, 105), (w // 2 - 80, 185), home_bgr, -1)
    cv2.rectangle(canvas, (w // 2 + 80, 105), (w - 80, 185), away_bgr, -1)
    cv2.rectangle(canvas, (w // 2 - 75, 105), (w // 2 + 75, 185), (10, 14, 20), -1)

    htc = text_color_for_bg(home_bgr)
    atc = text_color_for_bg(away_bgr)

    cv2.putText(canvas, home_team.upper(), (100, 156), cv2.FONT_HERSHEY_DUPLEX, 0.85, htc, 2, cv2.LINE_AA)
    cv2.putText(canvas, away_team.upper(), (w // 2 + 100, 156), cv2.FONT_HERSHEY_DUPLEX, 0.85, atc, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"{score[0]} - {score[1]}", (w // 2 - 50, 160), cv2.FONT_HERSHEY_DUPLEX, 1.05, (255, 255, 255), 2, cv2.LINE_AA)

    stat_rows = [
        ("Possession", f"{h_poss:.1f}%", f"{a_poss:.1f}%"),
        ("Total Shots", str(h_shots), str(a_shots)),
        ("Shots on Target", str(h_sot), str(a_sot)),
        ("Expected Goals (xG)", f"{h_xg:.2f}", f"{a_xg:.2f}")
    ]

    for idx, (label, val_l, val_r) in enumerate(stat_rows):
        y = 250 + idx * 52
        cv2.rectangle(canvas, (80, y - 32), (w - 80, y + 14), (24, 30, 42), -1)
        cv2.putText(canvas, val_l, (120, y), cv2.FONT_HERSHEY_DUPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, label, (w // 2 - 90, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (180, 200, 220), 2, cv2.LINE_AA)
        cv2.putText(canvas, val_r, (w - 180, y), cv2.FONT_HERSHEY_DUPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)

    if events:
        goals = [e for e in events if e.get("type") == "goal"]
        if goals:
            cv2.putText(canvas, "MATCH TIMELINE", (80, 490), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (16, 185, 129), 2)
            for idx, g in enumerate(goals[:3]):
                gy = 525 + idx * 30
                cv2.putText(canvas, f"{g.get('minute')}' - {g.get('player')} ({g.get('team', '').upper()})",
                            (80, gy), cv2.FONT_HERSHEY_DUPLEX, 0.58, (240, 240, 240), 1, cv2.LINE_AA)

    if motm_player and title == "FULL TIME":
        mx, my = w // 2 + 40, 480
        cv2.rectangle(canvas, (mx, my), (w - 80, my + 130), (28, 35, 50), -1)
        cv2.rectangle(canvas, (mx, my), (w - 80, my + 130), (0, 215, 255), 2)
        cv2.putText(canvas, "MAN OF THE MATCH", (mx + 20, my + 38), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, motm_player, (mx + 20, my + 82), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)

    return canvas
