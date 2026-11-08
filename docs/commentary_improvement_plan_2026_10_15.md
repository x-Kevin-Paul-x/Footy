# Commentary improvement plan

Research date: 15 October 2026. Status: first correctness milestone implemented; remaining work is tracked below.

The next version should sound like two people following the match: the lead describes meaningful action, the analyst adds context, excitement follows the clock and score, and neither voice invents what happened. Correctness and timing are release gates. Naturalness and pronunciation require listening, not just a passing automated report.

User requirement added 15 October: avoid long stretches without commentary. Quiet phases should carry entertaining player stories, team identity, form, other-fixture context and clearly framed opinions about what may happen next. The commentators should create anticipation and drama as well as describe events. Contextual conversation is a core requirement, not an optional polish pass.

## 1. Baseline and diagnosis

The reference is the fresh-season West Ham 4–4 Bournemouth recording, `match_2026_18_3`, and the user's timestamped review, rated **54/100**. Keep this video, script, audio and review notes unchanged as the comparison baseline.

| Measurement | Observed baseline |
| --- | --- |
| Script allocation | 50 slots |
| Published speech | 49 clips, 123.95 seconds in a 310.9-second video: 39.9% speech density |
| Writer decisions | 15 model lines accepted; 35 factual fallback lines; 35 candidate-rejection records |
| Rejection findings | 14 candidate records mention unsupported possession actions; 7 mention gender errors; 4 mention partner-name errors; eight records flag repetition. Records can contain multiple reasons. |
| Timing | Zero clip overruns or overlaps; goal voice onset approximately 15–19 ms after its event anchor |
| Buildup coverage | Six of eight goals have buildup under the existing audit definition |
| Reliability | A 0.8-second optional “Gerow!” slot stopped synthesis; review delivery required omitting that slot and resuming with 39 cached clips |
| Automated correctness blind spot | “West Ham level it. 1–2” passed the existing validator at video time 173.8 seconds |
| Media preservation | Source video packets preserved when adding commentary |

Machine-readable measurements and artifact locations: [baseline evidence](evidence/commentary_research_baseline_2026_10_15.json). The TTS run report was overwritten during the resumed batch; its elapsed time must not be presented as total synthesis time for the whole match.

### Confirmed code findings

- `llm/validator.py` checks numeric score strings but does not verify the meaning of “equaliser,” “ahead,” or “pull one back.” Its score regex is single-digit, and reversal is accepted without binding numbers to teams.
- `llm/prompts.py` omits the slot's match minute and before/after goal context from the writer's `live` object. `story_stats.py` does not provide a useful past-only comeback summary to the writer.
- `llm/client.py` has tiny analysis fallback pools, includes “A narrow lead” and “A fresh contest,” and gives half/full-time scores awkward team bindings.
- `llm/writer.py` checks repetition before fallback replacement. The replacement can repeat earlier fallback text without another repetition gate; length alternatives are not treated as separate editorial candidates.
- `planning/slot_allocator.py` searches backwards from known goals for the future scorer, rather than independently planning observed attacks. Generic possession-in-attack events are not eligible for ordinary live slots. At 245–258 seconds the extractor produced turnovers, attacking control and a shot-release cue, but the only planned lead-in was 257.0–257.8 seconds.
- `understanding/danger.py` is not called by the orchestrator. It treats home as attacking negative X, whereas the selected recording's goal crossings show home scoring at positive X and away at negative X. Other extractor rules use different conventions. This is an integration/convention defect, not proof that every existing possession label is wrong.
- `tts/batch_runner.py` fixes speaker names but leaves sampling settings largely at model defaults, has no recorded per-clip seed or pronunciation profile, and does not pass the utterance's emotion through to the instruction helper. A failed optional clip aborts the batch.
- `quality.py` reports `all_script_variants_valid` using the same validator that missed the false equaliser. That flag is not an independent factual guarantee.
- `logic/clay_broadcast.py` explicitly renders `goals[:3]`. The missing full-time scorers are a layout limit, not missing canonical events.

The server log contains 50 completed generation requests, with median 10.57 seconds and p95 13.52 seconds; none exceeded 15 seconds in server generation time. This does not measure full HTTP latency, but the recorded rejections give stronger evidence for fixing the context/validation contract than blaming the model timeout alone.

## 2. Research and design decisions

### Preserve exact event alignment

MatchTime identifies temporal alignment as a major football-commentary problem. Footy already has recorded states and presentation timestamps, so preserve that advantage instead of estimating events from screenshots. This is our application of the paper, not a claim that its model has been evaluated on Footy. [MatchTime, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.99/).

Keep three clocks separate: simulation step, match clock, and video presentation time. Cards and inserted goal frames change video timing. The 90-minute match is shown in about five minutes, so a five-second spoken sentence can span substantial match action.

### Use supported speech controls; measure consistency

