# Implementation Plan

> **Implementation verification — 6 September 2026:** This file is the original target design and remains useful as the detailed specification. It is not a completion record. The current implementation is a mixture of verified, partial, and open work; see [05_current_status.md](05_current_status.md) for code-backed status and [Backend_audit_PLAN.md](Backend_audit_PLAN.md) for the remaining execution order.

## Current phase status

| Phase | Status | Main remaining acceptance criteria |
| --- | --- | --- |
| P0 correctness/data safety | Partial | Supervisor-owned fixture leases; fresh Alembic bootstrap; implicit pickle removal; complete media validation. |
| P1 orchestration/consolidation | Partial | Durable queued/leased jobs, immediate `run_id`, restart recovery, canonical artifact ownership. |
| P2 API/database/config | Partial | Service boundaries, unambiguous run-scoped resource IDs, consistent schemas/errors, single configuration source. |
| P3 replay/frontend | Partial | Renderer-exact timeline, AVI halftime stats, Axios settings integration, server-state consolidation. |
| P4 performance/product | Mostly open | Real concurrent GRF benchmark, measured tuning, browser-native 2D replay, analytics/inspection features. |

Reproduced checks: full backend suite **95 passed, 9 skipped**; frontend **6 tests passed**; TypeScript and production build passed; existing database is healthy at revision `879f4c01467a`; empty-database Alembic upgrade failed at `c7c6ac0ab9c1`. The smoke benchmark is synthetic and does not measure worker scaling.

This plan preserves current behavior wherever possible, fixes correctness and data-loss risks first, and delays performance work until the benchmark harness can prove an improvement.

Use a dedicated branch such as `codex/audit-remediation`. Before implementation, capture the current dirty working tree and decide which existing uncommitted changes belong in the baseline. Each phase below should be independently reviewable and revertible.

## Global execution rules

- Never update deterministic baselines simply because a test fails. First explain why behavior changed.
- Run all database and destructive failure tests against temporary directories.
- Store every simulated match under a run-scoped identity.
- Treat simulation success and render success as independent outcomes.
- Do not delete replay sources until the published video passes complete decode validation.
- Do not introduce GPU batching, persistent GRF environments, or more workers until the benchmark phase.
- Keep compatibility adapters temporarily, but route them into canonical implementations.
- Add schema migrations with SQLite-compatible `batch_alter_table`.
- Do not use the existing destructive initial Alembic migration against real data.

# P0 — Correctness, hangs, and data-loss prevention

## P0.1 — Generate valid football matchdays

**Dependencies:** None. This should be the first behavioral correction.

**Affected files**

- [league.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/models/league.py:72)
- [main.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/main.py:552)
- Relevant league/domain tests under `backend/tests/`

**Exact problem**

`League.generate_schedule()` creates every ordered pairing and globally shuffles the list. The season runner slices every ten consecutive fixtures into a supposed matchday. A club can therefore appear multiple times within one batch while another club does not play.

Pre-match training, youth generation, reinforcement, lineup selection, suspension handling, recovery, finances, and standings assume these slices are chronological rounds.

**Intended solution**

1. Replace global fixture shuffling with a circle-method round-robin scheduler.
2. Produce explicit `Round` or matchday collections:
   - each team appears at most once per round;
   - each pairing occurs once per half;
   - reverse fixtures occur in the second half;
   - home/away allocation is reasonably balanced.
3. Keep a flattened `schedule` compatibility view temporarily.
4. Give every fixture a stable ID derived from competition, season, home team, away team, and leg.
5. Change `simulate_season_with_transfers()` to iterate explicit rounds.
6. Apply weekly training, recovery, finances, and suspension service once per team per round.
7. Prepare a fixture only after preceding rounds have committed.
8. Remove the assumption that `len(teams) // 2` consecutive list entries define a round.

**Risks**

- All deterministic season results and fixture dates will change.
- Existing frontend ordering may assume a flat randomized list.
- Tests using current fixture numbers may require fixture-ID migration.
- Saved games may need a legacy schedule adapter.

**Tests**

- For 20 teams, assert 38 rounds, 10 matches per round, and 380 fixtures.
- Assert every team appears exactly once in every round.
- Assert each ordered home/away pairing occurs exactly once.
- Assert no duplicate fixture IDs.
- Assert home/away count balance.
- Simulate at least three rounds with instrumented teams and prove training, finance, recovery, and suspension updates occur once per round.
- Add deterministic scheduler tests using a supplied schedule seed.
- Add legacy-save loading coverage if schedules are serialized.

---

## P0.2 — Fix multi-season control flow

**Dependencies:** Prefer P0.1 first so the multi-season test uses valid rounds.

**Affected files**

- [main.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/main.py:736)
- [run_3_seasons.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/run_3_seasons.py:64)
- Multi-season tests

**Exact problem**

Final report generation and `premier_league.increment_season()` are nested under the exception handler for finalizing `SimulationRun`. A successful run therefore does not execute normal season rollover.

**Intended solution**

1. Reorganize `main()` into explicit stages:
   - begin run;
   - initialize/load world;
   - simulate one season;
   - finalize season report;
   - commit season completion;
   - roll over to next season;
   - finalize the overall run.
2. Put failure handling around each stage without nesting normal behavior under `except`.
3. Record `matches_played` from committed matches rather than `len(schedule)`.
4. Mark failed runs as `failed`, with a structured error field.
5. Advance contracts, ages, cards, injuries, youth, and season year exactly once.
6. Close transfer logs in `finally`.

**Risks**

- Previously dormant rollover logic may expose contract or retirement defects.
- Report uniqueness constraints may collide with repeated 2026 data.
- Current tests may have implicitly depended on a single repeated season.

**Tests**

- Run two shortened seasons in an isolated database.
- Assert years differ, match identities do not collide, and both reports remain queryable.
- Assert each player ages exactly once per completed season.
- Assert contracts decrement exactly once.
- Assert failed seasons do not increment the year.
- Assert rerunning finalization is idempotent.
- Add a regression test proving successful finalization executes report creation and rollover.

---

## P0.3 — Repair worker lease and terminal-result handling

**Dependencies:** None. Can run in parallel with scheduler work.

**Affected files**

- [simulation_process_pool.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_process_pool.py:88)
- [simulation_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_worker.py:159)
- [test_inflight_sigkill_recovery.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/tests/test_inflight_sigkill_recovery.py)
- [test_simulation_resilience.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/tests/test_simulation_resilience.py)

**Exact problem**

After repeated abrupt worker deaths, a fixture can be marked `FAILED` without producing a result or raising. The supervisor still waits for all fixtures forever. A worker also clears its in-flight entry before result publication, creating a lost-result window.

**Intended solution**

