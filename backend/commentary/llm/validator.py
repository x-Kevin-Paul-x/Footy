"""
Phase 8: Fact Firewall & Repetition Validator.
Validates generated commentary lines against the factual whitelist and checks repetition.
Enforces:
- Strict running scoreline verification (rejects future/unverified scores).
- Active goal scorer verification (must celebrate the correct player).
- Anti-spoiler rules (rejects premature match endings or full-time declarations).
- Anti-repetition across a sliding window.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from backend.commentary.schemas import CommentaryUtterance, CommentarySlot, MatchContext


class FactFirewallValidator:
    """Validates that generated lines cite valid fact IDs and do not hallucinate."""

    def __init__(self, match_context: MatchContext):
        self.context = match_context
        self.allowed_facts = match_context.allowed_facts
        self.all_player_names = set(match_context.home_players + match_context.away_players)

    def validate(self, utterance: CommentaryUtterance, slot: CommentarySlot) -> Tuple[bool, List[str]]:
        errors = []

        # 1. Verify commentary_id correspondence
        if utterance.commentary_id != slot.commentary_id:
            errors.append(f"Mismatched ID: expected {slot.commentary_id}, got {utterance.commentary_id}")

        # 2. Verify all used_fact_ids are real
        for fid in utterance.used_fact_ids:
            if fid not in self.allowed_facts:
                errors.append(f"Unknown cited fact ID: {fid}")
            if slot.allowed_fact_ids and fid not in slot.allowed_fact_ids:
                errors.append(f"Fact outside this slot: {fid}")
            if self.context.fact_available_ms.get(fid, 0) > slot.start_ms:
                errors.append(f"Future fact: {fid}")

        # 3. Check for premature match ending phrases before minute 88
        if slot.slot_type != "fulltime_summary":
            lower_primary = ' '.join([utterance.primary, utterance.short, utterance.emergency_short]).lower()
            prohibited_terms = [
                "game over",
                "sealed the win",
                "sealed it",
                "final whistle",
                "full-time",
                "all over",
                "take all three points",
                "final score",
                "win it four to two",
                "bournemouth win it",
            ]
            for term in prohibited_terms:
                if term in lower_primary:
                    errors.append(f"Premature match conclusion phrase '{term}' in minute {slot.match_minute}")

        # 4. Strict Running Scoreline Verification
        # Find any score pattern like X-Y or X to Y
        for text in [utterance.primary, utterance.short, utterance.emergency_short]:
            number_words = {'nil':'0', 'zero':'0', 'one':'1', 'two':'2', 'three':'3', 'four':'4', 'five':'5', 'six':'6', 'seven':'7', 'eight':'8', 'nine':'9', 'ten':'10'}
            score_text = re.sub(r'\b(?:nil|zero|one|two|three|four|five|six|seven|eight|nine|ten)\b', lambda m:number_words[m.group()], text.lower())
            scores_found = re.findall(r"\b(\d+)\s*(?:[-–]|to)\s*(\d+)\b", score_text)
            for h, a in scores_found:
                mentioned = f"{h}-{a}"
                # Must match current running score (or reverse)
                expected_score = slot.running_score
                parts = expected_score.split("-") if "-" in expected_score else ["0", "0"]
                exp_h, exp_a = parts[0], parts[1]
                if mentioned not in (expected_score, f"{exp_a}-{exp_h}"):
                    errors.append(
                        f"Illegal scoreline {mentioned} mentioned: active match score is {expected_score}"
                    )

        # 5. Active Goal Scorer Verification
        if slot.slot_type == "goal_reaction" and slot.active_player:
            active_p = slot.active_player.lower()
            last_name = active_p.split()[-1] if active_p else ""
            for text in (utterance.primary, utterance.short, utterance.emergency_short):
                if last_name not in text.lower():
                    errors.append(f"Wrong scorer attributed: expected {slot.active_player} in '{text}'")
        for text in (utterance.primary, utterance.short, utterance.emergency_short):
            if not text.strip(): errors.append('Empty speech variant')
            if re.search(r'\b(?:he|she|his|her)\b', text, re.I):
                errors.append('Unverified player gender')
            if not re.search(r'[A-Za-z]', text): errors.append('Speech has no words')
            if slot.active_event_type in ('CONTROL_IN_ATTACK', 'POSSESSION_START', 'TURNOVER') and re.search(r'\b(?:pass(?:es)?|feed(?:s)?|find(?:s)?|turn(?:s)?|run(?:s)?|move(?:s)?|driv(?:es|ing)|advance|build|attack|press|space)\b', text, re.I):
                errors.append('Invented action beyond recorded possession')
            if slot.active_event_type in ('PASS', 'PROGRESSIVE_PASS') and re.search(r'\b(?:run(?:s)?|move(?:s)?|press|driv(?:es|ing)|space|attack|respond)\b', text, re.I):
                errors.append('Invented action beyond recorded pass')
            permitted = [slot.active_player or '', slot.active_facts.get('passer',''), slot.active_facts.get('receiver','')]
            permitted_words = {name.lower().split()[-1] for name in permitted if name}
            if slot.active_event_type != 'INTRO':
                for name in self.all_player_names:
                    surname = name.lower().split()[-1]
                    if surname not in permitted_words and re.search(r'\b'+re.escape(surname)+r'\b', text.lower()):
                        errors.append(f'Unrelated player in active action: {name}')
            if slot.slot_type == 'lead_in' and slot.active_player and slot.active_player.lower().split()[-1] not in text.lower():
                errors.append('Buildup names the wrong player')
            if slot.active_event_type != 'INTRO' and re.search(r'\b(?:Ryan|Aiden)\b', text):
                errors.append('Unnecessary partner name')
            if any(phrase in text.lower() for phrase in ('dictating tempo', 'stretching the pitch', 'circulating the ball', 'clinical execution', 'cold-blooded', 'did you see that', 'spot on')):
                errors.append('Stock commentary phrase')

        # 6. Verify length ordering: primary >= short >= emergency_short
        p_len = len(utterance.primary.split())
        s_len = len(utterance.short.split())
        e_len = len(utterance.emergency_short.split())

        if s_len > p_len + 2:
            errors.append(f"Short variant ({s_len} words) is longer than primary ({p_len} words)")
        if e_len > s_len + 2:
            errors.append(f"Emergency short ({e_len} words) is longer than short ({s_len} words)")

        is_valid = len(errors) == 0
        return is_valid, errors


class RepetitionDetector:
    """Detects repetitive phrasing and clichés across recent utterances."""

    def __init__(self, memory_window: int = 5):
        self.memory_window = memory_window
        self.history: List[str] = []

    def get_ngrams(self, text: str, n: int = 3) -> set:
        words = re.findall(r"\b\w+\b", text.lower())
        if len(words) < n:
            return set()
        return set(tuple(words[i : i + n]) for i in range(len(words) - n + 1))

    def check_repetition(self, new_text: str, commit: bool = True) -> Tuple[bool, float, Optional[str]]:
        """Returns (is_repetitive, max_overlap_ratio, repetitive_phrase)."""
        new_ngrams = self.get_ngrams(new_text, n=3)
        if not new_ngrams or not self.history:
            if commit: self.history.append(new_text)
            if len(self.history) > self.memory_window:
                self.history.pop(0)
            return False, 0.0, None

        max_overlap = 0.0
        worst_phrase = None
        for prev in self.history:
            prev_ngrams = self.get_ngrams(prev, n=3)
            if not prev_ngrams:
                continue
            intersection = new_ngrams.intersection(prev_ngrams)
            overlap = len(intersection) / max(1, len(new_ngrams))
            if overlap > max_overlap:
                max_overlap = overlap
                if intersection:
                    worst_phrase = " ".join(list(intersection)[0])

        is_repetitive = max_overlap > 0.35  # More than 35% 3-gram reuse triggers variant shift

        if commit: self.history.append(new_text)
        if len(self.history) > self.memory_window:
            self.history.pop(0)

        return is_repetitive, round(max_overlap, 3), worst_phrase
