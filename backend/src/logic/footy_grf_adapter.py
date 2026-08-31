"""
Footy to Google Research Football (GRF) Adapter.
Bridges Footy managerial tactics, squad attributes, and player form
with physics-grounded 3D Multi-Agent Reinforcement Learning simulation.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
import numpy as np


# Standard Formation Anchor Coordinates on GRF Pitch: x in [-1.0, 1.0], y in [-0.42, 0.42]
FORMATION_COORDINATES: Dict[str, List[Tuple[float, float]]] = {
    "4-3-3": [
        (-0.95,  0.00),  # GK
        (-0.60,  0.30),  # LB
        (-0.70,  0.10),  # LCB
        (-0.70, -0.10),  # RCB
        (-0.60, -0.30),  # RB
        (-0.45,  0.00),  # CDM
        (-0.30,  0.18),  # LCM
        (-0.30, -0.18),  # RCM
        (-0.15,  0.28),  # LW
        (-0.10,  0.00),  # ST
        (-0.15, -0.28),  # RW
    ],
    "4-2-3-1": [
        (-0.95,  0.00),  # GK
        (-0.60,  0.30),  # LB
        (-0.70,  0.10),  # LCB
        (-0.70, -0.10),  # RCB
        (-0.60, -0.30),  # RB
        (-0.45,  0.15),  # LDM
        (-0.45, -0.15),  # RDM
        (-0.25,  0.00),  # CAM
        (-0.20,  0.28),  # LAM
        (-0.20, -0.28),  # RAM
        (-0.10,  0.00),  # ST
    ],
    "3-5-2": [
        (-0.95,  0.00),  # GK
        (-0.70,  0.22),  # LCB
        (-0.75,  0.00),  # CB
        (-0.70, -0.22),  # RCB
        (-0.40,  0.35),  # LWB
        (-0.40, -0.35),  # RWB
        (-0.45,  0.00),  # CDM
        (-0.30,  0.15),  # LCM
        (-0.30, -0.15),  # RCM
        (-0.12,  0.12),  # LS
        (-0.12, -0.12),  # RS
    ],
    "4-4-2": [
        (-0.95,  0.00),  # GK
        (-0.60,  0.30),  # LB
        (-0.70,  0.10),  # LCB
        (-0.70, -0.10),  # RCB
        (-0.60, -0.30),  # RB
        (-0.35,  0.32),  # LM
        (-0.35,  0.12),  # LCM
        (-0.35, -0.12),  # RCM
        (-0.35, -0.32),  # RM
        (-0.12,  0.12),  # LS
        (-0.12, -0.12),  # RS
    ],
    "5-3-2": [
        (-0.95,  0.00),  # GK
        (-0.65,  0.35),  # LWB
        (-0.72,  0.18),  # LCB
        (-0.75,  0.00),  # CB
        (-0.72, -0.18),  # RCB
        (-0.65, -0.35),  # RWB
        (-0.35,  0.18),  # LCM
        (-0.40,  0.00),  # CDM
        (-0.35, -0.18),  # RCM
        (-0.12,  0.12),  # LS
        (-0.12, -0.12),  # RS
    ],
    "3-4-3": [
        (-0.95,  0.00),  # GK
        (-0.70,  0.22),  # LCB
        (-0.75,  0.00),  # CB
        (-0.70, -0.22),  # RCB
        (-0.40,  0.32),  # LM
        (-0.40,  0.10),  # LCM
        (-0.40, -0.10),  # RCM
        (-0.40, -0.32),  # RM
        (-0.15,  0.28),  # LW
        (-0.10,  0.00),  # ST
        (-0.15, -0.28),  # RW
    ]
}


@dataclass
class GRFPlayerProfile:
    """
    Normalized physical & technical profile for a player in GRF simulation.
    Ratings range from 0 to 100, mapped to action execution and physics multipliers.
    """
    player_id: Optional[int] = None
    name: str = "Player"
    position: str = "CM"
    pace: float = 70.0
    shooting: float = 70.0
    passing: float = 70.0
    dribbling: float = 70.0
    defending: float = 70.0
    stamina: float = 70.0
    goalkeeping: float = 70.0
    form_factor: float = 1.0
    fitness_factor: float = 1.0

    @property
    def speed_multiplier(self) -> float:
        """Pace multiplier in [0.90, 1.10] applied to player movement."""
        effective_pace = self.pace * self.fitness_factor * self.form_factor
        return 0.90 + (min(100.0, max(40.0, effective_pace)) - 40.0) / 60.0 * 0.20

    @property
    def stamina_decay_rate(self) -> float:
        """Fatigue accumulation rate per action tick in [0.70, 1.30]. Higher stamina decays slower."""
        base_decay = 1.0 - ((self.stamina - 50.0) / 100.0) * 0.40
        return max(0.60, min(1.40, base_decay))

    @property
    def shot_quality_modifier(self) -> float:
        """Shooting precision and power multiplier in [0.80, 1.25]."""
        effective_shot = self.shooting * self.form_factor
        return 0.80 + (min(100.0, max(40.0, effective_shot)) - 40.0) / 60.0 * 0.45

    @property
    def pass_precision_variance(self) -> float:
        """Angular error variance in radians for passing [0.02, 0.12]. Higher passing -> lower error."""
        return max(0.02, 0.12 - (self.passing / 100.0) * 0.10)

    @property
    def tackle_success_prob(self) -> float:
        """Base probability of winning a tackle / interception [0.45, 0.85]."""
        return 0.45 + (min(100.0, max(40.0, self.defending)) - 40.0) / 60.0 * 0.40

    @property
    def gk_save_coverage(self) -> float:
        """Goalkeeper save angle coverage multiplier [0.75, 1.25]."""
        return 0.75 + (min(100.0, max(40.0, self.goalkeeping)) - 40.0) / 60.0 * 0.50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GRFTeamTactics:
    """Team formation, tactical style, and squad roster configuration for GRF."""
    team_name: str
    formation: str = "4-3-3"
    offensive_bias: float = 50.0  # 0 to 100
    defensive_bias: float = 50.0  # 0 to 100
    pressing_intensity: float = 50.0  # 0 to 100
    tempo: float = 50.0  # 0 to 100
    roster: List[GRFPlayerProfile] = field(default_factory=list)

    def get_formation_anchors(self, is_right_team: bool = False) -> List[Tuple[float, float]]:
        coords = FORMATION_COORDINATES.get(self.formation, FORMATION_COORDINATES["4-3-3"])
        if not is_right_team:
            return coords
        # 180° rotation for right team
        return [(-x, -y) for (x, y) in coords]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_name": self.team_name,
            "formation": self.formation,
            "offensive_bias": self.offensive_bias,
            "defensive_bias": self.defensive_bias,
            "pressing_intensity": self.pressing_intensity,
            "tempo": self.tempo,
            "roster": [p.to_dict() for p in self.roster],
        }


class FootyGRFAdapter:
    """
    Translation adapter converting Footy domain objects into GRF simulation inputs
    and parsing match trajectories back into Footy match results and database records.
    """

    @staticmethod
    def extract_player_profile(player: Any, assigned_pos: str = "CM") -> GRFPlayerProfile:
        """Extract attributes from a Footy player object (or dict) into GRFPlayerProfile."""
        if isinstance(player, dict):
            name = player.get("name", "Player")
            pos = player.get("position", assigned_pos)
            attrs = player.get("attributes", {})
            overall = float(player.get("potential", 70))
        else:
            name = getattr(player, "name", "Player")
            pos = getattr(player, "position", assigned_pos)
            attrs = getattr(player, "attributes", {})
            overall = float(getattr(player, "potential", 70))

        # Helper to query nested Footy attribute categories
        def get_attr_val(attr_name: str, default: float) -> float:
            if not attrs:
                return default
            for cat, vals in attrs.items():
                if isinstance(vals, dict) and attr_name in vals:
                    return float(vals[attr_name])
            return default

        pace = get_attr_val("pace", get_attr_val("acceleration", overall))
        shooting = get_attr_val("shooting", get_attr_val("finishing", overall))
        passing = get_attr_val("passing", get_attr_val("vision", overall))
        dribbling = get_attr_val("dribbling", get_attr_val("ball_control", overall))
        defending = get_attr_val("tackling", get_attr_val("defending", overall))
        stamina = get_attr_val("stamina", 75.0)
        gk = get_attr_val("goalkeeping", overall if pos == "GK" else 30.0)

        form = 1.0
        fitness = 1.0
        if not isinstance(player, dict):
            if hasattr(player, "get_form_rating") and callable(player.get_form_rating):
                form = float(player.get_form_rating())
            if hasattr(player, "stats") and isinstance(player.stats, dict):
                fitness = float(player.stats.get("fitness", 100)) / 100.0

        p_id = getattr(player, "id", None) if not isinstance(player, dict) else player.get("id")

        return GRFPlayerProfile(
            player_id=p_id,
            name=name,
            position=pos,
            pace=pace,
            shooting=shooting,
            passing=passing,
            dribbling=dribbling,
            defending=defending,
            stamina=stamina,
            goalkeeping=gk,
            form_factor=max(0.7, min(1.3, form)),
            fitness_factor=max(0.6, min(1.0, fitness)),
        )

    @classmethod
    def build_team_tactics(
        cls,
        team: Any,
        lineup: Optional[List[Any]] = None,
        positions: Optional[List[str]] = None,
        formation: Optional[str] = None
    ) -> GRFTeamTactics:
        """Build GRFTeamTactics from a Footy Team object or fallback name."""
        team_name = getattr(team, "name", str(team)) if team else "Team"
        manager = getattr(team, "manager", None) if team else None

        tactics_dict = getattr(manager, "tactics", {}) if manager else {}
        form = formation or getattr(manager, "formation", "4-3-3")
        if form not in FORMATION_COORDINATES:
            form = "4-3-3"

        off_bias = float(tactics_dict.get("offensive", 50.0))
        def_bias = float(tactics_dict.get("defensive", 50.0))
        press = float(tactics_dict.get("pressing", 50.0))
        tempo = float(tactics_dict.get("tempo", 50.0))

        # Extract player profiles for 11 starters
        roster_profiles = []
        raw_lineup = lineup or (getattr(team, "players", [])[:11] if hasattr(team, "players") else [])
        for idx in range(11):
            if idx < len(raw_lineup):
                p = raw_lineup[idx]
                pos = positions[idx] if positions and idx < len(positions) else ("GK" if idx == 0 else "CM")
                roster_profiles.append(cls.extract_player_profile(p, assigned_pos=pos))
            else:
                pos = "GK" if idx == 0 else "CM"
                roster_profiles.append(GRFPlayerProfile(name=f"{team_name} Player {idx+1}", position=pos))

        return GRFTeamTactics(
            team_name=team_name,
            formation=form,
            offensive_bias=off_bias,
            defensive_bias=def_bias,
            pressing_intensity=press,
            tempo=tempo,
            roster=roster_profiles
        )