Introduce a small explicit lease protocol:

```text
QUEUED
→ LEASED(attempt, worker, started_at)
→ RESULT_PUBLISHED
→ ACKNOWLEDGED
→ SUCCEEDED

or

LEASED
→ RETRY_PENDING
→ LEASED

or

LEASED
→ FAILED_TERMINAL
```

Implementation details:

1. Assign every attempt a unique attempt ID.
2. Record the lease before performing any fixture work.
3. Put the result on the result queue before clearing the lease.
4. Let the supervisor acknowledge the result, then clear the lease.
5. Count terminal failures toward batch completion.
6. Raise a structured `BatchSimulationError` containing failed fixture IDs after cleanup.
7. Reject duplicate fixture IDs before starting workers.
8. Add initialization, fixture, idle, and total-batch deadlines.
9. Do not respawn a worker when the queue is drained and every fixture is terminal.
10. Explicitly close queues, pipes, and the multiprocessing manager.
11. Escalate from graceful termination to kill after a bounded wait.
12. Recycle a worker following native GRF exceptions.

**Risks**

- Multiprocessing ordering bugs are platform-specific.
- Manager proxies can themselves become failure points.
- Abrupt termination during queue publication remains subtle.
- More structured errors may break callers expecting a generic exception.

**Tests**

Inject failure at:

- immediately after dequeue;
- immediately after lease creation;
- during environment construction;
- during a step;
- during finalization;
- immediately before result publication;
- immediately after publication;
- after lease clearing;
- after retries are exhausted.

For each case assert:

- bounded completion;
- expected retry count;
- exactly one terminal state per fixture;
- no duplicate standings/result application;
- no surviving worker, manager, or queue feeder;
- no partial artifact marked ready.

Use explicit worker PIDs and synchronization events. Do not select an arbitrary Python descendant.

---

## P0.4 — Guarantee GRF resource cleanup

**Dependencies:** Coordinate with P0.3.

**Affected files**

- [simulation_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_worker.py:159)
- [simulation_process_pool.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_process_pool.py:88)
- [grf_sim_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/wsl_workers/grf_sim_worker.py:77)

**Exact problem**

Environment, archive, dump directory, policy state, and temporary artifacts are not managed by one failure-safe owner. Construction or finalization errors can bypass cleanup. Environment close is duplicated in some paths.

**Intended solution**

1. Add idempotent `SimulationWorker.close()` and `abort(reason)`.
2. Track which resources were successfully acquired.
3. Use `try/finally` or a context manager starting before archive/environment construction.
4. Close each resource independently so one close failure does not block others.
5. Preserve the original exception and attach cleanup errors separately.
6. Delete only staging artifacts; retain completed authoritative artifacts.
7. Mark the worker process unhealthy after a native failure and exit it after reporting.
8. Make `finalize()` produce data; make cleanup a separate guaranteed operation.

**Risks**

- GRF close calls may block.
- Calling close twice may expose native-library defects.
- Existing tests may depend on finalization performing cleanup implicitly.

**Tests**

- Constructor failure after archive creation.
- Environment creation failure.
- Step exception.
- Archive-close failure.
- GRF-close failure.
- Result serialization failure.
- Verify all handles close and temporary directories are removed.
- Verify cleanup errors do not replace the original simulation error.

---

## P0.5 — Correct canonical side handling

**Dependencies:** Capture deterministic baselines first.

**Affected files**

- [simulation_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_worker.py:262)
- [grf_core.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_core.py:104)
- Semantic/determinism tests

**Exact problem**

Away-team input is canonicalized and then passed through side-specific tactical mirroring again. Offensive tactical overrides can direct away players backward.

**Intended solution**

1. Define a documented canonical convention: both teams attack toward positive X during policy and tactical processing.
2. Make `apply_tactical_action_bias()` side-independent when given canonical data.
3. Mirror observations once when entering canonical space.
4. Mirror actions once when returning to physical GRF space.
5. Remove or rename `team_side` parameters that invite duplicate transformation.
6. Add helper functions for coordinate and action transforms rather than inline negations.

**Risks**

- Match results will change.
- Existing deterministic hashes will change.
- Some existing callers may pass physical rather than canonical coordinates.

**Tests**

- Round-trip observation and action transforms.
- Mirrored fixtures with home/away swapped.
- Extreme offensive, defensive, and pressing settings.
- Assert canonical “forward” always increases canonical X.
- Compare neutral tactics before and after to isolate unintended changes.
- Approve new deterministic baselines only after reviewing action traces.

---

## P0.6 — Correct event and statistic attribution

**Dependencies:** P0.5 and canonical match-result schema from P1.2 can be designed together.

**Affected files**

- [simulation_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_worker.py:270)
- [grf_sim_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/wsl_workers/grf_sim_worker.py:458)
- [grf_core.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_core.py)
- Football semantic/correspondence tests

**Exact problem**

Actions belong to the pre-step state, while ownership and coordinates used for classification often come from the post-step state. This misses released-ball actions and can attribute actions to the recipient or new owner. Goal fallbacks use post-goal coordinates.

**Intended solution**

Create a transition record containing:

- step and match time;
- pre-step owner/team/player;
- pre-step player and ball positions;
- selected actions;
- post-step owner and positions;
- score before/after;
- game mode before/after.

Split processing into:

1. `capture_intent(pre_state, actions)`;
2. `resolve_transition(intent, post_state)`;
3. `reduce_event(canonical_transition)`.

Shots should originate from the kicker’s pre-step location. Goals should link to a prior unresolved shot when evidence supports it. Own goals and uncertain attribution must be explicit.

**Risks**

- Historical statistics and event counts will change.
- Some GRF transitions may not expose enough information for certain attribution.
- Matching a goal to a prior strike requires a bounded, documented window.

**Tests**

- Shot releases possession.
- Completed and intercepted passes.
- New owner after tackle.
- Goal from a recent shot.
- Own goal.
- Goal with no identifiable striker.
- Simultaneous game-mode transition.
- Compare result score against GRF score for every seed.
- Ensure shots, xG, events, and replay banners use the same canonical event objects.

---

## P0.7 — Make video publication and retention safe

**Dependencies:** Establish artifact identity in P1.3; an immediate safety patch can precede full redesign.

**Affected files**

- [grf_native_runner.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_native_runner.py:287)
- [grf_renderer.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_renderer.py:450)
- [grf_render_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/wsl_workers/grf_render_worker.py:87)
- [match_manifest.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/match_manifest.py:226)
- [replay_encoder.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay/replay_encoder.py:32)

**Exact problem**

2D and 3D renders share filenames. Any nonzero MP4 is accepted as completed 3D. Partial files are written to final paths. Early AVI EOF can still produce a “finished” video and trigger source deletion.

