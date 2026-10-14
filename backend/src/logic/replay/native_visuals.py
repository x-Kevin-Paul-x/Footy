"""Apply match-frozen materials and cameras through Footy's optional native bindings."""

import sys
from pathlib import Path


def enable_visual_runtime():
    root = Path(__file__).resolve().parents[3] / "native/runtime/visual"
    if (root / "_gameplayfootball.so").is_file():
        sys.path.insert(0, str(root))
        return True
    return False


def generate_kit(path, kit, number=None):
    from PIL import Image, ImageDraw
    from logic.clay_broadcast import font, contrast_ink

    image = Image.new("RGB", (1024, 1024), "#000000")
    draw = ImageDraw.Draw(image)
    # Native full-body UV atlas: two shirt/short islands and two sock islands.
    for offset in (0, 512):
        draw.polygon(
            [
                (offset + 4, 6),
                (offset + 508, 6),
                (offset + 508, 147),
                (offset + 404, 178),
                (offset + 404, 420),
                (offset + 108, 420),
                (offset + 108, 178),
                (offset + 4, 147),
            ],
            fill=kit["shirt"],
        )
        if kit["pattern"] == "stripes":
            for x in range(offset + 108, offset + 404, 74):
                draw.rectangle((x, 6, x + 36, 419), fill=kit["secondary"])
        else:
            draw.rectangle((offset + 4, 6, offset + 108, 145), fill=kit["secondary"])
            draw.rectangle((offset + 404, 6, offset + 508, 145), fill=kit["secondary"])
        draw.rectangle((offset + 108, 420, offset + 403, 579), fill=kit["shorts"])
    for x in (6, 284):
        draw.rectangle((x, 586, x + 266, 735), fill=kit["socks"])
    if number is not None:
        draw.text(
            (768, 170),
            str(number),
            font=font(130, True),
            anchor="mt",
            fill=contrast_ink(kit["shirt"]),
            stroke_width=2,
            stroke_fill=kit["shirt"],
        )
        draw.text((365, 495), str(number), font=font(52, True), anchor="mt", fill=contrast_ink(kit["shorts"]))
    image.save(path)


def bind_visual_identity(env, manifest, directory):
    native = env.unwrapped._env._env
    if not hasattr(native, "set_visual_player"):
        return False
    from logic.visual_identity import freeze_visual_identity

    identity = manifest.visual_identity or freeze_visual_identity(
        manifest.home_team, manifest.away_team, manifest.home_roster, manifest.away_roster
    )
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for team, side in enumerate(("home", "away")):
        for index in range(11):
            roster = identity[side]["roster"]
            player = roster[index] if index < len(roster) else {}
            kit = identity[side]["goalkeeper"] if index == 0 else identity[side]["kit"]
            path = directory / f"{side}-{index}.bmp"
            generate_kit(path, kit, player.get("jersey_number"))
            appearance = player.get("appearance") or {}
            names = manifest.home_players if team == 0 else manifest.away_players
            name = names[index] if index < len(names) else player.get("name") or "Unknown player"
            native.set_visual_player(
                team,
                index,
                str(path.resolve()),
                appearance.get("skin", 0),
                appearance.get("hair", ""),
                appearance.get("hair_colour", "black"),
                name,
            )
    return True
