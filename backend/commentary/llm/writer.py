"""Write, validate every alternative, and remember only accepted lines."""
from backend.commentary.schemas import CommentaryScript
from backend.commentary.llm.client import LlamaClient
from backend.commentary.llm.validator import FactFirewallValidator, RepetitionDetector
class CommentaryWriter:
    def __init__(self, match_context, client=None):
        self.context, self.client = match_context, client or LlamaClient()
        self.validator = FactFirewallValidator(match_context)
        self.repetition = RepetitionDetector(memory_window=12)
        self.diagnostics = {"llm_accepted":0, "factual_fallbacks":0, "rejections":[]}
    def write_script(self, slots):
        utterances = []
        for slot in slots:
            # Sub-second live calls are tightly constrained, not prose writing.
            if slot.slot_type == "shot_call":
                utt = self.client.fallback_generate(slot, self.context)
                source = "factual_fallbacks"
            else:
                utt = self.client.generate_utterance(slot, self.context, utterances)
                source = "llm_accepted" if self.client.last_generation_source == 'llm' else "factual_fallbacks"
            valid, errors = self.validator.validate(utt, slot)
            repetitive, _, phrase = self.repetition.check_repetition(utt.primary, commit=False)
            if not valid or repetitive or len(utt.primary.split()) > slot.target_words+3:
                self.diagnostics["rejections"].append({"id":slot.commentary_id,"errors":errors,"repeated":phrase})
                utt = self.client.fallback_generate(slot, self.context)
                source = "factual_fallbacks"
            valid, errors = self.validator.validate(utt, slot)
            if not valid:
                raise ValueError(f"Invalid fallback {slot.commentary_id}: {errors}")
            self.repetition.check_repetition(utt.primary)
            self.diagnostics[source] += 1
            utterances.append(utt)
        return CommentaryScript(match_id=self.context.match_id, utterances=utterances,
            model_version="Qwen3.5-9B-Q4_K_M" if self.diagnostics["llm_accepted"] else "factual-fallback")