**Intended solution**

1. Use run-qualified, mode-qualified artifact paths.
2. Add render identity fields:
   - simulation result hash;
   - source artifact hash;
   - mode;
   - resolution/FPS;
   - encoder;
   - renderer version;
   - overlay version.
3. Write to a uniquely named `.partial` file.
4. Close and reap the encoder deterministically.
5. Validate with `ffprobe`.
6. Decode the complete file with FFmpeg.
7. Check duration/frame count against the presentation timeline.
8. Hash the validated file.
9. Atomically publish using the existing manifest helper.
10. Only then update the database to `READY`.
11. Apply source retention in a separate transaction after publication.
12. Treat unexplained early source EOF as render failure.
13. Never infer mode from a filename.

**Risks**

- Existing video URLs change.
- Full decode validation adds latency.
- Existing artifacts lack provenance and need a legacy state.
- Cross-filesystem atomic replacement may not be possible.

**Tests**

- 2D then 3D with the same match.
- 3D then 2D.
- Nonzero truncated MP4.
- FFmpeg exits during intro, match, halftime, and final card.
- Early AVI EOF.
- Disk full during staging.
- Duplicate simultaneous render requests.
- Restart with `.partial` file present.
- Verify authoritative input remains after every failure.
- Verify only validated files become discoverable.

---

## P0.8 — Repair replay queue and encoder lifecycle

**Dependencies:** P0.7.

**Affected files**

- [replay_pipeline.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay/replay_pipeline.py:40)
- [persistent_replay_engine.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay/persistent_replay_engine.py:64)
- [replay_encoder.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay/replay_encoder.py:32)
- [test_simulation_resilience.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/tests/test_simulation_resilience.py:147)

**Exact problem**

Queue writes, sentinel insertion, and thread joins are unbounded. The consumer exits after recording an exception, leaving the producer capable of blocking forever. Encoder shutdown closes stdin and then calls `communicate()`, which needs runtime validation.

**Intended solution**

1. Introduce a shared cancellation/error event.
2. Replace unbounded `put()` with timed retries that inspect consumer health.
3. Make introduction, match, halftime, final, and sentinel writes use the same helper.
4. Use a bounded consumer join.
5. On failure:
   - signal cancellation;
   - stop producing;
   - terminate FFmpeg;
   - drain or discard queued frames;
   - join the consumer;
   - remove partial output.
6. Make encoder `close()` distinguish success, timeout, and abort.
7. Drain stderr safely to avoid pipe blockage.
8. Require a known zero exit code.
9. Move all acquired resources under one `ExitStack` or equivalent lifecycle owner.

**Risks**

- Thread/process shutdown races.
- Too-short timeouts could fail slow but healthy encoders.
- Error propagation may differ between software and NVENC.

**Tests**

Use a controllable fake encoder that:

- fails on start;
- fails after N frames;
- blocks during write;
- blocks during close;
- exits without consuming;
- fills a queue of size one.

Assert bounded failure and no remaining thread/process. Add a tiny real encode and full decode test when FFmpeg is available.

---

## P0.9 — Make persistence run-scoped and transactional

**Dependencies:** Stable fixture IDs from P0.1. Requires a migration.

**Affected files**

- [models.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/models.py:155)
- [match_db.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/match_db.py:10)
- [db_setup.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/db_setup.py:11)
- [api_fastapi.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/api_fastapi.py)
- Alembic versions
- Frontend API types and query keys

**Exact problem**

Match upsert identity uses season and match number, allowing one run to overwrite another. Reports and many queries are year-scoped rather than run-scoped.

**Intended solution**

1. Require `simulation_run_id` for new matches.
2. Add stable `fixture_id`.
3. Add unique constraints:
   - `(simulation_run_id, fixture_id)`;
   - optionally `(simulation_run_id, match_number)`.
4. Add match lifecycle/status and error fields.
5. Make events, shots, and artifacts belong to the canonical match row.
6. Upsert only within a run.
7. Add run ID to season/transfer report identity.
8. Add explicit current-run selection to frontend endpoints.
9. Backfill legacy rows into a `legacy` run.
10. Make match result, shots, events, and status commit in one transaction.
11. Do not update standings until the match result commit is accepted or idempotently recognized.

**Risks**

- Migration affects most read paths.
- Existing numeric match IDs remain ambiguous.
- Reports keyed only by year need compatibility handling.

**Tests**

- Two runs of the same season coexist.
- Same fixture retry within one run is idempotent.
- Events/shots are not duplicated after retry.
- Composite lookups never cross runs.
- Frontend switching runs returns the correct artifacts and reports.
- Migration tests from realistic legacy database snapshots.

---

## P0.10 — Replace unsafe save/load behavior

**Dependencies:** Coordinate with job lifecycle in P1.1.

**Affected files**

- [api_fastapi.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/api_fastapi.py:361)
- [session.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/session.py:11)
- Save API tests

**Exact problem**

The database operates in WAL mode, but save/load directly copies the main `.db` file. A live copy can omit committed WAL pages. Loading replaces the file while pooled SQLAlchemy connections may remain open.

**Intended solution**

1. Serialize save/load operations with a durable application lock.
2. Reject load while any simulation, render commit, or database mutation job is active.
3. Use SQLite’s online backup API to a temporary database.
4. Run `PRAGMA integrity_check` on the backup.
5. Atomically publish the save.
6. On load:
   - dispose the SQLAlchemy engine;
   - validate the selected save;
   - restore through SQLite backup or a safe staged replacement;
   - recreate engine/session bindings;
   - reopen and run integrity checks.
7. Generate collision-safe save IDs with UUIDs.
8. Store save metadata and schema version.
9. Return generic client errors while logging internal details.

**Risks**

- Engine disposal affects in-flight readers.
- Windows file locking can complicate replacement.
- Old saves may require schema migration after restore.

**Tests**

- Save while committed data remains in WAL.
- Concurrent readers during backup.
- Load while job active returns conflict.
- Interrupted backup/load.
- Invalid/corrupt save.
- Old schema save with migration.
- Repeated save within one second produces unique IDs.
- Assert restored content and foreign keys.

---

## P0.11 — Establish a safe migration baseline

**Dependencies:** Schema design from P0.9.

**Affected files**

- `backend/alembic/`
- [db_setup.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/db_setup.py:11)
- [session.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/session.py:47)
- Deployment documentation

**Exact problem**

The initial migration drops numerous existing application tables. Runtime startup also performs ad hoc column/index changes, producing two competing migration mechanisms.

**Intended solution**

1. Inventory supported database starting states.
2. Create disposable snapshots for each known state.
3. Choose one approach:
   - squash into a safe baseline for development databases; or
   - add a data-preserving transition plus explicit stamping instructions.
