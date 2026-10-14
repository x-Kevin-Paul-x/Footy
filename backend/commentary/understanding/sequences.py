"""
Phase 2: Sequence Builder.
Groups atomic enriched events into coherent football sequences (attacks, buildup, goals).
"""

from typing import List, Dict, Any, Optional
from backend.commentary.schemas import EnrichedEvent, FootballSequence


class SequenceBuilder:
    """Builds narrative football sequences from chronological events."""

    def __init__(self, home_team: str = "Burnley", away_team: str = "Bournemouth"):
        self.home_team = home_team
        self.away_team = away_team

    def build_sequences(self, events: List[EnrichedEvent]) -> List[FootballSequence]:
        sequences: List[FootballSequence] = []
        if not events:
            return sequences

        home_score = 0
        away_score = 0
        current_score = f"{home_score}-{away_score}"

        current_events: List[EnrichedEvent] = []
        seq_idx = 0

        def event_narrative(e: EnrichedEvent) -> str:
            """Turn an EnrichedEvent into a factual narrative line."""
            if e.type == "GOAL":
                return f"GOAL! {e.player} scores for {e.team}! ({e.facts.get('score', '')})"
            elif e.type == "SHOT":
                on_tgt = "on target" if e.facts.get("on_target") else "off target"
                return f"{e.player} takes a shot {on_tgt} (xG: {e.facts.get('xg', 0.0):.2f})"
            elif e.type == "HIT_POST":
                return f"{e.player}'s effort strikes the woodwork!"
            elif e.type == "BOX_ENTRY":
                return f"{e.team} penetrate the penalty area"
            elif e.type == "PROGRESSIVE_PASS":
                passer = e.facts.get("passer", e.player)
                rec = e.facts.get("receiver", "a teammate")
                return f"{passer} plays a progressive ball forward to {rec}"
            elif e.type == "PASS":
                passer = e.facts.get("passer", e.player)
                rec = e.facts.get("receiver", "a teammate")
                return f"{passer} passes to {rec}"
            elif e.type == "TURNOVER":
                return f"Turnover: {e.player} recovers possession for {e.team}"
            elif e.type == "POSSESSION_START":
                return f"{e.player} gains control for {e.team}"
            elif e.type == "HALFTIME":
                return f"Whistle blows for half-time ({e.facts.get('score', '')})"
            elif e.type == "FULLTIME":
                return f"Full-time whistle! Final score: {e.facts.get('score', '')}"
            return f"{e.team} in possession with {e.player}"

        def flush_sequence(seq_evts: List[EnrichedEvent], outcome: str) -> Optional[FootballSequence]:
            nonlocal seq_idx, current_score, home_score, away_score
            if not seq_evts:
                return None

            seq_idx += 1
            team = seq_evts[0].team
            start_ms = seq_evts[0].presentation_ms
            end_ms = seq_evts[-1].presentation_ms
            # Ensure at least 1.5s window
            if end_ms - start_ms < 1500:
                end_ms = start_ms + 2500

            start_step = seq_evts[0].step
            end_step = seq_evts[-1].step

            max_imp = max(e.importance for e in seq_evts)
            max_dgr = max(e.danger for e in seq_evts)

            # Sequence classification
            types = {e.type for e in seq_evts}
            if "GOAL" in types:
                seq_type = "GOAL_SEQUENCE"
            elif "SHOT" in types or "HIT_POST" in types:
                seq_type = "SHOT_SEQUENCE"
            elif "BOX_ENTRY" in types or max_dgr >= 0.70:
                seq_type = "DANGEROUS_ATTACK"
            elif "PROGRESSIVE_PASS" in types or max_dgr >= 0.45:
                seq_type = "PROGRESSIVE_ATTACK"
            elif "TURNOVER" in types and max_dgr >= 0.40:
                seq_type = "COUNTER_ATTACK"
            else:
                seq_type = "BUILDUP"

            score_before = current_score
            # Update score if goal occurred
            for e in seq_evts:
                if e.type == "GOAL":
                    sc = e.facts.get("score", "")
                    if "-" in sc:
                        current_score = sc
                        parts = sc.split("-")
                        try:
                            home_score = int(parts[0])
                            away_score = int(parts[1])
                        except Exception:
                            pass
            score_after = current_score

            narratives = [event_narrative(e) for e in seq_evts]
            fact_ids = [e.event_id for e in seq_evts]

            return FootballSequence(
                sequence_id=f"seq_{seq_idx:04d}",
                type=seq_type,
                team=team,
                start_step=start_step,
                end_step=end_step,
                start_ms=start_ms,
                end_ms=end_ms,
                importance=round(max_imp, 3),
                danger=round(max_dgr, 3),
                events=narratives,
                fact_ids=fact_ids,
                outcome=outcome,
                score_before=score_before,
                score_after=score_after,
            )

        for e in events:
            # Stoppage milestones are their own immediate sequence
            if e.type in ("HALFTIME", "FULLTIME"):
                if current_events:
                    seq = flush_sequence(current_events, "STOPPAGE")
                    if seq:
                        sequences.append(seq)
                    current_events = []
                seq = flush_sequence([e], e.type)
                if seq:
                    sequences.append(seq)
                continue

            # Goal ends sequence immediately
            if e.type == "GOAL":
                current_events.append(e)
                seq = flush_sequence(current_events, "GOAL")
                if seq:
                    sequences.append(seq)
                current_events = []
                continue

            # Shot or hit post completes the attacking sequence
            if e.type in ("SHOT", "HIT_POST"):
                current_events.append(e)
                # Next event might be goal or rebound or turnover
                continue

            # Team turnover splits possession into a new sequence
            if current_events and e.type == "TURNOVER":
                # Flush previous sequence
                seq = flush_sequence(current_events, "TURNOVER")
                if seq:
                    sequences.append(seq)
                current_events = [e]
                continue

            # Time gap split (> 12 seconds in video)
            if current_events and (e.presentation_ms - current_events[-1].presentation_ms > 12000):
                seq = flush_sequence(current_events, "BUILDUP")
                if seq:
                    sequences.append(seq)
                current_events = [e]
                continue

            current_events.append(e)

        if current_events:
            seq = flush_sequence(current_events, "IN_PLAY")
            if seq:
                sequences.append(seq)

        return sequences
