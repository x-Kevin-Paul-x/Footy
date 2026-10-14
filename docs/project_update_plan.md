# Footy project update plan

Prepared: 13 October 2026

Implementation followed this planning baseline. See [current status](05_current_status.md) and [dated verification](verification_2026_10_13.md) for delivered changes, measured results and remaining native-engine limitations.

## Objective and scope

Turn the supplied project review into an executable roadmap: protect saved data, make long-running jobs reliable, demonstrate the AI and simulation claims, and prepare a reproducible release before expanding gameplay and the economy.

This is a planning deliverable. Findings below come from reading the current source, workflows, tests, and documentation; no application changes, migrations, tests, training runs, or new season simulations were executed. Existing test counts and season results are historical evidence, not newly verified results. The review's scores are subjective estimates and are not acceptance criteria.

Assumption: one developer, reliability and evidence first, with no fixed delivery deadline. Effort ranges are working days of implementation and verification, excluding unattended training, long GRF runs, and hosting decisions.

## What the supplied review gets right, and what has changed

| Review recommendation | Current evidence | Planned response |
| --- | --- | --- |
| Add the missing MIT license | `LICENSE` exists. | Verify ownership, third-party notices, and README links; do not create a duplicate. |
| Add CI and API tests | `.github/workflows/ci.yml` and API regression suites exist. Backend CI selects three suites and does not run the advertised lint, typing, or coverage gates. | Extend coverage and required checks; confirm an actual passing workflow before updating claims. |
| Introduce SQLAlchemy and foreign keys | ORM models/repositories exist; `database/session.py` enables foreign keys, WAL, and busy timeout. Raw SQL remains in schema setup and a report route. | Finish repository boundaries and migration ownership. Retain the SQLite backup API for consistent snapshots. |
| Stop wiping every simulation; add saves | The normal `_run_main` uses run IDs without calling the old reset helper. Save/load endpoints and WAL-safe snapshots exist. A legacy initializer and `run_3_seasons.py` still contain resets. | Isolate destructive tooling; verify run/report/world-state isolation and what save/load actually restores. |
| Integrate Alembic | Six revision files exist. The first creates only report tables; the next alters `Match`, so the fresh-install chain is structurally incomplete. The September audit also records this failure. | Prove empty and legacy upgrades on isolated databases, then make Alembic the production schema authority. |
| Add concurrency protection | An `asyncio.Lock` exists, but submission returns before creating the run and protection is process-local. | Persist acceptance and worker ownership; support restart reconciliation and concurrent API processes. |
| Add action masking | `DQNAgent`, `FootyEnv`, training, and manager selection contain masks. | Test behavior across exploration, greedy selection, learning targets, and production transfer decisions. |
| Remove unused tabular RL | `ManagerBrain.select_action` actively falls back to tabular Q-learning for decisions outside its DQN path. | Document policy scope and dependencies before choosing whether to replace that fallback. |
| Publish trained weights | `dqn_best.pt` and `dqn_final.pt` are tracked in Git. | Add hashes, provenance, compatibility information, and reproducible evaluation; use release hosting if needed. |
| Add injuries, suspensions, substitutions, and variable home advantage | These mechanisms exist in the older `models/match.py` / `models/player.py` path. The latest GRF verification explicitly says native substitutions are unsupported. | Verify which mechanisms reach the active GRF season path; implement missing integration rather than duplicate legacy features. |
| Delete root npm files and move docs | Root npm scripts launch both apps, so the package is used. Audits/plans are already under `docs/`; a root image and duplicated dependencies remain. | Preserve useful launchers, prune proven-unused dependencies, consolidate docs, and repair links when renaming. |
| Add a dashboard GIF | README already contains a match GIF, screenshots, and recorded match assets. | Add a short dashboard walkthrough only if it demonstrates a missing user journey. |

Starting references: [current status](05_current_status.md), [backend remediation checklist](Backend_audit_PLAN.md), [earlier improvement plan](improvement_plan_2026_09.md), and [latest season verification](fresh_season_verification.md). The September status documents must be reconciled with later source changes rather than copied as current truth.

## Phase 1 — Establish one accurate baseline

**Priority:** P0. **Effort:** 1–2 days. **Dependency:** none.

1. Create a capability matrix with implemented / partial / absent / unverified states, source location, test evidence, engine mode, and verification date.
2. Reconcile README, current-status page, audit report, and existing plans. Keep the original audit as a dated historical record; make this roadmap and the updated status page the execution references.
3. Replace static test totals and broad determinism/performance assertions with dated, reproducible evidence. Keep native GRF physics, synthetic orchestration, management DQN, and TiKick player policies clearly identified.
4. Document limitations: unsupported native substitutions, untracked assists, artifact retention, required WSL/GRF runtime, and incomplete job/migration behavior.
5. Capture backend/frontend checks and dependency versions in an isolated environment. Separate unavailable native checks from passing checks.