4. Never edit already-deployed migration history without documenting compatibility consequences.
5. Move all schema evolution out of `create_tables()`.
6. Keep `create_all()` only for isolated tests or a clearly defined new-database bootstrap.
7. Use SQLite batch migrations.
8. Add pre-migration backup and integrity guidance.
9. Fail startup when schema is unsupported instead of silently patching it.

**Risks**

- Highest database risk in the plan.
- Incorrect stamping can skip required changes.
- Batch table recreation can lose constraints if not inspected carefully.

**Tests**

For every fixture database:

- copy to a temporary directory;
- run upgrade to head;
- compare row counts and important values;
- inspect indexes, foreign keys, unique constraints, and nullability;
- run `foreign_key_check` and `integrity_check`;
- start the application against the migrated copy;
- test downgrade only if downgrade is officially supported.

# P1 — Job orchestration and subsystem consolidation

## P1.1 — Introduce durable simulation and render jobs

**Dependencies:** P0.3, P0.9, P0.10.

**Affected files**

- [api_fastapi.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/api_fastapi.py:250)
- Database models and Alembic
- New backend job service modules
- [Dashboard.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/pages/Dashboard.tsx:147)
- [useSimulationSocket.ts](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/hooks/useSimulationSocket.ts:5)
- [MatchVideoReplay.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/MatchVideoReplay.tsx:95)

**Exact problem**

Job ownership uses process-global booleans and asyncio locks. These disappear on restart and do not coordinate multiple API workers. Background tasks have no durable identity, heartbeats, cancellation, or reconciliation.

**Intended solution**

Add a `Job` model with:

- job ID and idempotency key;
- type and target identity;
- queued/running/succeeded/failed/cancelled state;
- progress/stage;
- attempts and lease owner;
- created/started/heartbeat/finished timestamps;
- structured error;
- result reference;
- cancellation request.

Create service methods for enqueue, lease, heartbeat, complete, fail, cancel, and stale-job recovery. FastAPI should return HTTP 202 with `job_id` and URLs. Workers, rather than request processes, execute the jobs.

Initially, a local single-host job worker backed by SQLite is sufficient. Keep the interface replaceable if Redis/PostgreSQL becomes necessary.

**Risks**

- Requires careful transactional leasing with SQLite.
- Jobs can be delivered more than once, so handlers must be idempotent.
- Background worker deployment becomes a new operational component.

**Tests**

- Duplicate idempotency key returns the same job.
- Concurrent lease attempts yield one owner.
- Worker death causes stale lease recovery.
- API restart preserves job state.
- Cancel queued/running/rendering jobs.
- Completion and failure events match polling responses.
- No duplicate match or artifact publication.

---

## P1.2 — Consolidate simulation implementations

**Dependencies:** P0.5 and P0.6.

**Affected files**

- [simulation_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_worker.py)
- [grf_sim_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/wsl_workers/grf_sim_worker.py)
- [grf_native_runner.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_native_runner.py)
- [simulation_process_pool.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_process_pool.py)
- [match_engine_grf.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/match_engine_grf.py)
- Engine equivalence tests

**Exact problem**

Single-match native execution and season batch execution implement football semantics independently.

**Intended solution**

1. Define `SimulationSpec`, `SimulationTransition`, and `CanonicalMatchResult`.
2. Create one `GRFMatchExecutor` responsible for:
   - environment configuration;
   - seeding;
   - policy reset;
   - canonical transformations;
   - step processing;
   - event/stat reduction;
   - final result construction.
3. Let single, daemon, dynamic-pool, and central-batch routes adapt their transport to that executor.
4. Normalize seed handling once.
5. Remove duplicated shot/xG/possession logic after equivalence is proven.
6. Version the result schema.

**Risks**

- Broad deterministic output changes.
- Worker serialization requirements may constrain class design.
- Native GRF objects cannot cross process boundaries.

**Tests**

- Same fixture/seed through every actual entrypoint.
- Exact action and score equivalence.
- Explicit tolerances for floating statistics, documented by field.
- Seeds below and above `2**31 - 1`.
- Worker-count/topology invariance.
- Cross-platform tests where GRF environments exist.

---

## P1.3 — Define one artifact package and lifecycle

**Dependencies:** P0.7, P0.9, P1.1.

**Affected files**

- [match_manifest.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/match_manifest.py)
- [grf_trajectory.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_trajectory.py)
- [grf_state_archive.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_state_archive.py)
- All runners/renderers
- Database artifact model and migration

**Exact problem**

The repository contains separate manifest concepts, run directories, compatibility copies, filename discovery, and file-existence-based readiness.

**Intended solution**

Create one artifact record/package containing:

- run and fixture identity;
- simulation specification/version;
- seed and engine build;
- canonical result hash;
- trajectory path/hash;
- dump/state path/hash;
- render variants and status;
- sizes and timestamps;
- retention class;
- failure details.

Use database lookup as the normal discovery path. Restrict filesystem scanning to an explicit legacy importer.

Write NPZ atomically. Replace object/pickle metadata with UTF-8 JSON and `allow_pickle=False` for new files. Validate trajectory, archive, payload, and match IDs together.

**Risks**

- Legacy artifact compatibility.
- Hashing large files adds cost.
- Moving files may invalidate stored URLs.

**Tests**

- Mismatched trajectory/archive IDs.
- Same-length artifacts from different matches.
- Hash mismatch.
- Interrupted NPZ write.
- Legacy import.
- Multiple render variants for one source.
- Retention deletion only after reference checks.

---

## P1.4 — Separate simulation from rendering

**Dependencies:** P1.1 and P1.3.

**Affected files**

- [grf_batch_runner.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_batch_runner.py:70)
- [simulation_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_worker.py:555)
- [grf_renderer.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_renderer.py)
- Replay pipeline and job service

**Exact problem**

A fixture worker remains occupied while capturing/transcoding video. A render failure is often swallowed after successful simulation, and season batches wait for presentation work.

**Intended solution**

1. Simulation worker produces the canonical result and selected replay source.
2. Persist simulation success transactionally.
3. Enqueue render variants as separate jobs.
4. Use an independently configurable render concurrency limit.
5. Return season simulation results without waiting for video.
6. Expose render progress and failure separately.
7. Allow rerender without resimulation.
8. Prioritize on-demand user renders over bulk background renders where appropriate.

**Risks**

- Frontend must accept results before video availability.
- Artifact retention must account for queued renders.
- Job ordering and backpressure require observability.

**Tests**

- Simulation succeeds while render fails.
- Retry render without changing match result.
- Cancel render without cancelling simulation.
- Season completes while render backlog remains.
- Priority and concurrency limits.
- Compare simulation throughput before and after.

