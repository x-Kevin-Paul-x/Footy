"""
HTTP Client for llama-server with JSON schema enforcement, strict validation, and factual fallback.
"""

import json
import urllib.request
from typing import Dict, Any, List, Optional

from backend.commentary.schemas import CommentarySlot, CommentaryUtterance, MatchContext
from backend.commentary.config import LLM_HOST, LLM_PORT
from backend.commentary.llm.prompts import (
    WRITER_SYSTEM_PROMPT,
    WRITER_JSON_SCHEMA,
    build_writer_user_prompt,
)


class LlamaClient:
    """Client for querying llama-server OpenAI-compatible API."""

    def __init__(self, host: str = LLM_HOST, port: int = LLM_PORT):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v1/chat/completions"
        self._server_available: Optional[bool] = None
        self.last_generation_source = 'none'

    def is_server_online(self) -> bool:
        if self._server_available is not None:
            return self._server_available
        try:
            health_url = f"http://{self.host}:{self.port}/health"
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=0.4) as resp:
                self._server_available = (resp.status == 200)
        except Exception:
            self._server_available = False
        return self._server_available

    def generate_utterance(
        self,
        slot: CommentarySlot,
        match_context: MatchContext,
        recent: List[CommentaryUtterance],
    ) -> CommentaryUtterance:
        """Query llama-server with thinking disabled and JSON schema enforced."""
        if not self.is_server_online():
            return self.fallback_generate(slot, match_context)

        sys_prompt = WRITER_SYSTEM_PROMPT.format(
            home_team=match_context.home_team,
            away_team=match_context.away_team,
            speaker=slot.speaker,
        )
        user_prompt = build_writer_user_prompt(
            slot=slot.model_dump(),
            match_context=match_context.model_dump(),
            recent_utterances=[r.model_dump() for r in recent],
        )

        payload = {
            "model": "qwen3.5-9b",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.65,
            "max_tokens": 200,
            "response_format": {
                "type": "json_object",
                "schema": WRITER_JSON_SCHEMA,
            },
            "enable_thinking": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }

        try:
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                self.last_generation_source = 'llm'
                return CommentaryUtterance(
                    commentary_id=slot.commentary_id,
                    speaker=slot.speaker,
                    energy=slot.energy_target,
                    emotion=parsed.get("emotion", "excited" if slot.energy_target >= 0.7 else "calm"),
                    target_duration_ms=int(slot.window_seconds * 1000),
                    primary=parsed.get("primary", ""),
                    short=parsed.get("short", ""),
                    emergency_short=parsed.get("emergency_short", ""),
                    used_fact_ids=parsed.get("used_fact_ids", slot.allowed_fact_ids[:2]),
                )
        except Exception:
            return self.fallback_generate(slot, match_context)

    def fallback_generate(self, slot, match_context):
        """Concise factual safety lines; never manufacture finish technique."""
        self.last_generation_source = 'factual_fallback'
        p = (slot.active_player or "").split()
        name = p[-1] if p else ""
        team, score, kind = slot.active_team or match_context.home_team, slot.running_score, slot.slot_type
        index = sum(ord(c) for c in slot.commentary_id)
        if kind == "goal_reaction":
            h, a = map(int, score.split("-"))
            outcome = "It's level!" if h == a else f"{team} score!"
            primary = f"Goal! {name}! {outcome}"
            short, emergency = f"Goal! {name} scores!", f"Goal! {name}!"
        elif kind == "analysis":
            h, a = map(int, score.split("-"))
            difference = abs(h-a)
            if h == a:
                choices = ["Nothing separates the sides now.", "An equaliser. A fresh contest."]
                short = "They're back on level terms."
                emergency = "Level again."
            elif difference == 1:
                choices = [f"{team} ahead now. A slender advantage.", "A narrow lead. Plenty still at stake."]
                short, emergency = f"A slender lead for {team}.", f"{team} lead."
            else:
                choices = [f"{team} have breathing room. {difference} goals clear.", "A bigger cushion, with time still remaining."]
                short, emergency = f"{team} are {difference} goals clear.", f"{team} lead."
            primary = choices[index % len(choices)]
        elif kind == "shot_call": primary = short = emergency = f"{name or 'Chance'}!"
        elif kind == "lead_in":
            primary, short, emergency = f"{name}, in possession here.", f"{name} on the ball.", f"{name}!"
            if slot.window_seconds < 1.5:
                primary = short = emergency
        elif kind == "halftime_recap":
            primary, short, emergency = f"Half-time. {match_context.home_team} {score}, {match_context.away_team}.", f"Half-time, {score}.", "Half-time."
        elif kind == "fulltime_summary":
            primary = f"Full-time! {match_context.home_team} {score}, {match_context.away_team}."
            short, emergency = f"Full-time, {score}.", "Full-time!"
        elif slot.active_event_type == "INTRO":
            if slot.speaker == "Ryan":
                primary = f"{match_context.home_team} against {match_context.away_team}. Welcome to {match_context.venue or 'the ground'}."
                short = f"{match_context.home_team} against {match_context.away_team}. We're underway."
            else:
                primary, short = "Good to be here. Let's see how this develops.", "Both teams are underway."
            emergency = "We're underway."
        elif slot.active_event_type in ("PASS", "PROGRESSIVE_PASS"):
            receiver = slot.active_facts.get("receiver", "").split()
            receiver = receiver[-1] if receiver else ""
            primary = [f"{name} finds {receiver}.", f"Across to {receiver}, from {name}.",
                       f"{name}, then {receiver}.", f"The ball reaches {receiver}."][index % 4]
            short, emergency = f"{name} to {receiver}.", f"{receiver}."
        elif slot.active_event_type == "BOX_ENTRY":
            primary, short, emergency = f"{name} reaches the penalty area.", f"{name} in the box.", f"{name}!"
        elif slot.active_event_type == "SHOT_RELEASE":
            primary, short, emergency = f"{name or 'The ball'}, towards goal!", f"{name or 'Chance'}!", f"{name or 'Chance'}!"
        else:
            primary = [f"{name} has it now.", f"Possession with {name}.", f"{name}, on the ball.",
                       f"{name} takes possession."][index % 4]
            short, emergency = f"{name} has it.", f"{name}."
        return CommentaryUtterance(commentary_id=slot.commentary_id, speaker=slot.speaker,
            energy=slot.energy_target, emotion="excited" if slot.energy_target>.7 else "calm",
            target_duration_ms=int(slot.window_seconds*1000), primary=primary,
            short=short, emergency_short=emergency, used_fact_ids=list(slot.allowed_fact_ids))
