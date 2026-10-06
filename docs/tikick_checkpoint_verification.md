# TiKick checkpoint and inference check — 4 October 2026

The installed `backend/checkpoints/tikick/actor.pt` is byte-for-byte identical
to the official 11-v-11 checkpoint linked by [TiKick's repository](https://github.com/TARTRL/TiKick).

- Official folder: `15OiZeUKCIJeWKePPCYrff-abnIm16jsF`.
- Official actor file: `1sssrSfTmiKvjmGcViMoKkv66KbjqRKIq`.
- Both files contain 2,964,564 bytes.
- Both SHA-256 values:
  `5e8157c79353cc916464faa0b2feba07ab4bdcf7b521060c85a19e86686dcef5`.

The earlier 380-match verification season used these exact weights, but restricted
inference to 19 actions and applied Footy's tactical action overrides. Its audit
establishes replay integrity, not equivalence to TiKick's original policy behaviour.
Those archived matches and their audit remain unchanged.

Current default inference restores actions 0–19, as TiKick's `11_vs_11_kaggle`
wrapper specifies. Action 19 delegates to GRF's built-in AI; it is a legitimate
choice of the released actor. Footy's movement and sprint overrides now require
explicit `apply_tactical_bias=True`. Match provenance records the inference
profile and whether tactical action overrides were enabled.

`backend/verification/verify_actor_encoder.py` compares both teams' features and
actions against TiKick's original encoder, model configuration and recurrent
evaluation for 32 live native steps. Both comparisons passed.

`backend/verification/compare_actor_profiles.py` ran two complete native matches
from the same seed with default rosters. The earlier settings finished 2–0;
restored settings finished 3–4. Each completed 3,001 public steps. All corrected
match actions were checked against actor output before being applied to GRF.

A rough crowding measure counted team-frames with at least three players within
0.10 normalized pitch units of the ball during normal play: 1,394 under the
earlier settings and 572 under the restored settings. This one comparison
supports the observed behaviour change; it does not establish general tactical
quality or isolate the action mask from tactical overrides.

Footy's team formations and player attributes still differ from a completely
unmodified upstream scenario. The 11-v-11 actor is used for both teams in self-play;
TiKick's published evaluation controls one team against GRF's opponent AI.

Footy's actual frontend is running on `http://127.0.0.1:5173/`, connected to its
FastAPI backend on port 5001 and the saved full-season database. Port 8768 was
only a separate verification viewer.
