"""Select an eligible speech plan; model output cannot introduce prose or facts."""
import json
import urllib.request
from backend.commentary.config import LLM_HOST, LLM_PORT
from backend.commentary.grounding import GroundedCompiler


class LlamaClient:
    def __init__(self, host=LLM_HOST, port=LLM_PORT):
        self.host, self.port = host, port
        self.base_url = f"http://{host}:{port}/v1/chat/completions"
        self._server_available = None
        self.last_generation_source = 'none'
        self.last_failure = None

    def is_server_online(self):
        if self._server_available is None:
            try:
                with urllib.request.urlopen(f"http://{self.host}:{self.port}/health", timeout=.4) as response:
                    self._server_available = response.status == 200
            except OSError:
                self._server_available = False
        return self._server_available

    def choose_template(self, slot, options, recent):
        self.last_failure = None
        self.last_generation_source = 'grounded_fallback'
        fallback = GroundedCompiler.stable_choice(slot, options)
        if not self.is_server_online() or len(options) == 1:
            return fallback
        ids = [o.template_id for o in options]
        payload = {
            "model": "qwen3.5-9b", "temperature": .35, "max_tokens": 80,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [
                {"role": "system", "content": "Choose one supplied commentary template. Select natural variety appropriate to the speaker and clock. Return only the template_id JSON. Never write commentary or introduce facts."},
                {"role": "user", "content": json.dumps({
                    "speaker": slot.speaker, "match_minute": slot.match_minute,
                    "purpose": slot.slot_type,
                    "candidates": [{"template_id": o.template_id, "text": o.primary} for o in options],
                    "recent_lines": [u.primary for u in recent[-12:]],
                })},
            ],
            "response_format": {"type": "json_object", "schema": {
                "type": "object", "additionalProperties": False,
                "properties": {"template_id": {"type": "string", "enum": ids}},
                "required": ["template_id"],
            }},
        }
        try:
            request = urllib.request.Request(self.base_url, data=json.dumps(payload).encode(),
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=20) as response:
                parsed = json.loads(json.loads(response.read())["choices"][0]["message"]["content"])
            if set(parsed) != {"template_id"} or parsed['template_id'] not in ids:
                raise ValueError('Unknown template or extra factual output')
            self.last_generation_source = 'llm_selection'
            return parsed['template_id']
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            self.last_failure = type(exc).__name__
            return fallback

    def generate_utterance(self, slot, match_context, recent):
        compiler = GroundedCompiler(match_context)
        return compiler.realize(slot, self.choose_template(slot, compiler.options(slot), recent))

    def fallback_generate(self, slot, match_context):
        self.last_generation_source = 'grounded_fallback'
        compiler = GroundedCompiler(match_context)
        return compiler.realize(slot, compiler.stable_choice(slot, compiler.options(slot)))