---

## P1.5 — Fix daemon ambiguity

**Dependencies:** P1.1, P1.2.

**Affected files**

- [grf_native_runner.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_native_runner.py:175)
- [grf_sim_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/wsl_workers/grf_sim_worker.py:686)

**Exact problem**

The daemon processes one request synchronously. An incomplete request can block it. Client timeout is treated as “daemon unavailable,” after which the caller can launch the same simulation again against the same paths.

**Intended solution**

1. Use request/job IDs and length-prefixed messages.
2. Add maximum message size and read deadlines.
3. Return structured accepted/running/completed/error responses.
4. On ambiguous timeout, query the existing job rather than resubmit.
5. Prevent concurrent writes using idempotency and artifact leases.
6. Add daemon health and graceful shutdown.
7. Consider removing the custom daemon if the durable worker service makes it redundant.

**Risks**

- Protocol compatibility.
- Long-running synchronous GRF calls still require worker isolation.
- Socket retry logic can create new edge cases.

**Tests**

- Partial request.
- Oversized request.
- Client disconnect after acceptance.
- Response loss after completion.
- Duplicate request ID.
- Daemon restart.
- Assert one simulation and one artifact package.

# P2 — Database, API, and configuration cleanup

## P2.1 — Define repository/service boundaries

**Dependencies:** P0.9 and P1.2.

**Affected files**

- `backend/src/database/*.py`
- Domain models under `backend/src/models/`
- [main.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/main.py:340)
- [api_fastapi.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/api_fastapi.py)

**Exact problem**

Domain models persist themselves while orchestration performs bulk ORM sync and API code also issues raw SQLite queries. Errors are inconsistently swallowed.

**Intended solution**

1. Domain models remain persistence-free.
2. Repositories handle SQLAlchemy access.
3. Application services own transaction boundaries.
4. API handlers call application services.
5. Remove raw SQLite queries except carefully isolated backup/migration operations.
6. Use explicit exceptions:
   - not found;
   - conflict;
   - validation;
   - transient storage failure;
   - integrity failure.
7. Replace full matchday synchronization with incremental changed-entity persistence.
8. Stop identifying teams, players, and managers solely by name; use stable IDs.

**Risks**

- Large surface area.
- Domain code currently depends on immediate database-assigned IDs.
- Incremental writes can omit mutated state without change tracking.

**Tests**

- Repository integration tests against temporary SQLite.
- Transaction rollback after partial domain failure.
- Stable identity for duplicate names.
- Query-count assertions for important endpoints.
- Domain unit tests run without database imports.

---

## P2.2 — Standardize and version APIs

**Dependencies:** P1.1 and P2.1.

**Affected files**

- [schemas.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/schemas.py)
- [api_fastapi.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/api_fastapi.py)
- [api.ts](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/services/api.ts)
- [nginx.conf](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/nginx.conf:13)
- Vite configuration

**Exact problem**

Root and `/api/v1` routes coexist, response shapes differ, several failures return empty success data, and deployed proxy paths are inconsistent.

**Intended solution**

1. Define complete `/api/v1` resources for:
   - runs;
   - jobs;
   - seasons;
   - fixtures/matches;
   - teams/players;
   - artifacts/renders;
   - ML evaluations;
   - settings.
2. Add Pydantic request/response models everywhere.
3. Use consistent status codes and error envelopes.
4. Add pagination and filters.
5. Generate or validate TypeScript types from OpenAPI.
6. Keep root routes as deprecated wrappers for one migration period.
7. Use relative same-origin URLs in the browser.
8. Preserve `/api/v1` through nginx and proxy `/recordings` and `/ws`.
9. Add proxy forwarding headers and WebSocket timeout settings.
10. Fix immediate defects:
    - import `TransferHistory`;
    - remove undefined `clean_id` use;
    - validate render mode;
    - apply request bounds;
    - stop exposing raw exception strings.

**Risks**

- Frontend migration touches most pages.
- Compatibility routes can prolong duplicate logic.
- Generated types may require schema normalization first.

**Tests**

- OpenAPI schema validation.
- Backend/frontend contract tests.
- Every route’s success, validation, not-found, conflict, and internal error.
- Nginx integration matrix for API, recordings, ranges, and WebSocket.
- Remote-host browser configuration test.
- API deprecation tests.

---

## P2.3 — Consolidate configuration

**Dependencies:** API schema can proceed simultaneously.

**Affected files**

- [config.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/config.py)
- `.env.example`
- frontend settings modal and API service
- Docker files and Compose
- README/setup documentation

**Exact problem**

Settings are distributed across environment variables, settings JSON, localStorage, hardcoded defaults, and request fields. Several UI settings have no consumer. Configured simulation timeout is unused.

**Intended solution**

1. Define typed backend settings in one module.
2. Validate enumerations and numeric ranges on startup.
3. Categorize settings:
   - startup-only infrastructure;
   - persisted application defaults;
   - per-job overrides;
   - frontend display preferences.
4. Make precedence explicit.
5. Expose only safe application settings through the API.
6. Remove or wire inert frontend options.
7. Apply the timeout to job execution and record which timeout fired.
8. Update `.env.example` to match real defaults; resolve its current ten-season contradiction.
9. Record effective simulation/render settings in each job and artifact manifest.

**Risks**

- Changing precedence may alter runs.
- Secrets must never be returned through settings APIs.
- Environment-dependent tests need isolation.

**Tests**

- Settings precedence table.
- Invalid startup configuration fails clearly.
- Per-job overrides do not mutate global settings.
- Frontend changes affect actual behavior.
- Artifact manifest records effective values.
- Timeout test proves cancellation/cleanup.

---

## P2.4 — Define retention and cleanup policy

**Dependencies:** P1.3.

**Affected files**

- [db_setup.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/database/db_setup.py:117)
- [config.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/config.py:51)
- Artifact service and database model

**Exact problem**

Starting a new run deletes all previous run directories. Startup cleanup recognizes only selected temporary patterns. Database rows can outlive missing artifacts or reference stale files.

**Intended solution**

1. Stop unconditional prior-run deletion.
2. Introduce retention classes:
   - authoritative simulation source;
   - published render;
   - regenerable derivative;
   - temporary/staging.
3. Track size, last access, status, and references.
4. Add explicit cleanup jobs with age/size policies.
5. Protect pinned/saved runs.
6. Reconcile database and filesystem:
   - missing file;
   - orphan file;
   - stale partial;
   - corrupt published artifact.
7. Provide dry-run cleanup output before deletion.
8. Keep startup cleanup limited to provably temporary stale files.

**Risks**

- Storage use increases until policies are active.
- Incorrect reference counting could delete required sources.
- Legacy files need classification.