**Completion gate:** every prominent README claim has evidence or an explicit limitation; a fresh contributor can identify the supported engine and setup path.

## Phase 2 — Complete persistence and job reliability

**Priority:** P0. **Effort:** 6–10 days. **Dependency:** Phase 1 baseline.

### 2A. Make migrations and saves dependable

- Repair the migration bootstrap while preserving compatibility with deployed revision histories. Define an explicit adoption path for unversioned databases created through `create_all`.
- Test empty-to-head and representative existing-database upgrades before removing runtime `ALTER TABLE` patches. Use SQLite batch alterations, consistent backups, integrity checks, and foreign-key checks.
- Move business queries, including the season-report transfer lookup, into SQLAlchemy repositories. Keep raw SQLite limited to documented administrative/backup needs.
- Quarantine reset helpers and make stress-test scripts use dedicated data/report directories. A test run must never reset the active user's database.
- Define save semantics: a database snapshot, a complete campaign save, and a resumable job are different capabilities. Verify calendar, squads, finances, manager state, RNG state, and retained media before claiming full campaign restoration.
- Separate history retention from media retention. Preserve the current configured media policy unless deliberately changed; show expired media clearly and allow selected saves/runs to retain necessary artifacts.
- Audit run scoping beyond matches: reports, standings, transfers, mutable squads, and finances must not mix two campaigns or overwrite reports from the same year.

**Completion gate:** a clean install reaches migration head; legacy saves upgrade without losing rows; save/restore reproduces the supported state; starting run B does not corrupt run A's retained history.

### 2B. Make simulation and evaluation jobs durable

- Persist a queued job before returning HTTP 202. Return `run_id` or `job_id` plus status/result locations.
- Implement explicit queued, running, completed, failed, cancelled, and interrupted transitions; database-backed ownership leases; heartbeat expiry; request idempotency; cancellation; restart reconciliation.
- Default to one season job operating on a campaign at a time. Coordinate this in the database across API processes; do not rely on a module-level boolean.
- Fix the fixture dequeue/ownership race in `simulation_process_pool.py`: supervisor-owned assignment before dispatch, bounded retries, and one terminal result/publication per fixture.
- Use the same lifecycle pattern for ML evaluation. Run synchronous episode work in a bounded executor and constrain models to registered IDs under the configured model directory.
- Update `frontend/src/services/api.ts`, simulation state, and `MlBenchmarks.tsx` to follow job status. The ML page currently expects an immediate report from an asynchronous acceptance response.
- Add schemas for remaining public responses and a consistent error envelope. Catch specific expected failures; retain a logged top-level unexpected-error boundary.

**Completion gate:** concurrent submissions, two API processes, refresh, cancellation, API restart, and worker death behave predictably; accepted IDs exist immediately; evaluation does not block health/status requests.

### 2C. Close artifact correctness gaps

- Make file containment checks consistent across recording/model/artifact entry points, including Windows drive paths, encoded traversal, and symlink/junction escapes.
- Remove implicit pickle loading from normal archive readers. Preserve old recordings through an explicit trusted conversion path with versioned output.
- Make match-to-video updates repository-owned and run-scoped; verify domain and ORM `Match` types cannot be confused.
- Keep published video URLs unset until successful atomic publication. Generate presentation timestamps from actual renderer output, and validate decoded frame count/duration before publishing the video and timeline together.

**Completion gate:** malformed paths/archives fail safely; duplicate match numbers in different runs stay isolated; interrupted rendering preserves good output; event seeking matches both 2D and 3D media.

## Phase 3 — Make routine verification reproducible

**Priority:** P1, started alongside Phase 2. **Effort:** 3–5 days. **Dependency:** baseline; final gates follow Phase 2 contracts.

1. Make editable installation work in a fresh environment. Align `pyproject.toml` with actual runtime dependencies; move test tooling into development dependencies and make ML/native requirements explicit. Remove manual path workarounds only after installed entry points and imports pass.
2. Add meaningful API contract and failure tests for jobs, save/load, migrations, and artifacts. Extend existing suites rather than recreate them.
3. Add a small isolated season integration test and invariants: points = 3 × wins + draws, played = wins + draws + losses, league goals-for = goals-against, unique fixtures, valid ownership and balances.
4. Run the full portable backend suite with coverage; run Ruff, scoped/static typing checks, frontend lint/tests/typecheck/build, and deterministic `npm ci`. Expand typing coverage incrementally with a recorded baseline.
5. Put native GRF/replay/recovery checks in an appropriately configured runner or scheduled/manual integration job. Required release checks must state exactly which native tests ran.
6. Add pre-commit hooks matching the fast CI checks, plus `CONTRIBUTING.md` with platform-specific commands.

