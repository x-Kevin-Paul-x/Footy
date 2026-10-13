"""Reserve decisive events first; optional speech yields to these deadlines."""
from backend.commentary.schemas import CommentarySlot
class SlotAllocator:
    def __init__(self, timeline, calibration=None): self.timeline = timeline
    def allocate_slots(self, events, sequences, context):
        slots = []
        goals = sorted([e for e in events if e.type == "GOAL"], key=lambda e:e.presentation_ms)
        def score_at(ms):
            eligible = [e for e in goals if e.presentation_ms <= ms]
            return eligible[-1].facts["score"] if eligible else "0-0"
        def add(start, end, kind, speaker="Ryan", event=None, summary="", priority=1, energy=.45):
            start, end = max(0, int(start)), min(self.timeline.total_duration_ms, int(end))
            if end-start < 600: return False
            conflicts = [s for s in slots if start < s.max_end_ms and end > s.start_ms]
            if any(s.priority >= priority for s in conflicts): return False
            for s in conflicts: slots.remove(s)
            ids = ["fact_0001", "fact_0002", "fact_0003"]
            if event:
                fid = context.event_to_fact_id.get(event.event_id)
                if fid and context.fact_available_ms.get(fid, 0) <= start: ids.append(fid)
            ids = [fid for fid in ids if fid in context.allowed_facts and context.fact_available_ms.get(fid, 0) <= start]
            score = score_at(start)
            h, a = map(int, score.split("-"))
            lead = f"Level at {score}" if h == a else f"{context.home_team if h > a else context.away_team} lead"
            slots.append(CommentarySlot(commentary_id="", start_ms=start, max_end_ms=end,
                window_seconds=(end-start)/1000, slot_type=kind, speaker=speaker, priority=priority,
                energy_target=energy, target_words=max(1, int((end-start)/1000*2)),
                match_minute=event.match_minute if event else self.timeline.pts_to_match_minute(start/1000),
                running_score=score, score_lead=lead, active_event_type=event.type if event else "INTRO",
                active_player=event.player if event else "", active_team=event.team if event else "",
                active_facts=event.facts if event else {}, in_play_summary=summary, allowed_fact_ids=ids))
            return True
        add(300, 5400, "stoppage", summary=f"Welcome to {context.venue or 'the ground'}. {context.home_team} against {context.away_team}; alongside Aiden.", priority=3)
        add(5600, 9200, "stoppage", "Aiden", summary="Both teams are underway. Settle into the match.", priority=2)
        for goal in goals:
            t = goal.presentation_ms
            upcoming = [e.presentation_ms for e in events if e.type in ("GOAL", "HALFTIME", "FULLTIME") and e.presentation_ms > t]
            deadline = min(upcoming or [self.timeline.total_duration_ms])
            end = min(t+4300, deadline-100)
            add(t, end, "goal_reaction", event=goal, priority=10, energy=.9)
            release = next((e for e in reversed(events) if e.type == "SHOT_RELEASE" and e.team == goal.team and e.player in ('', goal.player) and 0 < goal.step-e.step <= 60), None)
            if release:
                r = release.presentation_ms
                observed = [e for e in events if e.player == goal.player and e.type in ("CONTROL_IN_ATTACK","BOX_ENTRY","POSSESSION_START","PASS","PROGRESSIVE_PASS") and r-2000 <= e.presentation_ms < r]
                if observed:
                    approach = observed[0]
                    add(approach.presentation_ms, t, "lead_in", event=approach, priority=8, energy=.7)
                elif t-r >= 600:
                    add(r, t, "shot_call", event=release, priority=9, energy=.82)
            add(end+250, min(end+4100, deadline-100), "analysis", "Aiden", goal,
                summary="Explain the effect of the goal on the current score. No invented finish technique.", priority=5, energy=.52)
        for e in events:
            if e.type == "HALFTIME": add(e.presentation_ms, e.presentation_ms+2900, "halftime_recap", event=e, priority=9)
            elif e.type == "FULLTIME": add(e.presentation_ms, self.timeline.total_duration_ms, "fulltime_summary", event=e, priority=10)
        last_live = -10000
        for e in sorted(events, key=lambda e:e.presentation_ms):
            t = e.presentation_ms
            if t < 10000 or t-last_live < 6500 or e.type not in ("PASS","PROGRESSIVE_PASS","BOX_ENTRY","TURNOVER","SHOT_RELEASE"): continue
            if self.timeline.is_in_stoppage_card(t/1000): continue
            if add(t, t+3300, "attack" if e.type in ("BOX_ENTRY","SHOT_RELEASE") else "buildup",
                   event=e, priority=2, energy=.7 if e.type in ("BOX_ENTRY","SHOT_RELEASE") else .43): last_live = t
        slots.sort(key=lambda s:s.start_ms)
        for i, s in enumerate(slots): s.commentary_id = f"com_{i+1:03d}"
        return slots
