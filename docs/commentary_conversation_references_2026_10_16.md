# Conversational commentary references and implementation

The target is two people watching the same match together: one following the
action, the other responding with relevant interpretation. Alternating voices
over unrelated announcements does not meet that target.

## Sources actually inspected

| Reference | Access and reliability | Application |
| --- | --- | --- |
| [Flashscore public demo](https://www.flashscore.com/audio/) | Retrieved the page's public `audio-promo-en.mp3`; automatically transcribed locally with faster-whisper `base.en`. ASR names and punctuation are unverified. No perceptual listening claim. | One continuous action chain followed by goal and score confirmation. This short sample appears to feature one lead voice; it cannot establish two-person interaction patterns. |
| [World Cup 2022 transcript study: university thesis](https://uokerbala.edu.iq/wp-content/uploads/2025/09/RP-A-Pragma-Stylistic-Study-of-British-Football-Commentaries-on-FIFA-World-Cup-Qatar-2022.pdf.pdf) | The indexed excerpt at section 4.2.5 contains a transcribed Argentina–France final exchange. Direct PDF retrieval returned 403/406. This is a researcher's transcription, not a broadcaster-certified transcript. | Lead establishes the occasion, colleague reacts, analyst discusses the line-up, lead returns to ball movement, analyst explains the implications of a foul. Each speaker picks up the preceding contribution. |
| [Published World Cup study and transcribed examples](https://www.researchgate.net/publication/394549847_Achieving_Optimal_Relevance_through_Maxims_Flouting_A_Pragma-Stylistic_Study_of_British_Commentary_on_FIFA_World_Cup_2022) | Accessible full-text research article, with spoken examples from Brazil–South Korea and the final, and source links for the Netherlands–Argentina quarter-final and other games. The article's reference list is not itself a full-match transcript. | Short emphatic reactions, variable sentence lengths and occasional repetition carry emotion. We exclude invented inner thoughts and psychological assertions, even when human commentary uses them rhetorically. |
| [GOAL: grounded football commentaries](https://arxiv.org/html/2211.04534v1) | Primary research with professionally transcribed football highlights and actual commentary examples. | Previous utterances and entity knowledge matter. Its examples also demonstrate how fluent model outputs can invent the wrong outcome. Useful as a diagnostic reference, not assumed permission to redistribute broadcasts or train on them. |
| [Champions League final 2012 register study](https://journal.unair.ac.id/ANGLICIST%40the-register-of-football-commentators-in-champions-league-final-2012--article-9879-media-94-category-8.html) | Retrieved the authors' abstract and methodology describing their transcription. We have not retrieved their complete match transcript. | Action calls use fragments and changes in intonation; discussion can use fuller sentences. Do not enforce the same cadence on every turn. |

These are spoken-commentary references, with the access limits above. Written
minute-by-minute reports are a different format. No complete copyrighted match
transcripts or borrowed commentator catchphrases are included in the engine.
The local demo audio/ASR research files stay in ignored artifacts. References
inform original prompts and structure, not voice cloning or model fine-tuning.

## Implemented behaviour

- [x] Original language-model dialogue replaces template selection for discussion,
  post-goal analysis and introductions when the local model is available.
- [x] Ryan opens a topic or asks a question; Aiden receives the preceding turns
  and their possible spoken variants before replying.
- [x] Paired quiet-play discussions reserve space ahead of routine possession
  announcements. Recorded attacks, shots, goals and whistles retain priority.
- [x] Each prompt receives only evidence available at its presentation timestamp,
  current score/team binding and recent dialogue. The full-match final result and
  aggregate statistics are excluded.
- [x] Structured citations, length/format checks and a separate adversarial model
  review inspect every variant. One repair attempt is allowed before fallback.
- [x] The planner owns the supported conversational meaning and citations. The
  model writes one original primary turn; shorter emergency alternatives remain
  controlled. This separates language generation from factual planning.
- [x] Required event calls retain deterministic source-bound realization.
- [x] Missing spoken questions suppress dependent answers, including cached audio.
- [x] A rejected question or answer replaces both turns with a matched contextual
  exchange. Fallback answers recommend possible choices rather than inventing
  observed tactics or player behaviour.
- [x] Provenance distinguishes original reviewed dialogue from controlled fallback;
  the review page and quality report expose that distinction.

## What these checks can and cannot establish

Score transitions, event anchors, evidence availability, audio deadlines and
content integrity have deterministic checks. Open natural-language assertions
also rely on a fallible semantic model reviewer. That reviewer is a separate
request to the same local model, not a separately trained verifier and not a
proof that hallucinations are impossible. A passing automated report is not a
listening score. Rejected conversation falls back visibly; offline mode remains
controlled and will sound more repetitive.

The first real script trial exposed many malformed citations, overly long short
variants and an incorrect spoken score that the model reviewer missed. It was
not released as a new audio review. Citation IDs were subsequently constrained
in the JSON schema, budgets adjusted, and verbal score/embedded speaker-label
checks strengthened. A second trial still fell back too often, so generation
was simplified to one primary wording over an approved meaning; citations and
emergency variants now belong to the deterministic planner. A CPU pilot accepted
a complete original two-person exchange; another exchange fell back after a
request timeout. This is why real-generation checks accompany unit tests.

## Next evaluation gates

- [ ] Listen for believable responses, name pronunciation and consistent voices.
- [ ] Reject superficially fluent exchanges that do not answer the actual question.
- [ ] Compare quiet-gap durations and fallback rates against the previous review.
- [ ] Expand verified team/player histories before discussing streaks, biographies,
  league prospects or other fixtures. Absent evidence is not permission to invent.
- [ ] Extend richer live action chains using additional observed event evidence.
  The Flashscore sample shows the target; the current live observation vocabulary
  still limits how descriptive those calls can be.
