"""Footy broadcast typography and rounded overlays on native gameplay frames."""

import numpy as np
from PIL import Image, ImageDraw
from logic.clay_broadcast import font, contrast_ink
from logic.team_identity import club_colour


def overlay(
    frame,
    home_team,
    away_team,
    score,
    match_min,
    home_bgr,
    away_bgr,
    goal_banner=None,
    is_second_half=False,
    match_seconds=None,
):
    h, w = frame.shape[:2]
    scale = min(w / 1280, h / 720)

    def paste(image, x, y):
        pixels = np.asarray(image)
        ih, iw = pixels.shape[:2]
        if x < 0 or y < 0 or x + iw > w or y + ih > h:
            return
        alpha = pixels[:, :, 3:4].astype(float) / 255
        region = frame[y : y + ih, x : x + iw]
        region[:] = (region * (1 - alpha) + pixels[:, :, :3][:, :, ::-1] * alpha).astype(np.uint8)

    image = Image.new("RGBA", (round(450 * scale), round(56 * scale)))
    draw = ImageDraw.Draw(image)

    def rect(bounds, fill, radius=16):
        draw.rounded_rectangle(tuple(round(v * scale) for v in bounds), radius=round(radius * scale), fill=fill)

    def text(x, y, value, size, colour, heading=True, anchor="mm"):
        draw.text(
            (x * scale, y * scale),
            str(value),
            font=font(max(1, round(size * scale)), heading),
            fill=colour,
            anchor=anchor,
        )

    rect((0, 0, 450, 56), "#0C1D36")
    for x, name, bgr in ((4, home_team, home_bgr), (206, away_team, away_bgr)):
        colour = club_colour(name, "#%02x%02x%02x" % tuple(reversed(bgr)))
        rect((x, 4, x + 82, 52), colour, 12)
        words = name.split()
        label = (
            "".join(word[0] for word in words[:3])
            if len(words) >= 3
            else (words[0][0] + words[1][:2] if len(words) == 2 else name[:3])
        )
        text(x + 41, 28, label.upper(), 20, contrast_ink(colour))
    text(146, 28, f"{score[0]}  –  {score[1]}", 25, "#F8EBD5")
    seconds = max(0, int(match_seconds)) if match_seconds is not None else match_min * 60
    text(370, 20, f"{seconds // 60:02d}:{seconds % 60:02d}", 23, "#8FE3EC")
    text(370, 43, "SECOND HALF" if is_second_half else "FIRST HALF", 10, "#F8EBD5", False)
    paste(image, round(24 * scale), round(20 * scale))
    if goal_banner:
        image = Image.new("RGBA", (round(650 * scale), round(72 * scale)))
        draw = ImageDraw.Draw(image)
        rect((0, 0, 650, 72), "#0C1D36", 20)
        rect((6, 6, 108, 66), "#F85525", 14)
        text(57, 36, "GOAL", 24, "#FFFFFF")
        value = str(goal_banner)
        if value.startswith("GOAL!"):
            value = value[5:].strip()
        f = font(max(1, round(21 * scale)), True)
        while draw.textlength(value, font=f) > 510 * scale and len(value) > 1:
            value = value[:-2] + "…"
        draw.text((128 * scale, 36 * scale), value, font=f, fill="#F8EBD5", anchor="lm")
        paste(image, round((w - image.width) / 2), h - round(96 * scale))
    return frame