**Completion gate:** supported fresh environments install without manual `PYTHONPATH`; required CI passes; critical failure cases are covered; skipped native tests are visible rather than counted as verified.

## Phase 4 — Make AI and performance claims measurable

**Priority:** P1. **Effort:** 4–7 days plus training/evaluation runtime. **Dependency:** reliable jobs and portable checks.

### Manager DQN evidence

- Document the actual 24-value observation and five transfer/scouting actions, their meaning, reward, and limitations. The local RL guide's tactical example is not the current implemented action space.
- Explicitly distinguish the manager DQN from the TiKick policy controlling players inside GRF. Record whether results use fast mode or real GRF; do not present fast-mode scores as native match-engine validation.
- Compare DQN against random-valid, do-nothing/static, youth-focused, and an explicit rule-based transfer policy using identical initial conditions and held-out seed lists.
- Start with 10 held-out seeds, then expand to at least 30 independent evaluation scenarios and several training seeds if variance warrants it. Report sample sizes, mean, standard deviation, uncertainty, points, rank, and financial outcomes.
- Seed environment creation, episode reset, Python, NumPy, Torch, exploration, and worker assignment; save seeds/configuration, commit, dependency versions, and model hash with raw reports.
- Reject missing/incompatible model weights rather than silently labelling initialized weights as trained.
- Add action-mask tests at budget thresholds, closed windows, squad limits, exploration/greedy selection, and next-state learning targets. Always retain a legal fallback action.
- Save training curves and publish a README results table linked to raw reports. Report negative findings honestly; a fixed win-rate improvement is a research target, not a release requirement.
- Keep tabular behavior documented until replacement coverage exists. Choose a deliberate supported fallback policy and migrate persisted policy data before deleting the old path.
- Add model provenance, checksum, architecture/version, training command, and usage terms. Release-host weights only if size or distribution needs justify it.

### GRF throughput evidence

- Repair `backend/benchmarks/benchmark_harness.py` so worker counts actually dispatch through the real pool. Its present fixture loop is sequential even when the result labels vary workers.
- Measure cold startup, warm execution, archive writing, native replay, and encoding separately on a fixed seeded corpus. Record requested/observed concurrency, throughput, p50/p95 latency, memory, storage, failures, and canonical hashes.
- Keep synthetic smoke tests as orchestration checks and label them clearly. Attach hardware/configuration details to performance claims and confirm identical canonical results across worker counts.

**Completion gate:** another contributor can reproduce the reported policy comparison and benchmark configuration; models cannot be mislabelled; concurrency is observed; statistical improvement is claimed only when supported.

## Phase 5 — Calibrate and complete the active simulation path

**Priority:** P2. **Effort:** 7–12 days initially; native substitutions may require a separate feasibility spike. **Dependency:** reliable persistence, repeatable seeds, and validated canonical statistics.

1. Measure the active GRF engine before tuning. The latest recorded season has 1,874 goals in 380 fixtures, approximately **4.93 goals per match**; this is evidence to investigate, not a new benchmark run.
2. Select a named real competition and seasons, retrieve attributable data, and derive comparison ranges for goals, home/draw/away rates, shots, xG, cards, and score distributions. Treat numbers in the pasted review and local balancing guide as provisional targets until this reference is fixed.
3. Verify stat extraction before parameter changes. Separate metric-attribution errors from policy/physics differences; never edit final scores to force agreement.
4. Stage workloads: 100-match diagnostic corpus, one full season, then 5–10 seeded seasons; run a larger 100-season study only if uncertainty remains and measured cost is acceptable. Limit full-state/media capture for calibration and record storage budgets.
5. Make suspensions and injury recovery persist across fixtures, save/load, and season boundaries. Test lineup exclusion and serving bans correctly, including red-card handling and non-playing injured players.
6. Prototype native substitutions against GRF's actual player/roster controls. Confirm identity, stamina, stat attribution, archives, and replay compatibility; if unsupported, keep that limitation explicit and schedule the engine work separately.
7. Implement in-match tactical changes and test that they reach the active policy/engine. Calibrate home advantage only through mechanisms this path supports, avoiding an unused legacy multiplier.
8. Extend the existing event transport with versioned discriminated payloads for match and season events, including run/match identity and ordering. Preserve a human-readable log alongside the typed stream.

**Completion gate:** a published calibration report states engine/configuration, reference data, uncertainty, and remaining discrepancies; availability/tactical changes persist correctly; deterministic reruns and replay/stat correspondence remain intact.