Qwen CustomVoice supports named speakers, instruction text and generation parameters. Ryan is an English preset; Aiden is described as an American English voice. Asking both presets for British delivery may be an unstable choice and needs an A/B listening test. The model's generation code exposes sampling controls for both the main and auxiliary speech generator. [Official voice documentation](https://github.com/QwenLM/Qwen3-TTS#custom-voice-generation), [generation implementation](https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py).

Use stable speaker profiles and deterministic per-clip seeds for repeatable experiments. A seed is not a speaker embedding, an accent lock, or a guarantee of identical speech across devices and package versions. Pin the runtime and record reproducibility limits. [PyTorch reproducibility guidance](https://docs.pytorch.org/docs/main/notes/randomness.html).

The inspected CustomVoice API does not document an SSML/IPA pronunciation interface. Do not assume tags will be interpreted. First test plain-text pronunciation aliases and controlled wording with the installed model. A custom voice/reference-audio experiment is a later option if preset consistency remains insufficient.

### Verify the local serving contract

Qwen documents non-thinking configuration, and llama.cpp documents constrained JSON, template configuration and request timing. Current upstream documentation is not proof that every option exists in the installed `b11433` binary. Probe that binary's capabilities, log actual responses and use a versioned adapter. Structured JSON constrains shape; it does not prove football facts. [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-9B), [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

### Normalize coordinates before describing attacks

GRF documents ownership, goal coordinates, game modes and observation mirroring. Use an explicit archive coordinate contract, not a club-specific comment or an automatic half-time sign flip. Verify mirroring and goal direction against saved observations for each supported recording version. [Official GRF observations](https://github.com/google-research/football/blob/master/gfootball/doc/observation.md).

### Treat audio analysis as assistance to listening

FFmpeg supplies loudness measurement/normalization and bounded tempo adjustment. The current mixer already targets −18 LUFS and −1.5 dBTP; measure the delivered file before changing those settings. Optional local ASR can flag missing words and corrupt score readings, but name transcription errors do not prove bad pronunciation. [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html), [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## 3. Proposed architecture

```text
Immutable trajectory + manifest + presentation timeline
    -> Coordinate adapter + observed event evidence
    -> Past-only match context and goal transitions
    -> Typed commentary intent + speech claims
    -> Lead/analyst dialogue planner + duration-aware slots
    -> Constrained writer + semantic checks + varied safe fallback
    -> Display text / spoken text normalization
    -> Voice profile + pronunciation map + bounded synthesis retries
    -> Clip fitting + event-driven crowd mix + copied video stream
    -> Independent checks + transcript + side-by-side review
```

New derived fields belong in commentary artifacts. Do not rewrite historical manifests, score events, native states, physics parameters or scorer attribution. Venue metadata for old recordings remains a separate, identified enrichment unless it was recorded at the time.

Proposed internal records:

- `GoalTransition`: event ID, source evidence, scoring side, score before/after, beneficiary versus scorer identity, goal category, match clock, prior deficits and verified current-match milestones.
- `LiveContext`: as-of time, period, last known owner, normalized attacking direction, territory, observed action evidence and already-established story facts.
- `CommentaryIntent`: speaker role, purpose, required claims, permitted observations, forbidden claims, urgency and duration budget.
- `SpokenClip`: display text, spoken text, normalization mappings, selected variant, template family, speaker profile, seed, model/runtime revisions, actual duration and fit result.
- `BroadcastContextSnapshot`: fixture/run/campaign identity, football-time cutoff, frozen player/team facts, prior results, scheduled fixtures, sourced form summaries and any timestamped other-match feed. Each claim records when it became knowable.
- `StoryCandidate`: player/team/competition topic, supporting fact IDs, freshness and novelty, estimated duration, expiry, interruption priority, and whether the proposed line is a fact, observation or opinion.

Use the evidence contract below for all factual speech, including filler. The model may choose supported topics, emphasis and approved phrasing, but cannot introduce new factual propositions. A regex blacklist or a model's self-assigned fact citations cannot establish arbitrary prose truth.

### Required evidence contract — no unsupported factual speech

The user's requirement is that the commentators must not make up players, records, results, streaks or events to fill time. Implement this as a data and text-generation boundary, not merely an instruction saying “do not hallucinate.” This is the default release mode for both commentary voices.

#### 1. Build a read-only fact ledger for the current moment

Each usable fact needs a typed predicate and value, entity IDs, source references, campaign/fixture scope, `available_at` time, validity/expiry rules and evidence grade. Only facts whose inputs were available by the slot's start may enter its ledger. A missing value is **unknown**, never zero or permission to invent it.

Sources have explicit precedence: canonical match events for score/scorer; frozen squad metadata for identity; eligible dated fixtures for form; synchronized other-match events for live updates. Contradictions quarantine the affected claim and produce a diagnostic. The language model never resolves conflicting scores or player identities.

Derived statistics carry their inputs and definition. “Three wins in a row” requires three eligible completed fixtures and the correct streak semantics; “unbeaten” is not a synonym for “winning.” “Last four appearances” requires appearance evidence, not just the team's last four games. A claim based on too little history must describe the actual sample or remain unavailable.

For this recording, the canonical goal at source step 1676 supplies the current home-away score 1–2 at video time 173.8 seconds. The derived goal category is `deficit_reducer`. The ledger does not permit `equaliser`, regardless of how fluent a suggested sentence sounds.

#### 2. Have the model select a speech plan, not invent facts

Pass the writer only the relevant as-of ledger, current role and topic history. Request a bounded structure such as:

```json
{
  "speaker": "Ryan",
  "act": "deficit_reducer_call",
  "claim_ids": ["current_goal.scorer", "current_goal.score", "current_goal.category"],
  "template_id": "pull_one_back_short",
  "delivery": "urgent"
}
```

Claim names here illustrate the interface, not an additional source of match data. The compiler resolves their values from the ledger. Reject unknown IDs, incompatible acts/templates, unsupported entities and extra fields that attempt to add facts. The approved template supplies wording; the model cannot quietly add “a hat-trick,” an assist, an injury or a prediction to it.

Apply this controlled realization to player profiles, form, tables, other results and score calls. Provide a broad, reviewed collection of sentence forms and multi-sentence topic combinations, with whole-match variety tracking. This preserves expressive selection and dialogue without relying on unrestricted prose as a source of truth. Free-text writing can remain a separate labelled experiment, but is not the default factual release path.

#### 3. Give opinions their own bounded representation

An opinion requires `kind=opinion`, supporting ledger facts, an approved opinion form and an explicit uncertainty marker. It must not contain invented supporting statistics, private intentions, injuries or future results. Examples include a conditional expectation about a team's prospects or a suggested tactical response to an observed pattern.

“I'd expect them to climb if they keep creating chances” may be eligible when the ledger supports current chance creation. “They will finish fourth” is not a known fact, and adding “I think” does not make an arbitrary claim acceptable. Do not invent numeric probabilities or claim an unimplemented forecasting model produced them. Future-result data remains inaccessible to the writer even when an opinion is requested.

#### 4. Compile, check and audit every published variant

The text compiler inserts canonical names, natural score wording and verified values into approved forms. It evaluates the template's preconditions and checks team bindings, before/after score meaning, clock compatibility and required uncertainty markers. Every primary, shorter alternative, fallback and spoken-text normalization must preserve the same supported meaning.

After selection, retain a sentence-to-claim audit trail: exact published text, template/act, claim IDs, source references, as-of cutoff, normalization mappings and reason for acceptance. Repetition controls operate on this actual selected text and its topic family. A fact ID is useful only when the sentence's meaning is constrained to that fact; attaching a valid ID to an unrelated free-text assertion is not sufficient.

Pronunciation aliases can change how a known name is spoken, but cannot change its player ID or the fact being expressed. Validate and log aliases separately. Treat automated speech transcription as an anomaly detector: it cannot guarantee that neural audio pronounced every name or score correctly. Critical audio examples still require listening before declaring the release reviewed.

#### 5. Fail safely while keeping the broadcast alive

Reject unsupported candidates before speech synthesis. Try another verified topic or approved variant within a bounded retry budget. When historical data is absent, discuss supported current-match context or ask a grounded analyst question; never manufacture form to satisfy a silence target. If nothing useful is supported, allow an explicitly classified pause with crowd sound.

The quiet-gap policy cannot override the evidence gate. Optional omissions must be visible, and a missing required goal call must prevent a complete-release status. Keep uncertainty attached to inferred observations: ball movement can justify an anonymous danger cue, but does not prove a shooter, pass intent, finish technique or defensive mistake.

#### Evidence-contract acceptance tests

- A player-age claim with no recorded age, an invented streak and an unsourced other-match score cannot compile.
- Changing today's database, a future fixture result or an unrelated season cannot change an earlier slot's eligible ledger.
- Correct score numbers paired with the wrong meaning, reversed team bindings, or a false milestone fail template preconditions.
- A supported claim ID attached to an unsupported act/template is rejected; all published clauses have provenance.
- An opinion cannot disguise an unsupported factual premise or a numeric forecast as casual chat.
- Shortening, repetition replacement and pronunciation normalization do not bypass the evidence gate.
- Starving the context provider of optional facts produces safe topic selection/omissions, not invented details, and leaves required event timing intact.

Scope of assurance: this design can enforce that released **text claims** originate from validated data and controlled realization. It cannot guarantee that the source database is flawless, that every derived rule is correct, or that neural speech never produces an audible error. Those require source-integrity tests, adversarial regression cases and audio review. Report them separately instead of claiming that a general language-model validator proves zero hallucinations.

## 4. Implementation sequence and acceptance gates

### Milestone 0 — Freeze evidence and make runs reproducible

- Preserve original and review-adjusted plans, scripts, clip metadata, quality report, source hashes and user feedback timestamps.
- Inventory actual model hashes, llama.cpp version, Python/Torch/CUDA versions and generation settings; reconcile stale entries in `versions.json` with the files actually used.
- Add run IDs, stage timing, structured failure reasons, bounded retries and resume checkpoints. Keep the language/speech GPU handoff.
- Separate writer failures into transport, timeout, JSON/schema, unsupported fact, repetition and duration categories. Do not merge them into one fallback counter.
- Create a frozen evaluation pack: the eight goals, intro, second-half restart, full-time and the known silence interval. Add event/score fixtures for scenarios absent from this match.

**Gate:** a retry reuses valid clips; an optional clip failure can produce an explicitly marked partial/review result without manual JSON editing. Required goal/whistle speech failure prevents claiming a complete release.

### Milestone 1 — Score, clock and semantic correctness

Main files: `schemas.py`, `understanding/story_stats.py`, new `understanding/match_context.py`, new `speech_text.py`, `llm/validator.py`, `llm/prompts.py`, `llm/client.py`.

- Compute goal categories using the scoring team's signed margin before/after: `opener`, `go_ahead`, `equaliser`, `deficit_reducer`, `advantage_extended`; retain magnitude and late/comeback qualifiers separately. An opener also takes the lead, but receives its own narrative tag.
- Validate transitions against canonical score deltas. Ambiguous or inconsistent events get a conservative factual line and diagnostic, never guessed scorer correction. Handle explicit own-goal beneficiary separately from named scorer if the source records it.
- Introduce natural score formatting with explicit perspective: home/away, scoring-team-first, or team-bound result. Support multi-digit scores and drawn scores; never reverse numbers without their team bindings.
- Supply before/after score, current minute/period and past-only comeback facts to both writer and fallback.
- Reject semantic contradictions in every alternative, including “level,” “ahead,” “winner,” “fresh contest” and premature conclusions in incompatible contexts. Keep a deterministic safe score clause for the first release.
- Replace ambiguous noun “lead” in spoken fallback wording. Use “one-goal advantage” where appropriate.
- Add versioned venue metadata with recording override first. Verify clubs against official sources; West Ham's venue can use [the club's London Stadium page](https://www.whufc.com/en/london-stadium). Unknown venues receive a natural home-team introduction, not an invented stadium.

| Situation | Intended outcome example |
| --- | --- |
| 0–0 → 1–0 | “West Ham open the scoring. One-nil.” |
| 0–2 → 1–2 | “West Ham pull one back.” Never “level.” |
| 1–2 → 2–2 | “They're level. Two-all.” |
| 2–2 → 2–3 | “Bournemouth go in front.” |
| 1–2 → 1–3 | “Bournemouth restore a two-goal advantage.” Only “restore” if the past supports it. |
| 3–4 → 4–4 at 87 minutes | “A late equaliser! Four-all.” Past-only context can mention recovering a two-goal deficit. |
| Full-time 4–4 | “Full time. West Ham four, Bournemouth four.” |

Examples describe intended meaning, not mandatory repeated strings.

**Gate:** the false equaliser is rejected in primary, short, emergency and actual spoken text. Home/away-swapped and multi-digit tests pass. Full-time facts never enter earlier context. The late equaliser gets a different context from an early equaliser.

### Milestone 2 — A complementary duo and richer safe language

Main files: `planning/slot_allocator.py`, `llm/director.py`, `llm/writer.py`, `llm/prompts.py`, `llm/client.py`, `llm/validator.py`.

- Make the director choose explicit roles: event, score consequence, observed sequence explanation, late-match context, recap or intentional silence.
- Ryan owns the event/score. Aiden must add a distinct supported proposition; repeating Ryan's scorer/score is not sufficient. If no useful extra fact is available, leave space.
- Build current-match facts from completed events: deficit history, verified score changes, elapsed phase and supported pass/shot sequences. An observed pass is not automatically an assist, and a coordinate estimate is not official xG.
- Remove the duplicate team announcement from the intro. Allow a short analyst greeting or initial context instead.
- Record template family and semantic topic across the whole match. Ban exact repeated analyst sentences in the evaluation match; apply cooldowns to phrase families and normalized n-grams. Exempt essential names and score facts from blanket novelty rules.
- Apply the repetition and meaning checks after fallback selection and after duration fitting, not only to the first model candidate.
- Provide several context-appropriate safe alternatives. Bounded repair gets one targeted error message and retry; prefer concise safe speech or intentional silence to repeated invalid prose.
- Tune prompts and validation together: allow a possession statement when possession is known, but require evidence for runs, pressure, finish technique and defensive mistakes. Do not solve high fallback rates by weakening the factual standard.

**Gate:** no exact repeated analyst sentence in the reference match; no goal follow-up whose only information is the same scorer/score; all alternatives retain correct propositions. Report acceptance/rejection reasons. Improvement in model acceptance is an observation, not a release quota.

### Milestone 2 extension — Stories and conversation during quiet play

Main files: new `understanding/broadcast_context.py`, new `planning/story_selector.py`, `planning/slot_allocator.py`, `llm/director.py`, `llm/prompts.py`, `llm/validator.py`, `quality.py`; read-only adapters to the existing match/campaign/player repositories.

**Editorial goal:** make the match enjoyable even between chances. Ryan follows the game and can introduce a topic; Aiden contributes a short interpretation or opinion. They can disagree mildly or raise a genuine question when there is a new supported point to make. Avoid a repeated question/answer formula, scripted partner-name exchanges, or statistics read without explaining their relevance.

| Topic | Useful material | Evidence and availability rule |
| --- | --- | --- |
| A player | Role, recorded age/attributes when available, season scoring record, current-match influence, a recent transfer | Use recorded or kickoff-frozen identity and records. Never read today's mutable player table as historical truth. |
| The team | Formation, previous results, home/away form, unbeaten or winless run, scoring/defensive record | Derive from eligible completed fixtures in this campaign/world before the football-time cutoff. Define streak type and sample size. |
| How the team plays | Verified tactical selections and observed current-match tendencies: possession progression, pass directions, repeated entries | Distinguish configured intent from behaviour actually observed. A formation alone does not establish pressing, philosophy or defensive vulnerability. |
| Other matches | A completed earlier result, a known upcoming fixture, or a timestamped score update | No live score report without a synchronized event feed. A parallel worker finishing first does not make that fixture's result available earlier in football time. |
| Stakes | Kickoff standings, qualification/relegation implications, provisional points if the current score holds | Recompute from the eligible table and announce provisional scenarios as such. Do not use the final season table. |
| Opinion and prediction | A cautious view on the next phase or possible season trajectory | Explicitly mark the line as analyst opinion/conditional projection, grounded in available evidence; do not assert future results as facts or invent numeric probabilities. |

Examples of tone and intent, **conditional on the required facts existing**:

- “Three goals in the last four appearances. You can see why they're looking for that player again.” The goals/appearances and current involvement both need evidence.
- “That's four league games without defeat coming into today. Keeping that run going would mean a lot here.” Specify pre-match versus current provisional streaks.
- “They've used the right side repeatedly in this half. I'd like to see Bournemouth react to that.” Requires observed entry/pass counts; the proposed reaction is an opinion, not a claim that a tactical change occurred.
- “Arsenal won earlier, so a point here would leave them…” Only when that result and the derived table implication were already available at this moment.
- “It's early in the season, but if they keep creating chances like these, I'd expect them to climb.” Requires supported chance creation and an early-season context; it is not a promised finishing position.
- For the known late comeback: “They've already recovered from two goals down in this game. Would you back against another chance?” Only after that recovery has happened; do not use it to predict the recorded equaliser in advance.

#### Context collection without retrospective spoilers

1. Build and freeze a commentary-side context snapshot at fixture kickoff. Include source IDs, football dates/event times, campaign identity and explicit unknowns. This needs no database migration for the first delivery: a versioned JSON sidecar can hold the snapshot.
2. Populate from immutable fixture manifests and genuinely historical snapshots. `checkpoint_campaign()` currently updates one snapshot per run/season; it is not a per-fixture time machine. Derive prior results from dated, run-scoped match records where valid, and freeze mutable squad/manager data for future fixtures. Do not claim historical attributes or table positions when they cannot be reconstructed safely.
3. Allow current-match observations to update as presentation time advances. Keep prior-season data only when campaign continuity and player identity are established.
4. A fresh four-fixture season sample may have no meaningful form or streak history at kickoff. In that case use current-match patterns, recorded roles, formation, known fixtures and conditional discussion; do not borrow statistics from the older unrelated season.
5. Separate `fact`, `observation` and `opinion` in the intent schema. An opinion can discuss a future possibility, but all supporting statistics must be past/current facts. Keep actual future results outside the writer's input.

#### Scheduling and interruption policy

- Measure gaps between **actual spoken audio**, not merely allocated slot starts. The reference has four inter-clip gaps above eight seconds, including **13.34 seconds from 244.47–257.8** and **10.26 seconds from 283.44–293.7**. These are speech gaps; the crowd bed still plays.
- Start with a gap-fill trigger around **4–6 seconds** of ordinary quiet play. Prefer one short **3–6-second** relevant contribution, or a brief two-voice exchange when there is room. Treat **8 seconds as a review threshold**, with a provisional goal of no unexplained ordinary-play speech gap over **10 seconds**. These are tuning targets on the compressed video clock, not a football broadcasting standard.
- Give the next meaningful live cue priority over a story. Avoid starting an extended profile during observed rising danger. Maintain a shorter complete alternative or a natural clause boundary so Ryan can return to action promptly. Never speed through, overlap or keep a stale story running over a goal.
- Do not shift hard event anchors to finish a filler. The interruption/fitting policy must record why a story was shortened, deferred or dropped. Require short exchanges rather than uninterrupted monologues; do not resume a deferred topic when later events make it irrelevant.
- Select stories by relevance, recency, novelty and available time. Use player/topic/template cooldowns across the full match and ensure consecutive fillers add different information. Do not always assign filler to Aiden or repeat a score summary whenever facts run out.
- Keep purposeful short pauses after major moments. A speech-density target is a diagnostic, not permission to chatter continuously. Evaluate eligible gap reduction and listener enjoyment alongside action responsiveness.

**Gate:** add a profile/form story when an eligible quiet gap and sufficient context exist; preserve goal/cue timing when that story is interrupted. Never emit an unavailable streak, future other-match result or definitive season prediction. Test a campaign with real prior results, the sparse fresh-season sample, simultaneous fixtures, missing metadata, and a dangerous attack that interrupts conversation. Report every gap above eight seconds with its classification and every unexplained ordinary-play gap above ten seconds as a review failure. Run listening comparisons for topic variety, relevance and drama, not just more words.

### Milestone 3 — Evidence-driven anticipation and usable windows

Main files: `understanding/event_extractor.py`, `understanding/danger.py`, `understanding/sequences.py`, `understanding/timeline_adapter.py`, `planning/slot_allocator.py`.

- Establish one tested direction adapter for territory, box entry, progression and shot projection. On the reference recording home scores at positive X; do not infer a universal half-time flip from real football conventions.
- Trigger on observed attacks independent of whether they eventually score: final-third entry, controlled box entry and supported shot release. Use hysteresis and event cooldowns to avoid repeated threshold chatter.
- Distinguish `observed_control`, `recorded_action`, `inferred_ball_release` and `canonical_goal`. Unowned dangerous balls can trigger “Chance here” without a named shooter. Failed inference must not become a factual shot or goal prediction.
- Add causal carry/progression evidence only after testing ownership, restarts, loose-ball intervals and opponent touches. Current ownership changes alone do not prove every transfer was an intentional pass.
- Connect the danger engine only after coordinate and evidence tests pass; preserve individual component values. Calibrate urgency with territory, trajectory, score importance and match phase rather than setting every goal to the same intensity.
- Plan attack clusters that yield space for escalation. Use measured speaker/name duration distributions, not a universal words-per-second constant. A 0.8-second name call needs a feasible tested short realization or deliberate omission.
- Integrate quiet-play stories from Milestone 2 with the same scheduler: filler yields first to an observed attack, and the gap-filling policy cannot suppress anticipation or delay decisive calls.
- Preserve hard goal anchors. For offline rendering, known segment deadlines can constrain fitting; they must not supply future scorers or outcomes to pre-event text. Keep detector/context/candidate generation prefix-invariant when the future of a replay is changed.

**Gate:** opportunities are detected for both scoring and non-scoring attacks; mirrored-coordinate fixtures behave equivalently; there are no pre-event scorer/outcome leaks. Inspect 245–258 seconds manually. Aim for usable anticipation before at least seven of the reference goals if observations permit; document exceptions rather than inventing a cue to reach a percentage.

### Milestone 4 — Consistent voices, pronunciation and resilient synthesis

Main files: `tts/worker.py`, `tts/batch_runner.py`, new `tts/voice_profiles.py`, new `tts/pronunciations.json`, `audio/processor.py`, `audio/mixer.py`, `audio/ambient_bed.py`, `quality.py`.

- Define two persistent voice profiles, each with a stable baseline and a small number of delivery tiers. Test native preset delivery against the current British-accent instruction; a prompt cannot guarantee an accent change.
- Derive a per-clip seed from stable content/profile/variant IDs. Pin and log both generators' sampling settings and runtime revisions. Include instructions, pronunciation revision, seed and settings in cache keys; synthesizing only a subset must not change other clips.
- Maintain display text separately from TTS text. Map names to approved spoken aliases using player IDs and full-word matches. For fictional generated names, choose a consistent reviewed pronunciation; do not claim an unverified etymologically correct one.
- Test Gerow, Sciancalepore, Zielinski, Munoz and the second-half restart line in multiple contexts and energy tiers. Normalize score language before synthesis. Do not inject unverified SSML tags.
- Add bounded quality retries for garbling, silence, inconsistent speaker delivery and duration. Keep the existing maximum 10% time compression as a ceiling, not a target. Never crop a name mid-word or move the goal to fit a clip.
- Optional clip failure emits a typed omission reason and continues. Missing required speech remains a visible failure/partial status. Resume must be an ordinary pipeline operation.
- Use optional ASR for lexical anomaly flags, RMS/peak/onset checks for audio integrity, and listening for pronunciation/prosody. A model transcript or speaker-similarity threshold is not a perceptual pass on its own.
- Measure final encoded loudness, true peak and speech/crowd balance. Drive crowd swells from canonical events and supported attack cues even when speech is omitted; retain the crowd asset attribution.

**Gate:** same-input cache reuse is stable in the pinned environment; changed pronunciation/profile invalidates affected audio only. Required calls remain intelligible and within budget. Both speakers are consistently distinguishable in a blind sample review. The garbled restart and repeated surname inconsistencies are resolved by listening, with no new clipped names.

### Milestone 5 — Complete cards and comparative delivery

Main files: `logic/clay_broadcast.py`, `quality.py`, review/export tooling.

- Replace the three-goal slice with a full-time layout that can display eight goals: use two compact columns and reduce secondary decorative space. For very high counts, paginate studio cards with matching timeline entries. A video card cannot scroll interactively.
- Keep longer names legible at 720p and 1080p. Test 0, 3, 8 and 12+ goals, long names, and both themes. Goal count must match the canonical event ledger.
- Extend the report with original slots, spoken clips, omissions, score-transition checks, observed-cue coverage, actual spoken text, repetition families, cache use, timing and model rejection reasons.
- Include quiet-play speech-gap distributions, maximum unclassified gap, story topic coverage, interruptions, context availability and clearly marked opinion lines in the review UI.
- Produce paired 20–30-second A/B extracts around the intro, first goal, 1–2 goal, silent attack, late equaliser and full-time. Randomize A/B labels for listening where practical.
- After short excerpts pass, generate the complete revised match and test a held-out game. Publish the new version beside the baseline with a reproducible run manifest and clickable transcript.

**Gate:** all eight goal entries appear in the final studio presentation; source physics and score hashes are unchanged. Commentary-only muxing preserves video packets. The separate visual-card revision is expected to change video packets and must be validated against its new silent source, not incorrectly compared to the old video hash.

## 5. Evaluation and release criteria

### Automated correctness gates

1. Score-transition matrix and property tests cover both teams, draws, multiple deficits, multi-digit scores and malformed events. Equaliser claims require equal scores; other goal meanings require the appropriate before/after margin.
2. Alternate-future tests preserve pre-event detector outputs, live facts and candidate text when the observed prefix is identical. Event-specific claims are unavailable before their evidence timestamp.
3. Each clip either fits its window or has an explicit allowed omission/failure result. No overlaps, hidden shifts, unknown audio substitutions or manual JSON repairs.
4. Goal reaction slots begin at canonical presentation anchors. Measure audible onset; target the baseline's responsiveness, with a provisional ≤100 ms onset gate and human verification. Onset thresholds do not prove intelligibility.
5. Validate actual spoken variants, not only the planned primary text. Report zero known score/context contradictions in the regression corpus; this is not a universal truth guarantee for arbitrary generated prose.
6. No exact analyst sentence repeats in the reference game, with semantics-based topic checks and editorial review for paraphrased echoes.
7. Source artifacts remain immutable; the report distinguishes commentary-only packet preservation from deliberately re-rendered studio cards.
8. Check real spoken gaps in eligible ordinary play. Flag over-eight-second intervals for review and reject unexplained over-ten-second intervals under the initial policy. Assertions distinguish intentional pauses, dropped optional speech, unsafe/unknown context and scheduling failures. A high overall speech density cannot conceal a long silent attack.
9. Context tests prevent current database state, unrelated campaigns, later other-match results and final season outcomes from leaking into earlier stories. Forecasts remain explicitly conditional and evidence-backed; fact validation does not simply ban every forward-looking opinion.

### Listening rubric — proposed target, not a promised score

| Dimension | Weight |
| --- | ---: |
| Factual correctness and useful live context | 25 |
| Timing, anticipation and rhythm | 20 |
| Voice stability, intelligibility and pronunciation | 20 |
| Complementary dialogue and variation | 20 |
| Match drama and relevance to the clock | 10 |
| Crowd/mix quality | 5 |

Use the same excerpts and questions for both versions. Ask the user for timestamped errors and comparative preference. A provisional target is **80/100**, with no critical factual contradiction; a weighted average cannot excuse a false equaliser or scorer. No listening score should be claimed from logs alone.

Use West Ham–Bournemouth as a regression fixture, not the entire benchmark. Add a held-out recorded fixture and focused synthetic commentary fixtures for 0–0, a one-goal match, late winner, early equaliser, away comeback, missing shooter identity, extra-time metadata when actually supported, and high goal counts. Synthetic commentary tests must be labelled and must not be presented as new native simulation evidence.

## 6. Delivery order, risks and decisions

| Delivery | Scope | Review artifact |
| --- | --- | --- |
| A | Milestones 0–1: provenance, goal meanings, clock and score speech | Corrected 1–2 and late-equaliser script/audio excerpts |
| B | Milestone 2: complementary roles, varied safe language and quiet-play storytelling | Intro, three goal/analysis exchanges, and player/team/form conversations in quiet phases |
| C | Milestone 3: coordinates, danger integration and scheduling | Observed cue trace and the 245–258-second attack comparison |
| D | Milestone 4: voice/pronunciation and normal resumability | Name/context listening pack and fit/omission report |
| E | Milestone 5: studio completeness and release evaluation | Full improved video, A/B clips, transcript and independent checks |

Voice micro-experiments can begin after A, while attack evidence is audited; do not spend a full-match synthesis pass after every prompt edit. First run deterministic tests and text validation, then short neural samples, then full-match delivery. Calibrate cue thresholds and voice settings on the laptop actually used; research model benchmarks are not local latency promises.

Main risks and responses:

- **Lower fallback rate but less truthful language:** retain claim provenance and hard score clauses; measure why candidates fail rather than optimizing an acceptance quota.
- **More speech but stale descriptions:** prioritize current attacks, expire old action claims, and evaluate silence during dangerous play separately from overall speech density.
- **Interesting stories but invented history:** freeze time-scoped context, track source IDs, and provide current-match discussion when season history is sparse. Keep other-match updates aligned to football time rather than worker completion order.
- **Stable but flat voices:** vary bounded delivery tiers while keeping identity stable; use paired listening tests instead of treating deterministic decoding as automatically better.
- **Incorrect inferred action:** preserve evidence grades and anonymous alternatives; no invented assist, body part, finish technique or defensive failure.
- **Accent/pronunciation experiments consume time:** use a small approved name set before any model switch or full re-synthesis. Base/VoiceDesign checkpoints are a later evaluated option, not a prerequisite.
- **Optional failure still blocks the match:** distinguish optional/required speech and make omissions auditable; exercise the 0.8-second failure in a resume test.

Retain current models for the first correctness/dialogue iterations. Consider a smaller writer, alternate voice model or reference-voice approach only after measured A/B trials establish a quality or runtime benefit. No automatic production model migration is part of this plan.

## 7. Task checklist

- [x] Read the user's timestamped review and verify baseline artifacts.
- [x] Inspect context, writer, validation, scheduling, speech and studio-card code.
- [x] Review primary model, serving, timing, audio and GRF documentation.
- [x] Record measured baseline and distinguish findings from hypotheses.
- [ ] M0: freeze versioned evaluation artifacts and implement normal resume/omission reporting.
- [x] M1: implement goal-transition context, semantic score checks and natural speech formatting.
- [x] M1–M2: enforce the time-scoped fact ledger, structured speech acts, controlled realization and sentence-to-source audit for all factual dialogue and filler.
- [ ] M2: implement distinct dialogue roles, contextual fallbacks, full-match repetition tracking, time-scoped player/team/fixture stories and an interruptible quiet-play gap-filling policy.
- [ ] M3: unify coordinate interpretation and implement evidence-driven anticipation.
- [ ] M4: evaluate voice profiles, pronunciation normalization and bounded audio quality retries.
- [ ] M5: show every goal, generate paired samples, evaluate a held-out game and deliver the full revised broadcast.

The initial research pass changed documentation only. Subsequent authorized implementation extends the existing commentary edits; the published baseline review remains untouched.


## Implementation progress — 15 October 2026

The first correctness milestone is implemented on `codex/commentary-grounding`.
The earlier planning-only status describes the research pass; runtime changes are
now in progress. The recorded baseline review remains unchanged.

- [x] Canonical, time-scoped evidence ledger and controlled factual sentence generation.
- [x] Model selection restricted to eligible template IDs; arbitrary prose and extra fields rejected.
- [x] Score transition classification, natural number wording, late equaliser context and provenance validation.
- [x] Historical snapshot adapter rejects wrong-run/hash bindings, duplicate results and retrospective snapshots; later results cannot supply pre-match stories.
- [x] Ordinary attack cues use observed events; danger calculation is wired into extraction with tested mirrored-coordinate behavior.
- [x] Quiet-play role/formation topics and whole-match exact analyst-sentence cooldowns.
- [x] Content-checked script resume, stable clip seeds, versioned delivery settings and explicit optional speech omissions.
- [x] Adversarial regression coverage, including invented claims, forged citations and tampered script checkpoints.
- [x] Finish automated full-run audio verification and export an evidence-linked review page.
- [ ] Collect the user's new listening review and use it to calibrate remaining dialogue/voice work.
- [ ] Broaden contextual storytelling from actual historical snapshots and evaluate source-derived current-match story variety.
- [ ] Calibrate pronunciation/voice delivery with listening; add only reviewed aliases.
- [ ] Complete the full-time card layout and remaining release-evaluation gates.

The historical snapshot is an explicit trusted input boundary, not independent
proof that upstream records are correct. Unrestricted free-text factual narration
is not used in the default release path. The broader M0/M2–M5 checkboxes remain
open where their full acceptance gates have not yet been met.

Verification: [first milestone evidence](evidence/commentary_grounding_verification_2026_10_15.json). Backend: 177 passed, 11 environment-dependent skips. Commentary: 52 passed. The new review has 59 voiced clips and eight story segments; the longest measured inter-clip gap is 8.029 seconds, versus 13.34 seconds in the baseline. This is not a new human quality score.
