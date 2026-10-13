"""Timestamped facts from the recorded match, without future outcomes."""
from backend.commentary.schemas import MatchContext
class StoryStatsBuilder:
    def __init__(self, manifest): self.manifest = manifest
    def build_match_context(self, events, sequences):
        m = self.manifest
        home, away = m["home_team"], m["away_team"]
        venue = m.get("venue") or ("Turf Moor" if home == "Burnley" else "")
        facts, available, links = {}, {}, {}
        def add(text, when=0):
            fid = f"fact_{len(facts)+1:04d}"
            facts[fid], available[fid] = text, when
            return fid
        add(f"The home team is {home}.")
        add(f"The away team is {away}.")
        add(f"The venue is {venue}." if venue else "The home team hosts this fixture.")
        for team, players in ((home, m.get("home_players", [])), (away, m.get("away_players", []))):
            for player in players: add(f"{player} plays for {team}.")
        for e in events:
            name, team, text = e.player, e.team, ""
            if e.type == "GOAL": text = f"{name} scores for {team}. Current home-away score: {e.facts['score']}."
            elif e.type == "SHOT_RELEASE": text = f"{name or 'The ball'} {'releases the ball' if name else 'travels'} towards goal for {team}. Outcome is unknown."
            elif e.type == "BOX_ENTRY": text = f"{name} takes the ball into the opposing penalty area for {team}."
            elif e.type in ("PASS", "PROGRESSIVE_PASS"): text = f"{e.facts.get('passer', name)} passes to {e.facts.get('receiver', 'a teammate')} for {team}."
            elif e.type in ("TURNOVER", "POSSESSION_START", "CONTROL_IN_ATTACK"): text = f"{name} has possession for {team}."
            elif e.type == "SHOT": text = f"{name} has a shot for {team}."
            elif e.type == "HIT_POST": text = f"{name}'s effort hits the woodwork for {team}."
            elif e.type in ("HALFTIME", "FULLTIME"): text = f"{'Half-time' if e.type == 'HALFTIME' else 'Full-time'} whistle. Home-away score: {e.facts.get('score', '')}."
            if text: links[e.event_id] = add(text, e.presentation_ms)
        fulltime = next((e.presentation_ms for e in events if e.type == "FULLTIME"), 10**12)
        for key in ("possession", "shots", "xg"):
            value = m.get(key, [])
            if len(value) == 2: add(f"Full-time {key}: {home} {value[0]}, {away} {value[1]}.", fulltime)
        return MatchContext(match_id=str(m["match_id"]), home_team=home, away_team=away,
            home_score=int(m["home_score"]), away_score=int(m["away_score"]), venue=venue,
            score_str=f"{home} {m['home_score']}-{m['away_score']} {away}",
            home_players=m.get("home_players", []), away_players=m.get("away_players", []),
            xg=m.get("xg", []), possession=m.get("possession", []), shots=m.get("shots", []),
            shots_on_target=m.get("shots_on_target", []), allowed_facts=facts,
            fact_available_ms=available, event_to_fact_id=links)
