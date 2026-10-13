"""Fact-scoped writing guidance, without canned pundit exchanges."""
import json
DIRECTOR_SYSTEM_PROMPT = "Plan a factual broadcast for {home_team} versus {away_team}."
WRITER_SYSTEM_PROMPT = """Write British football commentary for {home_team} versus {away_team}.
You write for {speaker}. Ryan calls visible play. Aiden explains the implications after a goal.
Speak naturally, with varied sentence openings and short clauses. Never address your partner by name except during the introduction.
Use ONLY the supplied facts known NOW. Do not invent assists, tactics, finish technique, goalkeeper mistakes,
player gender, substitutions or crowd reactions. Never describe the match as decided before the full-time whistle.
Avoid: clinical execution, cold-blooded strike, dictating tempo, stretching the pitch, circulating the ball,
did you see that, spot on, absolutely frantic. No repeated question-and-answer formula.
Provide primary, shorter short, and still shorter emergency_short alternatives. Every goal alternative must name the scorer.
Urgent calls start with the action, without a preamble. Short slots need extremely short lines.
Return JSON only, with used_fact_ids supporting your words."""
WRITER_JSON_SCHEMA = {"type":"object", "properties":{
    "primary":{"type":"string"}, "short":{"type":"string"}, "emergency_short":{"type":"string"},
    "emotion":{"type":"string"}, "used_fact_ids":{"type":"array","items":{"type":"string"}}},
    "required":["primary","short","emergency_short","used_fact_ids"]}
def build_writer_user_prompt(slot, match_context, recent_utterances):
    whitelist = {fid:match_context["allowed_facts"][fid] for fid in slot["allowed_fact_ids"] if fid in match_context["allowed_facts"]}
    public = {k:slot.get(k) for k in ("slot_type","speaker","target_words","running_score","active_event_type","active_player","active_team","in_play_summary")}
    return json.dumps({"live":public,"facts":whitelist,"recent_lines":[u["primary"] for u in recent_utterances[-12:]],
        "requirements":"No partner names. Primary must fit target_words. Don't repeat these openings."})
