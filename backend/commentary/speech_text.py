"""Score meaning and spoken numbers, independent of model-generated prose."""

import re
from dataclasses import dataclass


def parse_score(value):
    if isinstance(value, str):
        if not re.fullmatch(r"\d+\s*[-–]\s*\d+", value):
            raise ValueError("Invalid home-away score")
        value = re.split(r"[-–]", value)
    if len(value) != 2 or any(isinstance(n, bool) or int(n) != float(n) or int(n) < 0 for n in value):
        raise ValueError("Invalid home-away score")
    return tuple(int(n) for n in value)


def number_word(value):
    value = int(value)
    small = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
             "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
             "eighteen", "nineteen")
    if 0 <= value < 20:
        return small[value]
    if value < 100:
        tens = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
        return tens[value // 10] + ("-" + small[value % 10] if value % 10 else "")
    return str(value)


def format_score_speech(score, home=None, away=None):
    h, a = parse_score(score)
    if home is not None and away is not None:
        return f"{home} {number_word(h) if h else 'nil'}, {away} {number_word(a) if a else 'nil'}"
    if h == a:
        return "nil-nil" if h == 0 else f"{number_word(h)}-all"
    return f"{number_word(h) if h else 'nil'}-{number_word(a) if a else 'nil'}"


@dataclass(frozen=True)
class GoalTransition:
    before: tuple
    after: tuple
    side: int
    category: str
    minute: int

    @property
    def late(self):
        return self.minute >= 86


def classify_goal(before, after, minute=0):
    before, after = parse_score(before), parse_score(after)
    delta = tuple(b - a for a, b in zip(before, after))
    if delta not in ((1, 0), (0, 1)):
        raise ValueError("A canonical goal must increment exactly one team's score")
    side = delta.index(1)
    other = 1 - side
    old_margin, new_margin = before[side] - before[other], after[side] - after[other]
    if new_margin == 0:
        category = "equaliser"
    elif new_margin < 0:
        category = "deficit_reducer"
    elif sum(before) == 0:
        category = "opener"
    elif old_margin <= 0:
        category = "go_ahead"
    else:
        category = "advantage_extended"
    return GoalTransition(before, after, side, category, int(minute))
