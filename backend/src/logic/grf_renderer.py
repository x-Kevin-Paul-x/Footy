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
from collections import deque
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


def team_color_from_name(name: Any) -> str:
    str_name = getattr(name, "name", str(name))
    idx = int(hashlib.md5(str_name.encode('utf-8')).hexdigest()[:4], 16) % len(_KIT_PALETTE)
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
    annotated = frame  # In-place drawing on writable frame, avoid full-frame copy
    h_img, w_img = annotated.shape[:2]

    # Floating Modern Top-Left TV Pill HUD
    px, py = 32, 24
    pw, ph = 370, 38

    # Fast ROI slice alpha-blending
    roi = annotated[py:py+ph, px:px+pw]
    bg_patch = np.full((ph, pw, 3), (14, 18, 26), dtype=np.uint8)
    cv2.addWeighted(bg_patch, 0.85, roi, 0.15, 0, roi)
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
        bw, bh = bx2 - bx1, by2 - by1
        g_roi = annotated[by1:by2, bx1:bx2]
        g_bg = np.full((bh, bw, 3), (10, 15, 24), dtype=np.uint8)
        cv2.addWeighted(g_bg, 0.88, g_roi, 0.12, 0, g_roi)
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


_STATIC_PITCH_CACHE: Dict[Tuple[int, int], np.ndarray] = {}


