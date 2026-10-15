"""Controlled factual realization with a second gate after candidate selection."""
from backend.commentary.schemas import CommentaryScript
from backend.commentary.llm.client import LlamaClient
from backend.commentary.llm.validator import FactFirewallValidator
from backend.commentary.grounding import GroundedCompiler, MissingEvidence
from backend.commentary.llm.conversation import draft


class CommentaryWriter:
    def __init__(self, match_context, client=None):
        self.context = match_context
        self.client = client or LlamaClient()
        self.compiler = GroundedCompiler(match_context)
        self.validator = FactFirewallValidator(match_context)
        self.diagnostics = {"llm_accepted": 0, "factual_fallbacks": 0, "rejections": [],
                            "omissions": [], "selected_claims": [], "dialogue_accepted": 0}

    def write_script(self, slots):
        utterances, spoken, prepared = [], set(), {}
        groups = {}
        for candidate in sorted(slots,key=lambda s:s.start_ms):
            if candidate.dialogue_id:
                groups.setdefault(candidate.dialogue_id,[]).append(candidate)
        for slot in sorted(slots,key=lambda s:s.start_ms):
            if slot.reply_to and not any(u.commentary_id == slot.reply_to for u in utterances):
                self.diagnostics['omissions'].append({'id':slot.commentary_id,'reason':'Dialogue opener omitted'})
                continue
            if slot.dialogue_id:
                if slot.dialogue_id not in prepared:
                    pair = groups[slot.dialogue_id]
                    if (len(pair)!=2 or pair[0].speech_act!='ask' or pair[1].speech_act!='answer' or
                            pair[1].reply_to!=pair[0].commentary_id):
                        raise MissingEvidence('Discussion must contain a linked question and answer')
                    turns = None
                    if self.client.is_server_online():
                        try:
                            first = draft(self.client,self.context,pair[0],utterances)
                            second = draft(self.client,self.context,pair[1],utterances+[first])
                            turns = [first,second]
                            if not all(self.validator.validate(u,s)[0] for u,s in zip(turns,pair)):
                                raise MissingEvidence('Discussion validation failed')
                            self.diagnostics['dialogue_accepted'] += 2
                        except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
                            self.diagnostics['rejections'].append({'id':slot.dialogue_id,'reason':str(exc)})
                            turns = None
                    if turns is None:
                        turns = [self.compiler.realize(
                            s,self.compiler.stable_choice(s,self.compiler.options(s))) for s in pair]
                        self.diagnostics['factual_fallbacks'] += 2
                    prepared[slot.dialogue_id] = {u.commentary_id:u for u in turns}
                utt = prepared[slot.dialogue_id][slot.commentary_id]
                utterances.append(utt)
                spoken.update((utt.primary,utt.short,utt.emergency_short))
                self.diagnostics['selected_claims'].append({'id':slot.commentary_id,**utt.grounding})
                continue
            conversational = slot.slot_type in ('story','analysis') or slot.active_event_type == 'INTRO'
            if conversational and self.client.is_server_online():
                try:
                    utt = draft(self.client,self.context,slot,utterances)
                    if any(getattr(utt,v) in spoken for v in ('primary','short','emergency_short')):
                        raise MissingEvidence('Repeated dialogue')
                    valid, errors = self.validator.validate(utt,slot)
                    if not valid:
                        raise MissingEvidence(str(errors))
                    self.diagnostics['dialogue_accepted'] += 1
                    utterances.append(utt)
                    spoken.update((utt.primary,utt.short,utt.emergency_short))
                    self.diagnostics['selected_claims'].append({'id':slot.commentary_id,**utt.grounding})
                    continue
                except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
                    self.diagnostics['rejections'].append({'id':slot.commentary_id,'reason':str(exc)})
            try:
                options = self.compiler.options(slot)
            except MissingEvidence as exc:
                if slot.slot_type in ('goal_reaction', 'halftime_recap', 'fulltime_summary'):
                    raise
                self.diagnostics['omissions'].append({"id": slot.commentary_id, "reason": str(exc)})
                continue
            # Critical calls may repeat necessary names. Analyst/filler prose
            # gets a whole-match exact-sentence cooldown, including alternatives.
            if slot.slot_type in ('analysis', 'story') and not slot.dialogue_id:
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
                                model_version='conversation-1-with-controlled-event-calls')
