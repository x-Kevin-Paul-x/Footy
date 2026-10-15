"""Controlled factual realization with a second gate after candidate selection."""
from backend.commentary.schemas import CommentaryScript
from backend.commentary.llm.client import LlamaClient
from backend.commentary.llm.validator import FactFirewallValidator
from backend.commentary.grounding import GroundedCompiler, MissingEvidence


class CommentaryWriter:
    def __init__(self, match_context, client=None):
        self.context = match_context
        self.client = client or LlamaClient()
        self.compiler = GroundedCompiler(match_context)
        self.validator = FactFirewallValidator(match_context)
        self.diagnostics = {"llm_accepted": 0, "factual_fallbacks": 0, "rejections": [],
                            "omissions": [], "selected_claims": []}

    def write_script(self, slots):
        utterances, spoken = [], set()
        for slot in slots:
            try:
                options = self.compiler.options(slot)
            except MissingEvidence as exc:
                if slot.slot_type in ('goal_reaction', 'halftime_recap', 'fulltime_summary'):
                    raise
                self.diagnostics['omissions'].append({"id": slot.commentary_id, "reason": str(exc)})
                continue
            # Critical calls may repeat necessary names. Analyst/filler prose
            # gets a whole-match exact-sentence cooldown, including alternatives.
            if slot.slot_type in ('analysis', 'story'):
                options = [o for o in options if not ({o.primary, o.short, o.emergency_short} & spoken)]
                if not options:
                    self.diagnostics['omissions'].append({"id": slot.commentary_id, "reason": 'No novel supported alternative'})
                    continue
            selected = self.client.choose_template(slot, options, utterances)
            utt = self.compiler.realize(slot, selected)
            valid, errors = self.validator.validate(utt, slot)
            if not valid:
                raise MissingEvidence(f'Controlled realization failed: {errors}')
            source = 'llm_accepted' if self.client.last_generation_source == 'llm_selection' else 'factual_fallbacks'
            self.diagnostics[source] += 1
            if self.client.last_failure:
                self.diagnostics['rejections'].append({"id": slot.commentary_id, "reason": self.client.last_failure})
            spoken.update((utt.primary, utt.short, utt.emergency_short))
            self.diagnostics['selected_claims'].append({"id": slot.commentary_id, **utt.grounding})
            utterances.append(utt)
        return CommentaryScript(match_id=self.context.match_id, utterances=utterances,
                                model_version='controlled-evidence-1')