**Tests**

- Cleanup dry run.
- Pinned artifact retention.
- Queued render source retention.
- Orphan and missing-file reconciliation.
- Restart after partial artifact.
- Storage-limit eviction order.

# P3 — Replay and broadcast correctness

## P3.1 — Create one canonical timeline

**Dependencies:** P0.6 and P1.3.

**Affected files**

- [grf_trajectory.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_trajectory.py)
- [replay_schema.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay_schema.py)
- [grf_renderer.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_renderer.py:450)
- Replay pipelines
- [MatchVideoReplay.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/MatchVideoReplay.tsx:178)

**Exact problem**

Renderers calculate match minutes and halftime differently. Event seeking assumes linear minute-to-video duration despite introductions, halftime cards, goal holds, and replay inserts.

**Intended solution**

Define three explicit clocks:

- simulation step/time;
- football match time;
- encoded presentation timestamp.

During render, emit a presentation map containing:

- segment type;
- source step range;
- encoded start/end;
- match minute;
- associated event IDs.

Persist the mapping with the render artifact. The frontend seeks using presentation timestamps, not `minute / 90`.

**Risks**

- Existing videos lack maps.
- Variable replay inserts complicate segment construction.
- Changing FPS must resample rather than reinterpret time.

**Tests**

- No-event match.
- Multiple goals in one minute.
- Minute-90 goal.
- Extra inserted cards/replays.
- Seek each event and verify nearby decoded frames contain the expected overlay.
- Cross-renderer clock and half-boundary agreement.

---

## P3.2 — Correct halftime and cumulative statistics

**Dependencies:** Canonical event/stat reducer.

**Affected files**

- [grf_renderer.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_renderer.py:535)
- [replay_pipeline.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay/replay_pipeline.py:273)
- [persistent_replay_engine.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/replay/persistent_replay_engine.py:200)
- `grf_render_worker.py`

**Exact problem**

Legacy halftime cards use final match statistics. State renderers initialize shot counters but never update them.

**Intended solution**

1. Store cumulative snapshots at event steps or a canonical halftime snapshot.
2. Make renderers consume snapshots instead of independently deriving statistics.
3. Use final canonical totals at fulltime.
4. Remove invented fallbacks where the data is unavailable.
5. Make man-of-the-match an optional canonical result field rather than selecting the last scorer or a fixed lineup index.

**Risks**

- Older trajectories lack cumulative snapshots.
- Deriving possession from sparse samples may differ from prior reports.

**Tests**

- Synthetic match with known first- and second-half values.
- Assert halftime never includes second-half actions.
- Assert fulltime matches canonical database/API values.
- Short lineups and no-event matches.
- Cross-renderer golden card values.

---

## P3.3 — Correct 2D event timing and color

**Dependencies:** P3.1.

**Affected files**

- [grf_renderer.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_renderer.py:356)
- [grf_render_worker.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/wsl_workers/grf_render_worker.py)

**Exact problem**

Goal events are approximated from minute and stored one per derived step. OpenCV BGR frames are sent directly to RGB-oriented writers in several paths.

**Intended solution**

1. Use exact event step IDs.
2. Store lists of events per step.
3. Keep bounded minute conversion only for explicitly marked legacy events.
4. Clamp legacy minute 90 to the final valid step.
5. Establish an RGB encoder-boundary contract.
6. Convert BGR exactly once.
7. Add a team-kit collision rule and explicit branding metadata.

**Risks**

- Double conversion if an existing path already provides RGB.
- Exact event step availability varies in legacy files.

**Tests**

- Known red/blue/green pixel patches through every renderer.
- Two goals at one step/minute.
- Minute-90 goal.
- Goal banner and replay start at the intended frame.
- Legacy event conversion test.

---

## P3.4 — Improve archive format and safe deserialization

**Dependencies:** Artifact versioning from P1.3.

**Affected files**

- [grf_state_archive.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_state_archive.py)
- [grf_trajectory.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/grf_trajectory.py:240)
- Replay loaders and import paths

**Exact problem**

The archive index must fit a fixed 16 KB header and can fail at close after capture. New NPZ metadata uses object arrays loaded with `allow_pickle=True`; archive fallback and chunks use pickle.

**Intended solution**

1. Create a new versioned format:
   - fixed header with footer/index offset;
   - variable-size index;
   - bounded record lengths;
   - JSON metadata;
   - explicit compression;
   - checksums.
2. Write new NPZ metadata as JSON bytes and load with `allow_pickle=False`.
3. Restrict legacy pickle reading to an explicit trusted-local import command.
4. Do not automatically treat unknown magic as pickle.
5. Close readers through context managers.
6. Propagate fsync and finalization errors.
7. Clean temporary files when close itself fails.

**Risks**

- Backward compatibility.
- GRF state blobs may still be opaque engine-specific bytes.
- Format migration needs storage and time.

**Tests**

- Long archive exceeding the old header limit.
- Random access, corruption, truncation, oversized record, wrong magic.
- Interrupted write and close failure.
- New format rejects malicious pickle/object metadata.
- Trusted legacy conversion produces equivalent states.

# P3 — Frontend and product integration

## P3.5 — Repair simulation and ML job UX

**Dependencies:** P1.1 and P2.2.

**Affected files**

- [Dashboard.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/pages/Dashboard.tsx:147)
- [useSimulationSocket.ts](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/hooks/useSimulationSocket.ts:5)
- [MlBenchmarks.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/pages/MlBenchmarks.tsx:164)
- [api.ts](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/services/api.ts:485)
- Zustand store

**Exact problem**

Request acceptance is displayed as completion. WebSocket event shapes do not match. ML evaluation dereferences a missing report from a valid 202 response.

**Intended solution**

1. Add generated/central TypeScript types for `Job`.
2. Mutation success stores the returned job ID.
3. Display queued/running/rendering/failed/cancelled/completed states.
4. Parse the backend’s canonical event envelope.
5. Reconcile every event by refetching the authoritative job.
6. Use bounded polling when WebSocket is disconnected.
7. Invalidate run, season, match, and artifact query keys only after relevant terminal transitions.
8. Add retry/cancel controls where supported.
9. ML completion should fetch its report through the result reference.

**Risks**

- WebSocket delivery is not guaranteed; polling fallback remains necessary.
- Duplicate events must be idempotent.
- Navigation should preserve current job visibility.

**Tests**

- Accepted job is not displayed as complete.
- Completion, failure, cancellation, disconnect, reconnect, and out-of-order event.
- Page reload during a running job.
- ML accepted/completed/failure lifecycle.
- Busy/conflict response.
- Cache invalidation occurs once for the correct run.

---

## P3.6 — Consolidate frontend server state

**Dependencies:** P2.2.

