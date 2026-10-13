"""Scalable broadcast cards using Footy's Outfit/Inter fonts and clay theme."""

from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from logic.team_identity import club_colour


def contrast_ink(colour):
    rgb = tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return "#FFFFFF" if sum(a * b for a, b in zip(rgb, (0.299, 0.587, 0.114))) < 145 else "#06101E"


@lru_cache(maxsize=128)
def font(size, heading=False):
    path = Path(__file__).with_name("broadcast_fonts") / ("Outfit.ttf" if heading else "Inter.ttf")
    result = ImageFont.truetype(str(path), size)
    axes = result.get_variation_axes()
    result.set_variation_by_axes([700 if b"Weight" in axis["name"] else axis["default"] for axis in axes])
    return result


class Card:
    def __init__(self, w, h, theme="dark"):
        self.w, self.h = w, h
        self.s = min(w / 1280, h / 720)
        self.ox, self.oy = (w - 1280 * self.s) / 2, (h - 720 * self.s) / 2
        self.light = theme == "light"
        self.bg, self.panel, self.ink, self.accent = (
            ("#FAA968", "#F6DCAC", "#01204E", "#028391") if self.light else ("#06101E", "#0C1D36", "#F8EBD5", "#8FE3EC")
        )
        self.image = Image.new("RGB", (w, h), self.bg)

    def box(self, bounds, fill=None, radius=24):
        x1, y1, x2, y2 = bounds
        rect = tuple(round(v * self.s + (self.ox if i % 2 == 0 else self.oy)) for i, v in enumerate(bounds))
        shadow = Image.new("RGBA", self.image.size)
        ImageDraw.Draw(shadow).rounded_rectangle(
            (rect[0], rect[1] + int(7 * self.s), rect[2], rect[3] + int(7 * self.s)),
            radius * self.s,
            fill=(0, 0, 0, 65),
        )
        self.image.paste(
            Image.alpha_composite(
                self.image.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(9 * self.s))
            ).convert("RGB")
        )
        draw = ImageDraw.Draw(self.image)
        draw.rounded_rectangle(
            rect,
            radius * self.s,
            fill=fill or self.panel,
            outline="#FFFFFF" if self.light else "#23405B",
            width=max(1, round(self.s)),
        )
        draw.line(
            (rect[0] + radius * self.s, rect[1] + 2 * self.s, rect[2] - radius * self.s, rect[1] + 2 * self.s),
            fill="#FFEBC9" if self.light else "#36516B",
            width=max(1, round(self.s)),
        )

    def text(self, xy, value, size=22, colour=None, heading=False, max_width=None, anchor="lt"):
        draw = ImageDraw.Draw(self.image)
        value = str(value)
        f = font(max(1, round(size * self.s)), heading)
        if max_width:
            while value and draw.textlength(value, font=f) > max_width * self.s:
                value = value[:-2].rstrip() + "…" if not value.endswith("…") else value[:-2] + "…"
                if value == "…":
                    break
        draw.text(
            (xy[0] * self.s + self.ox, xy[1] * self.s + self.oy), value, font=f, fill=colour or self.ink, anchor=anchor
        )

    def output(self):
        return np.asarray(self.image)[:, :, ::-1].copy()


def pre_match(
    w,
    h,
    home_team,
    away_team,
    home_players,
    away_players,
    home_formation,
    away_formation,
    home_bgr,
    away_bgr,
    home_roster=None,
    away_roster=None,
    theme="dark",
):
    c = Card(w, h, theme)
    c.text((48, 30), "FOOTY / MATCHDAY", 20, c.accent, True)
    c.text((48, 64), "The starting line-ups", 38, heading=True)
    c.text((1232, 42), "KICK-OFF", 18, c.accent, anchor="rt")
    for x, team, players, formation, bgr, roster in (
        (48, home_team, home_players, home_formation, home_bgr, home_roster),
        (664, away_team, away_players, away_formation, away_bgr, away_roster),
    ):
        c.box((x, 130, x + 568, 675))
        colour = club_colour(team, "#%02x%02x%02x" % tuple(reversed(bgr)))
        c.box((x + 16, 146, x + 552, 220), colour, 18)
        ink = contrast_ink(colour)
        c.text((x + 34, 169), team, 28, ink, True, max_width=360)
        c.text((x + 530, 178), formation, 18, ink, anchor="rt")
        c.text((x + 34, 237), "STARTING XI", 16, c.accent)
        for i, name in enumerate((players or [])[:11]):
            record = (roster or [])[i] if i < len(roster or []) else {}
            number = record.get("jersey_number")
            c.text((x + 36, 274 + i * 33), number if number is not None else "—", 19, c.accent)
            c.text((x + 86, 274 + i * 33), name, 19, max_width=390)
            if record.get("position") == "GK":
                c.text((x + 515, 278 + i * 33), "GK", 13, c.accent, anchor="rt")
    return c.output()


def stats(
    w,
    h,
    title,
    home_team,
    away_team,
    score,
    h_poss,
    a_poss,
    h_shots,
    a_shots,
    h_sot,
    a_sot,
    h_xg,
    a_xg,
    home_bgr,
    away_bgr,
    events,
    motm_player,
    theme="dark",
):
    c = Card(w, h, theme)
    c.text((48, 30), "FOOTY / MATCHDAY", 20, c.accent, True)
    c.text((48, 65), title.title(), 38, heading=True)
    for x, team, bgr in ((48, home_team, home_bgr), (824, away_team, away_bgr)):
        colour = club_colour(team, "#%02x%02x%02x" % tuple(reversed(bgr)))
        c.box((x, 134, x + 408, 234), colour)
        c.text((x + 24, 170), team, 28, contrast_ink(colour), True, max_width=360)
    c.box((480, 134, 800, 234))
    c.text((640, 156), f"{score[0]}  –  {score[1]}", 48, heading=True, anchor="mt")
    rows = [
        (
            "Possession",
            f"{h_poss:.1f}%" if h_poss is not None else "Untracked",
            f"{a_poss:.1f}%" if a_poss is not None else "Untracked",
        ),
        ("Total shots", str(h_shots), str(a_shots)),
        ("Shots on target", str(h_sot), str(a_sot)),
        ("Expected goals", f"{h_xg:.2f}", f"{a_xg:.2f}"),
    ]
    for i, (label, left, right) in enumerate(rows):
        y = 260 + i * 66
        c.box((48, y, 1232, y + 54), radius=18)
        c.text((80, y + 14), left, 22)
        c.text((640, y + 15), label, 20, c.accent, anchor="mt")
        c.text((1200, y + 14), right, 22, anchor="rt")
    c.box((48, 542, 790, 674))
    c.text((72, 558), "GOAL TIMELINE", 15, c.accent)
    goals = [e for e in (events or []) if e.get("type") == "goal"]
    for i, event in enumerate(goals[:3]):
        c.text(
            (72, 587 + i * 24),
            f"{event.get('minute', '—')}'  {event.get('player', 'Unknown')} · {event.get('team', '')}",
            17,
            max_width=690,
        )
    if not goals:
        c.text((72, 594), "Goal details unavailable" if sum(score) else "No goals yet", 20)
    c.box((814, 542, 1232, 674))
    c.text(
        (838, 559), "PLAYER OF THE MATCH" if motm_player and title.upper() == "FULL TIME" else "MATCHDAY", 15, c.accent
    )
    c.text(
        (838, 597),
        motm_player if motm_player and title.upper() == "FULL TIME" else "Every moment matters.",
        23,
        heading=True,
        max_width=365,
    )
    return c.output()
