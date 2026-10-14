"""Event-driven camera choices; reads recorded events without advancing physics."""

PRESETS = {"wide": 1, "bird": 2, "tele": 3}


class CameraDirector:
    def __init__(self, manifest, preset="wide"):
        if preset not in (*PRESETS, "director"):
            raise ValueError("Unknown replay camera")
        self.manifest = manifest
        self.preset = preset
        self.goals = [e for e in manifest.events if e.get("type") == "goal" and e.get("step") is not None]

    def at_step(self, step):
        if self.preset != "director":
            return PRESETS[self.preset], -1, -1, 1.0
        for goal in reversed(self.goals):
            age = step - int(goal["step"])
            if 0 <= age < 30:
                team = 0 if goal.get("team") == "home" else 1
                players = self.manifest.home_players if team == 0 else self.manifest.away_players
                scorer = goal.get("player") or goal.get("scorer")
                if scorer not in players:
                    continue
                # Ease in and out over half a simulation second. No camera cut
                # and no inferred scorer when historical attribution is absent.
                bias = min(1.0, age / 5.0, (30 - age) / 5.0)
                bias = bias * bias * (3 - 2 * bias)
                return 4, team, players.index(scorer), bias
        return 1, -1, -1, 1.0
