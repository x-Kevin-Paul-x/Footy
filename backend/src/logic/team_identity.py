"""Club brand colours for presentation; these do not select native kit textures."""

import hashlib
import re

CLUB_COLOURS = {
    "arsenal": "#EF0107",
    "aston villa": "#670E36",
    "bournemouth": "#DA291C",
    "brentford": "#E30613",
    "brighton": "#0057B8",
    "burnley": "#6C1D45",
    "chelsea": "#034694",
    "crystal palace": "#1B458F",
    "everton": "#003399",
    "fulham": "#111111",
    "leeds united": "#FFCD00",
    "leicester city": "#003090",
    "liverpool": "#C8102E",
    "manchester city": "#6CABDD",
    "manchester united": "#DA291C",
    "newcastle united": "#241F20",
    "nottingham forest": "#DD0000",
    "southampton": "#D71920",
    "sunderland": "#EB172B",
    "tottenham hotspur": "#132257",
    "west ham united": "#7A263A",
    "wolverhampton wanderers": "#FDB913",
    "ipswich town": "#0033A0",
    "sheffield united": "#EE2737",
}
ALIASES = {
    "afc bournemouth": "bournemouth",
    "brighton and hove albion": "brighton",
    "brighton hove albion": "brighton",
    "wolves": "wolverhampton wanderers",
    "spurs": "tottenham hotspur",
    "tottenham": "tottenham hotspur",
    "west ham": "west ham united",
    "newcastle": "newcastle united",
    "man city": "manchester city",
    "man utd": "manchester united",
    "man united": "manchester united",
    "leeds": "leeds united",
}
PALETTE = [
    "#e63946",
    "#2196f3",
    "#4caf50",
    "#ff9800",
    "#9c27b0",
    "#00bcd4",
    "#f44336",
    "#3f51b5",
    "#8bc34a",
    "#ff5722",
    "#009688",
    "#673ab7",
    "#ffc107",
    "#607d8b",
    "#e91e63",
]


def club_colour(name, fallback=None):
    raw = str(getattr(name, "name", name))
    key = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", raw.lower())).strip()
    key = re.sub(r"\s+f\s*c$", "", key).strip()
    key = ALIASES.get(key, key)
    return (
        CLUB_COLOURS.get(key) or fallback or PALETTE[int(hashlib.md5(raw.encode()).hexdigest()[:4], 16) % len(PALETTE)]
    )
