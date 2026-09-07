"""Deterministic presentation statistics derived from immutable trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from logic.grf_trajectory import MatchTrajectory
from .schema import StatsSnapshot, freeze_event

_PASS_ACTIONS = frozenset((9, 10, 11))


@dataclass
class _ActivePass:
    team: int
    passer: int
    step: int


class StatsSnapshotReducer:
    """Replays Footy's existing pass-accounting semantics without mutation.

    Trajectories retain post-step ownership, so the reducer uses the preceding
    recorded ownership for the same pre-step ownership consulted by
    ``GRFMatchExecutor.step``. The unrecorded environment-reset state before
    step zero cannot start a canonical pass and is deliberately not guessed.
    """

    @classmethod
    def at_step(cls, trajectory: MatchTrajectory, source_step: int) -> StatsSnapshot:
        if trajectory.total_steps <= 0:
            raise ValueError("trajectory has no steps")
        if trajectory.ball_owned_team is None or trajectory.ball_owned_player is None:
            raise ValueError("StatsSnapshot requires trajectory V2 ownership arrays")

        cutoff = max(0, min(int(source_step), trajectory.total_steps - 1))
        events = cls._events_through(trajectory.manifest.events, cutoff)
        shots, shots_on_target, xg = cls._shot_totals(events)
        possession = cls._possession_through(trajectory, cutoff)
        passes_attempted, passes_completed = cls._passes_through(trajectory, cutoff)
        snapshot = StatsSnapshot(
            source_step=cutoff,
            score=(int(trajectory.scores[cutoff, 0]), int(trajectory.scores[cutoff, 1])),
            possession=possession,
            shots=shots,
            shots_on_target=shots_on_target,
            xg=xg,
            passes_attempted=passes_attempted,
            passes_completed=passes_completed,
            events=tuple(freeze_event(event) for event in events),
        )
        if cutoff == trajectory.total_steps - 1:
            cls.assert_matches_final_manifest(snapshot, trajectory)
        return snapshot

    @staticmethod
    def _events_through(events: Iterable[Dict[str, Any]], cutoff: int) -> List[Dict[str, Any]]:
        # Canonical Footy events have a simulation step. Events lacking one are
        # legacy/unpositioned metadata and must not be guessed into a snapshot.
        return [dict(event) for event in events if event.get("step") is not None and int(event["step"]) <= cutoff]

    @staticmethod
    def _shot_totals(events: Iterable[Dict[str, Any]]) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[float, float]]:
        shots = [0, 0]
        on_target = [0, 0]
        xg = [0.0, 0.0]
        for event in events:
            if str(event.get("type", "")).lower() != "shot":
                continue
            team = 0 if event.get("team") == "home" else 1 if event.get("team") == "away" else None
            if team is None:
                continue
            shots[team] += 1
            on_target[team] += int(bool(event.get("on_target", False)))
            xg[team] += float(event.get("xg", 0.0))
        return (tuple(shots), tuple(on_target), (round(xg[0], 2), round(xg[1], 2)))

    @staticmethod
    def _possession_through(trajectory: MatchTrajectory, cutoff: int) -> Tuple[float, float]:
        ownership = trajectory.ball_owned_team[:cutoff + 1]
        home = int((ownership == 0).sum())
        away = int((ownership == 1).sum())
        total = max(1, home + away)
        home_pct = round((home / total) * 100.0, 1)
        return (home_pct, round(100.0 - home_pct, 1))

    @classmethod
    def _passes_through(cls, trajectory: MatchTrajectory, cutoff: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        attempted = [0, 0]
        completed = [0, 0]
        active: Optional[_ActivePass] = None
        for step in range(cutoff + 1):
            owner = int(trajectory.ball_owned_team[step])
            player = int(trajectory.ball_owned_player[step])
            if step == 0:
                continue
            previous_owner = int(trajectory.ball_owned_team[step - 1])
            previous_player = int(trajectory.ball_owned_player[step - 1])
            action_index = previous_player - 1
            if active is None and previous_owner in (0, 1) and previous_player >= 1 and action_index < 10:
                offset = action_index if previous_owner == 0 else 10 + action_index
                if int(trajectory.actions[step, offset]) in _PASS_ACTIONS:
                    attempted[previous_owner] += 1
                    active = _ActivePass(team=previous_owner, passer=previous_player, step=step)
            if active is not None:
                if owner == active.team:
                    if player != active.passer and player >= 0:
                        completed[active.team] += 1
                        active = None
                elif owner != -1:
                    active = None
                elif step - active.step > 30:
                    active = None
        return (tuple(attempted), tuple(completed))

    @staticmethod
    def assert_matches_final_manifest(snapshot: StatsSnapshot, trajectory: MatchTrajectory) -> None:
        """Fail loudly if a final presentation snapshot diverges from canon."""
        manifest = trajectory.manifest
        expected = {
            "score": tuple(manifest.score), "possession": tuple(manifest.possession),
            "shots": tuple(manifest.shots), "shots_on_target": tuple(manifest.shots_on_target),
            "xg": tuple(manifest.xg), "passes_attempted": tuple(manifest.passes_attempted),
            "passes_completed": tuple(manifest.passes_completed),
        }
        actual = {
            "score": snapshot.score, "possession": snapshot.possession,
            "shots": snapshot.shots, "shots_on_target": snapshot.shots_on_target,
            "xg": snapshot.xg, "passes_attempted": snapshot.passes_attempted,
            "passes_completed": snapshot.passes_completed,
        }
        if actual != expected:
            raise ValueError(f"final StatsSnapshot diverges from canonical manifest: expected={expected}, actual={actual}")