**Affected files**

- [simulationStore.ts](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/store/simulationStore.ts)
- Dashboard, LeagueOverview, SeasonReports, TeamDetails, PlayerProfiles, ManagerProfiles, YouthAcademy, TransferMarket
- [api.ts](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/services/api.ts)

**Exact problem**

React Query, Zustand, and local page state own competing copies of seasons and reports. Errors are sometimes converted to `null`, stale requests can overwrite current selections, and full reports are repeatedly downloaded.

**Intended solution**

1. Use React Query for remote data.
2. Keep Zustand for UI preferences and selected IDs only.
3. Define shared query keys including run and season.
4. Let HTTP failures throw typed errors.
5. Distinguish not-found from transport/server failure.
6. Use abort signals and keyed requests.
7. Add summary and paginated endpoints so list pages do not require full report trees.
8. Remove redundant fetches and mutation logic.
9. Use explicit loading/error/empty/success components.

**Risks**

- Cache behavior changes across navigation.
- Some pages depend on fields only available in large reports.
- Query invalidation must include run identity.

**Tests**

- Rapid season A→B change cannot display A under B.
- Team and match route reuse.
- Empty repository and API failure for every page.
- Request-count assertions during initial dashboard load and navigation.
- Cache invalidation scoped to the correct run/season.

---

## P3.7 — Fix replay polling and stale media

**Dependencies:** Job API and artifact lifecycle.

**Affected files**

- [MatchVideoReplay.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/MatchVideoReplay.tsx:68)
- [MatchDetail.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/pages/MatchDetail.tsx:169)
- API service

**Exact problem**

Polling intervals can overlap. Backend `error` status is not recognized as frontend `failed`, so polling can continue forever. Previous-match video can remain visible after navigation.

**Intended solution**

1. Replace `setInterval` with completion-scheduled polling or React Query refetching.
2. Permit only one in-flight request.
3. Abort on route change/unmount.
4. Stop on every terminal state.
5. Back off and pause in hidden tabs.
6. Reset video and progress state when match ID changes.
7. Key every response by match/artifact ID before applying it.
8. Add video `onError` behavior and retry.
9. Use metadata-driven 2D/3D, resolution, encoder, and source labels.

**Risks**

- Longer backoff may delay visible completion.
- Browser autoplay and media range behavior vary.

**Tests**

- Slow 30-second response with 800 ms configured cadence still produces one request.
- Failure terminates polling.
- Navigate from recorded match to unrecorded match.
- Late response from previous match is ignored.
- Unmount cancels request and prevents state update.
- Video decode/network error is visible.

---

## P3.8 — Fix responsive formation and accessibility

**Dependencies:** None.

**Affected files**

- [FormationViewer.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/FormationViewer.tsx:213)
- [MatchVideoReplay.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/MatchVideoReplay.tsx:284)
- Shared UI components

**Exact problem**

Players use fixed `x * 600` positioning in a responsive container, clipping right-side players. Some custom media controls lack labels. Missing ratings are shown as invented `7.2`.

**Intended solution**

1. Render formation in an SVG with a stable viewBox or percentage coordinates.
2. Maintain pitch aspect ratio.
3. Scale token and text sizes within accessible limits.
4. Add accessible names, focus indicators, keyboard behavior, and reduced-motion handling.
5. Display unavailable ratings as unavailable.
6. Ensure color is not the sole indicator.
7. Test 320, 375, 768, and desktop widths.

**Risks**

- Label overlap at very small widths.
- Snapshot changes.
- SVG text rendering differs across browsers.

**Tests**

- All XI visible and within bounds.
- Keyboard-accessible controls.
- Accessible-name queries.
- Reduced-motion behavior.
- Color contrast checks.
- Long player/team names.
- Missing rating display.

---

## P3.9 — Remove fabricated and inert UI state

**Dependencies:** Configuration/API cleanup.

**Affected files**

- [HeaderSettingsModal.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/HeaderSettingsModal.tsx:35)
- [HeaderNotificationsDrawer.tsx](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/frontend/src/components/HeaderNotificationsDrawer.tsx:32)
- API/service configuration

**Exact problem**

Several settings only write localStorage and affect no application behavior. Notifications contain hardcoded fictional transfers, results, and model improvements.

**Intended solution**

1. Remove unsupported settings or clearly label local display preferences.
2. Wire supported settings to their actual consumers.
3. Populate notifications from job/run/event data.
4. Provide an honest empty state when there are no notifications.
5. Store notification acknowledgement separately from source event truth.
6. Do not let a saved API URL override deployment security without validation.

**Risks**

- UI temporarily appears less feature-rich.
- Persisted localStorage values need migration/removal.

**Tests**

- Each retained setting changes observable behavior.
- Notification list reflects backend events.
- Empty state.
- Read/unread persistence.
- Invalid stored setting falls back safely.

# P4 — Performance work after measurement

## P4.1 — Build the benchmark and correctness gate

**Dependencies:** P0 correctness tests should land first.

**Affected files**

- New benchmark package/scripts
- Existing profiling configuration
- CI configuration and documentation

**Intended solution**

Create repeatable benchmark commands with isolated output directories and machine/config manifests. Cover:

- worker counts 1/2/4/8/12;
- fixtures 1/10/38/100/380;
- steps 200/1,200/full;
- replay modes none/trajectory/archive/live/deferred;
- CPU-single/CPU-batch/CUDA-batch;
- software/NVENC;
- 720p/candidate 1080p;
- cold/warm process and environment startup.

Measure stage timings, throughput, p50/p95, CPU/RSS, GPU/VRAM, disk, IPC wait, database lock time, artifact size, and frontend network/rendering.

**Risks**

- Benchmarks become noisy if background workload is uncontrolled.
- GRF determinism can be confused with performance variability.

**Tests/acceptance**

- Five or more repetitions.
- Median, p95, and spread.
- Machine and dependency identity recorded.
- Correctness hashes required before comparing speed.
- Benchmarks never target normal data directories.
- CI uses a smaller smoke benchmark; full benchmarks run in the prepared GRF environment.

---

## P4.2 — Bound central batched execution

**Dependencies:** P0.3 and P4.1.

**Affected files**

- [simulation_process_pool.py](/C:/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/src/logic/simulation/simulation_process_pool.py:435)
- Policy backends

**Exact problem**

Central batching starts one process per fixture and synchronizes every active environment at each step.

**Intended solution**

1. Enforce `num_workers` as the maximum number of active environments.
2. Admit pending fixtures as slots complete.
3. Record per-worker step duration and barrier wait.
4. If measurements justify it, replace the full barrier with bounded ready-worker microbatches:
   - maximum batch size;
   - maximum wait time;
   - deterministic match ordering;
   - per-match recurrent-policy state.