## Phase 6 — Package a credible release and demo

**Priority:** P1 for core release; gameplay additions need not delay it. **Effort:** 2–4 days. **Dependency:** Phases 1–4; accurately state Phase 5 limitations.

- Consolidate audit/status/roadmap links. Rename the spaced plan filename only after updating internal links and marking archived material.
- Keep the root npm launcher; remove dependencies only after confirming no code or tooling uses them. Move `image.png` if referenced and update those references.
- Add contribution guidance, issue templates, changelog, and setup commands for Windows and Linux/macOS, including the supported native runtime requirements.
- Verify MIT statements and third-party GRF/TiKick/checkpoint notices and redistribution terms before distributing model/native artifacts.
- Check current tags/releases before choosing a version; `pyproject.toml` already declares 0.1.0. Prepare release notes, checksums, reproducibility commands, and known limitations.
- Prepare a clear repository description/topics and a short dashboard walkthrough. Draft a project post explaining measured results, surprises, and failures.
- Prefer a read-only demo with precomputed results/replays initially. Select hosting only after measuring native runtime, persistent storage, media size, and operating cost; live simulation hosting is a separate deployment decision.

**Completion gate:** a fresh clone reproduces documented setup; the chosen version has passing release evidence and traceable assets; the demo demonstrates only supported behavior. Publishing, hosting selection, and external posts are later implementation actions, not actions taken by this plan.

## Phase 7 — Expand economy and transfer mechanics

**Priority:** P3. **Effort:** 10–20 days for the initial increment. **Dependency:** core release, durable campaign state, and long-run verification.

1. Audit existing income, wages, valuation, and transfer-window behavior before adding replacements. `FootyEnv` already tests opening and closing its summer window.
2. Implement a financial ledger for attendance income, broadcasting allocations, sponsorship, wages, fees, and adjustments; expose explanations in club finances.
3. Align window dates with the campaign calendar. Add loans, release clauses, and sell-on fees one feature at a time, with schema migrations, domain rules, typed APIs, and UI.
4. Version the DQN environment/rewards if new mechanics change its decision space or budget dynamics; reevaluate affected checkpoints.
5. Run isolated 5–10-season stress tests for cash-flow reconciliation, inflation, squad positional depth, loans returning, youth replenishment, aging, retirement, history retention, and memory/storage growth.

**Completion gate:** contracts and balances reconcile; no systematic economic collapse or squad depletion; multi-season results remain readable; policy performance is reevaluated against the expanded rules.

## Suggested implementation slices

| Order | Reviewable change | Depends on |
| --- | --- | --- |
| 1 | Current capability matrix, README corrections, limitations | Baseline inspection |
| 2 | Fresh/legacy migration bootstrap and isolated migration tests | 1 |
| 3 | Repository queries, reset isolation, save/history semantics | 2 |
| 4 | Durable season submission/status/cancel contract and UI | 2–3 |
| 5 | Fixture ownership/retry race and crash tests | 4 |
| 6 | Durable ML evaluation jobs, model IDs, frontend polling | 4; reuse job lifecycle |
| 7 | Archive/path safety and run-scoped artifact persistence | 2–4; independent fixes can start earlier |
| 8 | Renderer-owned timeline and publication validation | 7 |
| 9 | Editable install, full portable CI, scoped lint/type checks, hooks | Start after 1; integrate throughout |
| 10 | Seeded DQN comparison, masks, model metadata and curves | 6, 9 |
| 11 | Real concurrent GRF benchmark and evidence updates | 5, 8–9 |
| 12 | Core release docs/assets and read-only demo package | 1–11 |
| 13 | Calibration, availability integration, typed events | 5, 8, 10–11 |
| 14 | Native substitution feasibility, then tactical/substitution increments | 13 |
| 15 | Financial ledger, windows, then contract features | 3, 12–14 |

Large rows should be split further when migrations, service logic, and UI cannot be reviewed clearly together. Extract API services around these changes after contracts stabilize; avoid making an unrelated module rewrite a prerequisite.

## Delivery expectations

- **Core reliability, evidence, and release:** roughly 16–28 developer days, allowing CI work to overlap the reliability changes.
- **Realism and active GRF gameplay:** another 7–12 days initially, with native substitution support estimated after the feasibility spike.
- **Economy expansion:** another 10–20 days for the first scoped increment.

Review scope and estimates after the migration and durable-job changes. Finish each phase with its recorded completion evidence; do not measure success by the original reviewer assigning a higher score.

## Immediate next milestone

Deliver an accurate status matrix, a tested empty/legacy migration path, and a simulation submission that returns a persisted run ID and survives refresh/restart predictably. This resolves the highest-impact trust and reliability gaps before spending time on new gameplay or presentation.
