"""Reserve decisive events first; optional speech yields to these deadlines."""
from backend.commentary.schemas import CommentarySlot
from backend.commentary.grounding import EvidenceLedger
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
            add(end+250, min(end+4100, deadline-100), "analysis", "Aiden", goal,
                summary="Explain the effect of the goal on the current score. No invented finish technique.", priority=5, energy=.52)
        for e in events:
            if e.type == "HALFTIME": add(e.presentation_ms, e.presentation_ms+2900, "halftime_recap", event=e, priority=9)
            elif e.type == "FULLTIME": add(e.presentation_ms, self.timeline.total_duration_ms, "fulltime_summary", event=e, priority=10)
        last_live = -10000
        ordered_events = sorted(events, key=lambda e:e.presentation_ms)
        for e in ordered_events:
            t = e.presentation_ms
            urgent = e.type in ('BOX_ENTRY', 'SHOT_RELEASE', 'CONTROL_IN_ATTACK')
            if t < 10000 or t-last_live < (1900 if urgent else 6000):
                continue
            if e.type not in ('PASS','PROGRESSIVE_PASS','BOX_ENTRY','TURNOVER','SHOT_RELEASE','CONTROL_IN_ATTACK'):
                continue
            if self.timeline.is_in_stoppage_card(t/1000):
                continue
            # A recorded event may bound speech fitting, but no later scorer
            # or outcome selects an anticipation cue or its wording.
            blocked = [s.start_ms for s in slots if s.start_ms > t and s.priority >= 8]
            end = min(t + (2500 if urgent else 3300), min(blocked)-100 if blocked else t+3300)
            kind = 'shot_call' if e.type == 'SHOT_RELEASE' else 'attack' if urgent else 'buildup'
            if add(t, end, kind, event=e, priority=8 if urgent else 2,
                   energy=.76 if urgent else .43):
                last_live = t
        # Fill eligible quiet windows using already-recorded roles/formations.
        # No streak, age or other-match result is manufactured when absent.
        formations = [r for r in context.evidence_records if r['kind'] == 'formation']
        home_players = [r for r in context.evidence_records if r['kind'] == 'player' and r['data']['team'] == context.home_team]
        away_players = [r for r in context.evidence_records if r['kind'] == 'player' and r['data']['team'] == context.away_team]
        topics = [r for r in context.evidence_records if r['kind'] in ('prior_result','winning_run')] + formations
        for i in range(max(len(home_players),len(away_players))):
            topics.extend(team[i] for team in (home_players,away_players) if i < len(team))
        topic_index = 0
        used_stories = set()
        ledger = EvidenceLedger(context)
        boundaries = [(int(a*1000),int(b*1000)) for a,b in self.timeline.get_play_windows()]
        for start, end in boundaries:
            occupied = sorted([s for s in slots if s.start_ms < end and s.max_end_ms > start], key=lambda s:s.start_ms)
            cursor = start
            for following in occupied + [None]:
                stop = min(end, following.start_ms) if following else end
                if stop-cursor >= 6000 and topic_index < len(topics):
                    story_start = cursor+1800
                    story_end = min(story_start+4500,stop-250)
                    # Expire a background story before an observed danger cue,
                    # even when that cue itself was not allocated speech.
                    cues = [e.presentation_ms for e in ordered_events if
                            e.type in ('BOX_ENTRY','SHOT_RELEASE','CONTROL_IN_ATTACK') and
                            story_start < e.presentation_ms < story_end]
                    if cues:
                        story_end = min(cues)-100
                    if story_end-story_start >= 2800:
                        milestones = [r for r in ledger.at(story_start) if r['kind'] == 'goal_tally'
                                      and r['id'] not in used_stories]
                        record = milestones[-1] if milestones else topics[topic_index]
                        if record['available_ms'] <= story_start and add(story_start,story_end,'story',
                                speaker='Aiden' if topic_index%2==0 else 'Ryan',priority=1):
                            story_slot = slots[-1]
                            story_slot.active_event_type = 'STORY'
                            story_slot.evidence_ids = [record['id']]
                            used_stories.add(record['id'])
                            if not milestones:
                                topic_index += 1
                if following:
                    cursor = max(cursor,following.max_end_ms)
        slots.sort(key=lambda s:s.start_ms)
        for i, s in enumerate(slots): s.commentary_id = f"com_{i+1:03d}"
        return slots