5. Keep a strict deterministic mode.

**Risks**

- Batch topology can affect floating-point inference.
- Recurrent hidden-state association is critical.
- Ready-worker batching is substantially more complex.

**Tests**

- Active process count never exceeds the limit.
- Topology invariance for supported deterministic mode.
- Hidden-state isolation by match ID.
- Worker completion compaction.
- Compare throughput and tail latency against dynamic CPU pool.

---

## P4.3 — Evaluate persistent workers and environments

**Dependencies:** Reliable lifecycle and benchmark harness.

**Affected files**

- GRF native runner
- WSL workers
- process pool
- persistent replay engine

**Exact problem**

WSL, Python, model loading, worker creation, GRF environment creation, and renderer initialization repeat frequently.

**Intended solution**

Evaluate independently:

1. persistent WSL worker process;
2. persistent loaded policy;
3. persistent render environment;
4. persistent simulation environment reset.

Adopt each only if measured gains are meaningful and reset equivalence passes. Add maximum jobs per worker and RSS-based recycling.

**Risks**

- Native state leakage.
- Memory fragmentation.
- Seed/reset contamination.
- Persistent damaged workers.

**Tests**

- Cold versus warm equivalence.
- Same fixture after unrelated prior fixtures.
- Long sequence RSS trend.
- Forced worker recycling.
- Native crash followed by replacement.
- Compare throughput and p95 latency.

---

## P4.4 — Optimize rendering and encoding only from profiles

**Dependencies:** P0.7, P0.8, P3.1, P4.1.

**Affected files**

- Replay pipelines
- Renderer
- Encoder implementations

**Candidate changes**

- eliminate verified redundant color conversions;
- tune bounded queue size by measured memory and wait time;
- select software versus NVENC by benchmark;
- render at true target resolution instead of 720p followed by upscale;
- revise FPS only with presentation resampling;
- compare `/mnt/c` and WSL ext4 staging;
- cache immutable pitch/overlay assets;
- avoid repeated source decoding when one pass can feed overlay and encode.

**Risks**

- Video quality regression.
- Larger memory footprint.
- Hardware-specific behavior.
- Timing changes can break event alignment.

**Tests**

- Complete decode and frame count.
- Event timestamp accuracy.
- Golden overlay/color checks.
- Visual quality comparison on text and ball motion.
- CPU/GPU/memory/disk measurements.
- No correctness/hash regression in simulation results.

# P4 — Product improvements

## P4.5 — Interactive browser 2D replay

**Dependencies:** Canonical trajectory, timeline, artifact API, and frontend query cleanup.

**Affected areas**

- New compact trajectory API/format
- New frontend replay renderer
- Match detail/timeline integration
- Existing server 2D renderer retained for export

**Intended solution**

1. Serve bounded/chunked trajectory data.
2. Interpolate positions using simulation timestamps.
3. Render through Canvas or WebGL.
4. Use the canonical presentation/event timeline.
5. Add play/pause/speed/seek, player selection, labels, and tactical layers.
6. Keep rendering independent of React component rerenders.
7. Add optional trails, zones, possession, pressing, and event focus.
8. Retain MP4 generation for downloads/sharing.

**Risks**

- Payload size.
- Browser memory and lower-end mobile performance.
- Interpolation must not invent event ordering.

**Tests**

- Playback determinism against source frames.
- Frame budget on desktop/mobile.
- Seek and speed accuracy.
- Chunk loading and cancellation.
- Accessibility for controls and nonvisual event summaries.

---

## P4.6 — Analytics and deterministic inspection

**Dependencies:** Correct canonical events and run-scoped results.

**Affected areas**

- Backend analytics/read models
- Frontend match and season analytics
- New deterministic inspection tools

**Features**

- shot maps and cumulative xG;
- heatmaps;
- passing networks;
- possession chains;
- tactical phase comparisons;
- simulation seed/build comparison;
- action/state divergence inspector;
- artifact provenance and storage manager;
- per-stage performance telemetry;
- season/run comparison.

**Risks**

- Incorrect derived analytics could undermine trust.
- Large query/payload costs.
- Heatmaps and passing networks require corrected source events.

**Tests**

- Analytics totals reconcile with canonical match totals.
- Known synthetic matches produce expected networks/maps.
- Query and payload performance budgets.
- Empty/sparse data handling.
- Cross-run comparisons require compatible schema/engine versions.

# Cross-cutting test strategy

## Required test layers

1. **Pure domain tests**
   - schedule invariants;
   - standings;
   - contracts;
   - event reduction;
   - coordinate transformations.

2. **Database integration tests**
   - real temporary SQLite;
   - transactions;
   - run identity;
   - migrations;
   - backup/restore.

3. **Worker/concurrency tests**
   - synchronized fault injection;
   - deadlines;
   - retry exhaustion;
   - cancellation;
   - restart recovery.

4. **GRF certification tests**
   - actual native and pooled entrypoints;
   - immutable output paths;
   - seed and topology comparisons;
   - explicitly skipped when infrastructure is missing.

5. **Replay tests**
   - archive integrity;
   - frame timing;
   - color;
   - encoder failure;
   - complete media decoding.

6. **API contract tests**
   - OpenAPI-backed schemas;
   - job lifecycle;
   - idempotency;
   - errors and validation;
   - range streaming.

7. **Frontend tests**
   - async jobs;
   - WebSocket reconciliation;
   - stale-response prevention;
   - empty/error states;
   - responsive and accessible UI.

8. **Deployment tests**
   - built frontend behind nginx;
   - REST, WebSocket, recording ranges;
   - persistent database and artifact volumes.

9. **Performance tests**
   - correctness-gated;
   - stable corpus;
   - machine/config metadata;
   - regression thresholds only after reliable baselines exist.

# Recommended implementation order

1. Repair test validity and capture immutable baselines.
2. Fix scheduler and season rollover.
3. Fix worker leases, deadlines, and resource cleanup.
4. Correct side transformations and event attribution.
5. Establish safe migration history.
6. Add run-scoped fixture/match identity.
7. Add safe SQLite save/load.
8. Implement canonical result and artifact schemas.
9. Make video publication atomic and replay teardown bounded.
10. Add durable job orchestration.
11. Separate rendering from simulation.
12. Consolidate the two GRF executors.
13. Standardize APIs and deployment routing.
14. Repair frontend job, caching, polling, and route behavior.
15. Correct broadcast clocks, statistics, event timing, and colors.
16. Build and execute the benchmark suite.
17. Optimize only the measured bottlenecks.
18. Add interactive 2D and analytics features.

This ordering prevents later architectural work from being built on invalid calendars, ambiguous identities, unreliable workers, or unsafe artifacts.
