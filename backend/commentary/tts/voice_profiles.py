"""Versioned delivery settings; seeds aid reproducibility, not a voice guarantee."""

import hashlib

PROFILE_REVISION = 'preset-native-1'
PRONUNCIATION_REVISION = 'unaltered-1'
GENERATION = dict(do_sample=True, temperature=.65, top_p=.9, top_k=30,
                  subtalker_dosample=True, subtalker_temperature=.65,
                  subtalker_top_p=.9, subtalker_top_k=30)


def instruction(slot):
    if slot.get('speaker') == 'Aiden':
        return 'Clear English football analyst. Warm, conversational and measured, with consistent natural vocal tone. No whispering.'
    if slot.get('slot_type') == 'goal_reaction':
        return 'Clear English football commentator. Immediate energetic goal call in your usual voice. No screaming, whispering or long pauses.'
    if slot.get('energy_target', .5) >= .7:
        return 'Clear English football commentator. Brisk rising anticipation in your usual voice. Begin promptly, without whispering.'
    return 'Clear English football broadcaster. Relaxed conversational delivery in your usual voice. No whispering or theatrical pauses.'


def clip_seed(cid, text, speaker, variant):
    key = f'{PROFILE_REVISION}:{PRONUNCIATION_REVISION}:{cid}:{text}:{speaker}:{variant}'
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], 'big')