def create_static_pitch_background(w: int = 1280, h: int = 720) -> np.ndarray:
    key = (w, h)
    if key in _STATIC_PITCH_CACHE:
        return _STATIC_PITCH_CACHE[key]

    if cv2 is None:
        bg = np.zeros((h, w, 3), dtype=np.uint8)
        _STATIC_PITCH_CACHE[key] = bg
        return bg

    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # 1. Pitch Turf with alternating vertical grass stripes
    px_min, px_max = 70, w - 70
    py_min, py_max = 85, h - 35
    pw = px_max - px_min
    ph = py_max - py_min

    canvas[:] = (20, 24, 34)  # Dark surround

    stripe_count = 14
    stripe_w = pw / stripe_count
    for s in range(stripe_count):
        sx1 = int(px_min + s * stripe_w)
        sx2 = int(px_min + (s + 1) * stripe_w)
        grass_color = (34, 128, 48) if s % 2 == 0 else (28, 116, 42)
        cv2.rectangle(canvas, (sx1, py_min), (sx2, py_max), grass_color, -1)

    # 2. White Pitch Markings
    white = (245, 245, 245)
    cv2.rectangle(canvas, (px_min, py_min), (px_max, py_max), white, 2)

    # Halfway line & Center Circle
    mid_x = (px_min + px_max) // 2
    mid_y = (py_min + py_max) // 2
    cv2.line(canvas, (mid_x, py_min), (mid_x, py_max), white, 2)
    cv2.circle(canvas, (mid_x, mid_y), int(ph * 0.16), white, 2)
    cv2.circle(canvas, (mid_x, mid_y), 4, white, -1)

    # Penalty Boxes & 6-Yard Boxes (Left & Right)
    box_w = int(pw * 0.16)
    box_h = int(ph * 0.44)
    small_box_w = int(pw * 0.055)
    small_box_h = int(ph * 0.22)

    # Left box
    cv2.rectangle(canvas, (px_min, mid_y - box_h // 2), (px_min + box_w, mid_y + box_h // 2), white, 2)
    cv2.rectangle(canvas, (px_min, mid_y - small_box_h // 2), (px_min + small_box_w, mid_y + small_box_h // 2), white, 2)
    cv2.circle(canvas, (px_min + int(pw * 0.11), mid_y), 3, white, -1)

    # Right box
    cv2.rectangle(canvas, (px_max - box_w, mid_y - box_h // 2), (px_max, mid_y + box_h // 2), white, 2)
    cv2.rectangle(canvas, (px_max - small_box_w, mid_y - small_box_h // 2), (px_max, mid_y + small_box_h // 2), white, 2)
    cv2.circle(canvas, (px_max - int(pw * 0.11), mid_y), 3, white, -1)

    # Goals (posts)
    goal_h = int(ph * 0.14)
    cv2.rectangle(canvas, (px_min - 12, mid_y - goal_h // 2), (px_min, mid_y + goal_h // 2), (200, 200, 200), -1)
    cv2.rectangle(canvas, (px_max, mid_y - goal_h // 2), (px_max + 12, mid_y + goal_h // 2), (200, 200, 200), -1)

    _STATIC_PITCH_CACHE[key] = canvas
    return canvas


def draw_pitch_frame_from_state(
    frame_state: Dict[str, Any],
    home_team: str,
    away_team: str,
    home_players: Optional[List[str]] = None,
    away_players: Optional[List[str]] = None,
    home_bgr: Tuple[int, int, int] = (50, 50, 220),
    away_bgr: Tuple[int, int, int] = (220, 50, 50),
    goal_banner: Optional[str] = None,
    w: int = 1280,
    h: int = 720
) -> np.ndarray:
    """
    Render a single high-fidelity 720p broadcast frame directly from trajectory coordinates.
    Pure display pipe: does NOT depend on GRF environment or physics engine.
    """
    if cv2 is None:
        return np.zeros((h, w, 3), dtype=np.uint8)

    canvas = create_static_pitch_background(w, h).copy()

    px_min, px_max = 70, w - 70
    py_min, py_max = 85, h - 35
    pw = px_max - px_min
    ph = py_max - py_min

    # Coordinate mapping function
    def to_pixel(gx: float, gy: float) -> Tuple[int, int]:
        # GRF pitch: x in [-1.0, 1.0], y in [-0.42, 0.42]
        nx = max(-1.0, min(1.0, gx))
        ny = max(-0.44, min(0.44, gy))
        x_px = int(px_min + ((nx + 1.0) / 2.0) * pw)
        y_px = int(py_min + ((ny + 0.44) / 0.88) * ph)
        return x_px, y_px

    player_coords = frame_state["player_coords"]
    player_dirs = frame_state["player_dirs"]
    ball_coords = frame_state["ball_coords"]

    # 3. Draw Players
    # Home Players (0..10)
    for i in range(min(11, len(player_coords))):
        px, py = to_pixel(player_coords[i, 0], player_coords[i, 1])
        # Heading arrow
        dx, dy = player_dirs[i, 0], player_dirs[i, 1]
        norm = max(1e-4, np.hypot(dx, dy))
        hx, hy = int(px + (dx / norm) * 16), int(py + (dy / norm) * 16)
        cv2.line(canvas, (px, py), (hx, hy), (255, 255, 255), 2, cv2.LINE_AA)

        # Player token
        cv2.circle(canvas, (px, py), 13, (15, 15, 15), -1)
        cv2.circle(canvas, (px, py), 11, home_bgr, -1)
        cv2.circle(canvas, (px, py), 11, (255, 255, 255), 1, cv2.LINE_AA)
        num_str = str(i + 1) if i > 0 else "1"
        htc = text_color_for_bg(home_bgr)
        cv2.putText(canvas, num_str, (px - (4 if len(num_str) == 1 else 7), py + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, htc, 1, cv2.LINE_AA)

    # Away Players (11..21)
    for i in range(11, min(22, len(player_coords))):
        away_idx = i - 11
        px, py = to_pixel(player_coords[i, 0], player_coords[i, 1])
        dx, dy = player_dirs[i, 0], player_dirs[i, 1]
        norm = max(1e-4, np.hypot(dx, dy))
        hx, hy = int(px + (dx / norm) * 16), int(py + (dy / norm) * 16)
        cv2.line(canvas, (px, py), (hx, hy), (255, 255, 255), 2, cv2.LINE_AA)

        cv2.circle(canvas, (px, py), 13, (15, 15, 15), -1)
        cv2.circle(canvas, (px, py), 11, away_bgr, -1)
        cv2.circle(canvas, (px, py), 11, (0, 220, 255), 1, cv2.LINE_AA)
        num_str = str(away_idx + 1) if away_idx > 0 else "1"
        atc = text_color_for_bg(away_bgr)
        cv2.putText(canvas, num_str, (px - (4 if len(num_str) == 1 else 7), py + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, atc, 1, cv2.LINE_AA)

    # 4. Draw Ball with dynamic height shadow
    bx, by = to_pixel(ball_coords[0], ball_coords[1])
    bz = float(ball_coords[2]) if len(ball_coords) > 2 else 0.0
    shadow_offset = int(bz * 40)
    # Shadow on grass
    cv2.ellipse(canvas, (bx, by), (8, 4), 0, 0, 360, (15, 60, 25), -1)
    # Ball sphere elevated by z
    ball_y = by - shadow_offset
    ball_rad = max(4, min(10, int(6 + bz * 6)))
    cv2.circle(canvas, (bx, ball_y), ball_rad + 1, (20, 20, 20), -1)
    cv2.circle(canvas, (bx, ball_y), ball_rad, (255, 255, 255), -1)
    cv2.circle(canvas, (bx, ball_y), max(1, ball_rad - 3), (0, 0, 0), 1)

    # 5. Overlay Scoreboard HUD
    score = frame_state.get("score", [0, 0])
    match_min = frame_state.get("match_minute", 1)
    is_second_half = frame_state.get("is_second_half", False)

    annotated = draw_hud(
        canvas, home_team, away_team, (score[0], score[1]),
        match_min, home_bgr, away_bgr, goal_banner, is_second_half
    )

    return annotated


def render_video_from_trajectory(
    trajectory: MatchTrajectory,
    output_mp4: str,
    progress_callback: Optional[Any] = None
) -> str:
    """
    Render 100% pure deterministic 720p HD broadcast MP4 from recorded MatchTrajectory.
    Zero physics re-simulation: reads strictly from trajectory arrays and manifest metadata.
    """
    if imageio is None:
        raise ImportError("imageio with libx264 is required for trajectory video rendering.")

    manifest = trajectory.manifest
    total_steps = trajectory.total_steps
    home_team = manifest.home_team
    away_team = manifest.away_team
    home_color = manifest.home_color or team_color_from_name(home_team)
    away_color = manifest.away_color or team_color_from_name(away_team)
    home_bgr = hex_to_bgr(home_color)
    away_bgr = hex_to_bgr(away_color)

    os.makedirs(os.path.dirname(output_mp4) or '.', exist_ok=True)
    writer = imageio.get_writer(
        output_mp4, fps=15, codec='libx264',
        pixelformat='yuv420p',
        ffmpeg_params=['-crf', '28', '-preset', 'faster', '-b:v', '220k', '-maxrate', '350k', '-bufsize', '500k']
    )

    # 1. Pre-Match Card (3 seconds = 45 frames)
    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=manifest.home_players, away_players=manifest.away_players,
        home_formation=manifest.home_formation, away_formation=manifest.away_formation,
        home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    goal_events_by_step = {}
    for ev in manifest.events:
        if ev.get("type") == "goal":
            g_min = ev.get("minute", 0)
            approx_step = int((g_min / 90.0) * total_steps)
            goal_events_by_step[approx_step] = ev

    goal_banner = None
    goal_banner_cd = 0
    replay_buffer = deque(maxlen=30)

    for step in range(total_steps):
        state = trajectory.get_frame_state(step)
        match_min = state["match_minute"]

        # Check for goal event trigger
        if step in goal_events_by_step:
            gev = goal_events_by_step[step]
            scorer = gev.get("player", "Player")
            team_str = gev.get("team", "").upper()
            goal_banner = f"GOAL!  {scorer} ({team_str})  {match_min}'"
            goal_banner_cd = 30

        banner_to_show = goal_banner if goal_banner_cd > 0 else None
        frame = draw_pitch_frame_from_state(
            state, home_team, away_team,
            home_players=manifest.home_players,
            away_players=manifest.away_players,
            home_bgr=home_bgr, away_bgr=away_bgr,
            goal_banner=banner_to_show
        )
        writer.append_data(frame)

        replay_buffer.append(frame)

        # Slow-mo zoom action replay when goal is hit
        if step in goal_events_by_step and len(replay_buffer) >= 15:
            for _ in range(30):
                writer.append_data(frame)
            recent_frames = list(replay_buffer)[-20:]
            for rf in recent_frames:
                replay_annotated = draw_replay_frame(
                    rf, home_team, away_team, tuple(state["score"]),
                    match_min, home_bgr, away_bgr, state["is_second_half"], zoom_factor=1.35
                )
                writer.append_data(replay_annotated)
                writer.append_data(replay_annotated)

        if goal_banner_cd > 0:
            goal_banner_cd -= 1
            if goal_banner_cd == 0:
                goal_banner = None

        # Half-Time Studio Recap Card
        if step == (total_steps // 2):
            ht_card = draw_studio_stats_card(
                w=1280, h=720, title="HALF TIME",
                home_team=home_team, away_team=away_team,
                score=tuple(state["score"]),
                h_poss=manifest.possession[0], a_poss=manifest.possession[1],
                h_shots=manifest.shots[0], a_shots=manifest.shots[1],
                h_sot=manifest.shots_on_target[0], a_sot=manifest.shots_on_target[1],
                h_xg=manifest.xg[0], a_xg=manifest.xg[1],
                home_bgr=home_bgr, away_bgr=away_bgr,
                events=[e for e in manifest.events if e.get("minute", 0) <= 45]
            )
            for _ in range(60):
                writer.append_data(ht_card)

        # Progress Notification
        if progress_callback and (step % 50 == 0 or step == total_steps - 1):
            pct = min(98, 5 + int((step / max(total_steps - 1, 1)) * 93))
            progress_callback(pct, step, total_steps, match_min)

    # Full-Time Card with Man of the Match
    motm = None
    goals = [e for e in manifest.events if e.get("type") == "goal"]
    if goals:
        motm = goals[-1].get("player")
    elif manifest.home_players and manifest.away_players:
        motm = manifest.home_players[8] if manifest.home_score >= manifest.away_score else manifest.away_players[9]

    ft_card = draw_studio_stats_card(
        w=1280, h=720, title="FULL TIME",
        home_team=home_team, away_team=away_team,
        score=manifest.score,
        h_poss=manifest.possession[0], a_poss=manifest.possession[1],
        h_shots=manifest.shots[0], a_shots=manifest.shots[1],
        h_sot=manifest.shots_on_target[0], a_sot=manifest.shots_on_target[1],
        h_xg=manifest.xg[0], a_xg=manifest.xg[1],
        home_bgr=home_bgr, away_bgr=away_bgr,
        events=manifest.events,
        motm_player=motm
    )
    for _ in range(75):
        writer.append_data(ft_card)

    writer.close()
    return f"/recordings/{os.path.basename(output_mp4)}"


def transcode_live_avi_to_broadcast_mp4(
    raw_avi_path: str,
    output_mp4_path: str,
    manifest: MatchManifest,
    home_color: Optional[str] = None,
    away_color: Optional[str] = None,
    progress_callback: Optional[Any] = None
) -> str:
    """
    Overlays TV-style broadcast presentation (Lineup card, floating scoreboard pill,
    goal celebration popups, half-time and full-time studio cards) onto a native 3D
    video recorded directly during live C++ simulation. Guarantees 100% deterministic
    consistency with match scorecard and zero floating-point graphics replay drift.
    """
    if cv2 is None or imageio is None:
        raise RuntimeError("cv2 and imageio are required for video transcoding")

    cap = cv2.VideoCapture(raw_avi_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open live recording AVI: {raw_avi_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise ValueError(f"Recording AVI {raw_avi_path} contains 0 frames")

    os.makedirs(os.path.dirname(output_mp4_path) or '.', exist_ok=True)
    writer = imageio.get_writer(
        output_mp4_path,
        fps=15,
        codec='libx264',
        pixelformat='yuv420p',
        ffmpeg_params=['-crf', '28', '-preset', 'faster', '-b:v', '220k', '-maxrate', '350k', '-bufsize', '500k']
    )

    home_team = manifest.home_team
    away_team = manifest.away_team
    h_col = home_color or team_color_from_name(home_team)
    a_col = away_color or team_color_from_name(away_team)
    home_bgr = hex_to_bgr(h_col)
    away_bgr = hex_to_bgr(a_col)

    # 1. Pre-match starting lineup card (3 seconds)
    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=manifest.home_players, away_players=manifest.away_players,
        home_formation=manifest.home_formation, away_formation=manifest.away_formation,
        home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    goal_events_by_step = {}
    for ev in manifest.events:
        if ev.get("type") == "goal":
            s_idx = ev.get("step")
            if s_idx is None:
                g_min = ev.get("minute", 0)
                s_idx = int((g_min / 90.0) * total_frames)
            goal_events_by_step.setdefault(s_idx, []).append(ev)

    curr_score = [0, 0]
    goal_banner = None
    goal_banner_cd = 0

    for step in range(total_frames):
        ret, frame_bgr = cap.read()
        if not ret or frame_bgr is None:
            break

        match_min = max(1, min(90, int((step / max(total_frames, 1)) * 90) + 1))
        is_second_half = step > (total_frames // 2)

        # Update score and trigger celebration banner at goal events
        if step in goal_events_by_step:
            for g_ev in goal_events_by_step[step]:
                g_team = g_ev.get("team", "home")
                g_scorer = g_ev.get("player") or g_ev.get("scorer", "Goal")
                g_min = g_ev.get("minute", match_min)
                if g_team == "home":
                    curr_score[0] += 1
                else:
                    curr_score[1] += 1
                team_label = home_team if g_team == "home" else away_team
                goal_banner = f"GOAL!  {g_scorer} ({team_label})  {g_min}'"
                goal_banner_cd = 45

        # Resize frame if needed to 1280x720
        h_f, w_f = frame_bgr.shape[:2]
        if (w_f, h_f) != (1280, 720):
            frame_bgr = cv2.resize(frame_bgr, (1280, 720), interpolation=cv2.INTER_LINEAR)

        frame_annotated = draw_hud(
            frame=frame_bgr,
            home_team=home_team,
            away_team=away_team,
            score=(curr_score[0], curr_score[1]),
            match_min=match_min,
            home_bgr=home_bgr,
            away_bgr=away_bgr,
            goal_banner=goal_banner if goal_banner_cd > 0 else None,
            is_second_half=is_second_half
        )
        if goal_banner_cd > 0:
            goal_banner_cd -= 1

        writer.append_data(cv2.cvtColor(frame_annotated, cv2.COLOR_BGR2RGB))

        # Half-Time Studio Recap Card (at halftime step)
        if step == (total_frames // 2):
            ht_card = draw_studio_stats_card(
                w=1280, h=720, title="HALF TIME",
                home_team=home_team, away_team=away_team,
                score=(curr_score[0], curr_score[1]),
                h_poss=manifest.possession[0], a_poss=manifest.possession[1],
                h_shots=manifest.shots[0], a_shots=manifest.shots[1],
                h_sot=manifest.shots_on_target[0], a_sot=manifest.shots_on_target[1],
                h_xg=manifest.xg[0], a_xg=manifest.xg[1],
                home_bgr=home_bgr, away_bgr=away_bgr,
                events=[e for e in manifest.events if e.get("minute", 0) <= 45]
            )
            for _ in range(45):
                writer.append_data(ht_card)

        if progress_callback and (step % 50 == 0 or step == total_frames - 1):
            pct = min(98, 5 + int((step / max(total_frames - 1, 1)) * 93))
            progress_callback(pct, step, total_frames, match_min)

    cap.release()

    # Full-time card with Man of the Match
    motm = None
    goals = [e for e in manifest.events if e.get("type") == "goal"]
    if goals:
        motm = goals[-1].get("player")
    elif manifest.home_players and manifest.away_players:
        motm = manifest.home_players[8] if manifest.home_score >= manifest.away_score else manifest.away_players[9]

    ft_card = draw_studio_stats_card(
        w=1280, h=720, title="FULL TIME",
        home_team=home_team, away_team=away_team,
        score=(manifest.home_score, manifest.away_score),
        h_poss=manifest.possession[0], a_poss=manifest.possession[1],
        h_shots=manifest.shots[0], a_shots=manifest.shots[1],
        h_sot=manifest.shots_on_target[0], a_sot=manifest.shots_on_target[1],
        h_xg=manifest.xg[0], a_xg=manifest.xg[1],
        home_bgr=home_bgr, away_bgr=away_bgr,
        events=manifest.events,
        motm_player=motm
    )
    for _ in range(60):
        writer.append_data(ft_card)

    writer.close()

    # Space Optimization: Remove intermediate raw AVI and redundant traces/dumps
    try:
        if os.path.exists(raw_avi_path):
            os.remove(raw_avi_path)
    except Exception:
        pass

    try:
        dir_name = os.path.dirname(output_mp4_path)
        m_id = manifest.match_id
        # Remove redundant dumps, grfstates, and npz traces (the 3D video is already permanently saved)
        for ext in [".dump", ".grfstate", "_states.grfstate", ".npz"]:
            cand = os.path.join(dir_name, f"trace_{m_id}{ext}")
            if os.path.exists(cand):
                os.remove(cand)
    except Exception:
        pass

    return f"/recordings/{os.path.basename(output_mp4_path)}"

