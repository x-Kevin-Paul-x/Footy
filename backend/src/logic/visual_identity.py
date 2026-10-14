"""Persistent player cosmetics and match-frozen club kit choices."""

import hashlib
import json
import os
from pathlib import Path
from filelock import FileLock
from logic.team_identity import club_colour

HAIR_STYLES = ("bald", "short01", "short02", "medium01", "medium02", "long01", "long02")
HAIR_COLOURS = ("black", "brown", "darkblonde", "blonde", "red")


def appearance_for_player(player_id, name):
    if player_id is None:
        return None
    from config import DATA_DIR

    path = DATA_DIR / "player_appearances.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    key = f"{player_id}:{name}"
    with FileLock(str(path.with_suffix(".lock"))):
        data = json.loads(path.read_text()) if path.exists() else {}
        if key not in data:
            digest = hashlib.sha256(key.encode()).digest()
            data[key] = {
                "skin": 1 + digest[0] % 4,
                "hair": HAIR_STYLES[digest[1] % len(HAIR_STYLES)],
                "hair_colour": HAIR_COLOURS[digest[2] % len(HAIR_COLOURS)],
            }
            pending = path.with_suffix(".json.tmp")
            pending.write_text(json.dumps(data, sort_keys=True))
            os.replace(pending, path)
        return dict(data[key])


def colour_distance(a, b):
    left = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    right = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return sum((x - y) ** 2 for x, y in zip(left, right)) ** 0.5


def kit_definition(team):
    primary = club_colour(team)
    name = team.lower()
    secondary = "#8FCBE5" if "burnley" in name or "villa" in name else "#111111" if "bournemouth" in name else "#FFFFFF"
    return {
        "home": {
            "shirt": primary,
            "secondary": secondary,
            "shorts": secondary,
            "socks": primary,
            "pattern": "stripes" if "bournemouth" in name else "plain",
        },
        "away": {"shirt": "#F5F1E8", "secondary": primary, "shorts": primary, "socks": "#F5F1E8", "pattern": "plain"},
    }


def freeze_visual_identity(home_team, away_team, home_roster, away_roster):
    home = kit_definition(home_team)["home"]
    away = kit_definition(away_team)["home"]
    selection = "home"
    if colour_distance(home["shirt"], away["shirt"]) < 100:
        away = kit_definition(away_team)["away"]
        selection = "away"
        if colour_distance(home["shirt"], away["shirt"]) < 100:
            away = dict(away, shirt="#132257", socks="#132257")
    candidates = ("#1BB55C", "#F4D35E", "#E76BA9", "#773C9B", "#35B6ED")
    used = [home["shirt"], away["shirt"]]
    keepers = []
    for _ in range(2):
        colour = max(candidates, key=lambda c: min(colour_distance(c, u) for u in used))
        keepers.append({"shirt": colour, "secondary": "#111111", "shorts": colour, "socks": colour, "pattern": "plain"})
        used.append(colour)
    return {
        "version": 1,
        "home": {"kit": home, "selected": "home", "goalkeeper": keepers[0], "roster": home_roster},
        "away": {"kit": away, "selected": selection, "goalkeeper": keepers[1], "roster": away_roster},
    }
