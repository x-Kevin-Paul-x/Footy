# Backend Audit Remediation Plan

Last reviewed: **6 September 2026**

This page is the execution checklist for the remaining backend work. Completed and partial items are recorded in [05_current_status.md](05_current_status.md); the original detailed rationale remains in [Footy Project Improvement Plan.md](Footy%20Project%20Improvement%20Plan.md).

## P0 — release blockers

### 1. Repair Alembic bootstrap

- **Affected:** `backend/alembic/versions/f1279028ebae_add_season_and_transfer_reports.py`, `c7c6ac0ab9c1_sync_schema_to_models.py`, later revisions, migration tests.
- **Problem:** `alembic upgrade head` fails on an empty database because `c7c6ac0ab9c1` alters tables the base revision never creates.
- **Implementation:** Create a complete, tested baseline strategy. Preserve upgrade support for existing databases. Remove unreachable destructive generated operations from `f1279028ebae` after compatibility is proven.
- **Tests:** Empty database to head; representative legacy snapshot to head; `PRAGMA integrity_check`; `PRAGMA foreign_key_check`; duplicate-report and duplicate-match preflight failures.
- **Risk:** High. A migration mistake can lose save data. Use isolated copies and SQLite batch operations only.

### 2. Make simulation submission durable and contract-correct

- **Affected:** `backend/src/api_fastapi.py`, `database/db_setup.py`, `database/models.py`, frontend simulation callers.
- **Problem:** The API accepts work before creating a run and omits the `run_id` expected by the frontend. Ownership is a process-global boolean and lock.
- **Implementation:** Persist a queued run first, return HTTP 202 plus `run_id`, lease it to a worker, heartbeat it, and expose run-scoped status/cancel endpoints. Make retries and restart reconciliation idempotent.
- **Tests:** Concurrent submissions; returned ID exists immediately; progress is monotonic; cancel; worker crash; API restart; duplicate request key; two API workers.
- **Risk:** Medium-high because it changes lifecycle semantics.

### 3. Close the worker dequeue/ownership race

- **Affected:** `backend/src/logic/simulation/simulation_process_pool.py` and resilience tests.
- **Problem:** A shared queue lets a worker die after dequeue and before publishing in-flight ownership.
- **Implementation:** Record a supervisor-owned lease before dispatch to a worker-specific queue, or adopt durable visibility-timeout semantics. A fixture must end in one success result or one terminal error.
- **Tests:** Kill at pre-dequeue, post-dequeue/pre-start, mid-step, post-finalize/pre-result, and repeated retry exhaustion. Assert bounded termination and no duplicate artifact publication.
- **Risk:** Medium; multiprocessing timing tests must be deterministic.

### 4. Remove implicit unsafe deserialization

- **Affected:** `backend/src/logic/grf_state_archive.py`, `grf_trajectory.py`, import tools and API/render entry points.
- **Problem:** Unknown state files and legacy NPZ metadata can execute pickle loading automatically.
- **Implementation:** Reject unknown magic in normal readers; require an explicit trusted-local legacy import command; store new chunks in a non-executable length-prefixed format.
- **Tests:** Malicious pickle fixture is rejected without execution; V1/V2 trusted conversion; corrupt header/chunk/hash; oversized metadata.
- **Risk:** Medium due to legacy replay compatibility.

### 5. Enforce recording path containment

- **Affected:** `backend/src/api_fastapi.py::stream_recording` and API tests.
- **Problem:** The route uses substring traversal checks and basename fallback rather than resolved containment.
- **Implementation:** Resolve under `RECORDINGS_DIR`, require `relative_to(root)`, reject absolute/drive-qualified/encoded traversal, and remove fallback guessing.
- **Tests:** Valid nested recording and byte range; `..`; encoded separators; absolute POSIX path; Windows drive and UNC path; symlink/junction escape where supported.
- **Risk:** Low; legacy malformed URLs may stop working.

### 6. Repair the ML evaluation job contract

- **Affected:** `backend/src/api_fastapi.py`, ML evaluation services/model loading, `frontend/src/services/api.ts`, `frontend/src/pages/MlBenchmarks.tsx`, API tests.
- **Problem:** The backend returns HTTP 202 without the report the frontend immediately expects and provides no evaluation job identifier or status endpoint. Synchronous episodes execute in an async background coroutine and can block the API event loop. Caller-provided model paths are not constrained to the configured model directory.
- **Implementation:** Persist an evaluation job before acceptance; return its ID and status URL; execute evaluation in a bounded process or thread executor; add status, result, and cancellation endpoints; accept stable model IDs and resolve them with strict containment under `ML_MODELS_DIR`; update the page to poll and display queued/running/failed/completed states.
- **Tests:** Response-schema contract; heartbeat endpoint remains responsive during evaluation; successful and failed polling; cancellation; restart reconciliation; concurrent job limit; absolute/traversal/UNC model-path rejection; frontend queued-to-result flow.
- **Risk:** Medium because it changes an existing asynchronous endpoint contract and model selection flow.

### 7. Fix on-demand artifact persistence type ownership

- **Affected:** `backend/src/api_fastapi.py::simulate_grf_match`, `database/match_db.py`, API integration tests.
- **Problem:** The handler imports the domain `models.match.Match` and passes it to `db.query()` where the SQLAlchemy `database.models.Match` class is required. Live video generation succeeds, but linking the resulting URL to the match row fails and is reduced to a warning.
- **Implementation:** Alias domain and ORM imports explicitly, move the update into a run-scoped repository method, and make persistence failure visible in the response/job result rather than reporting an entirely successful operation.
- **Tests:** Generate or stub a successful recording; assert the intended `(run_id, season, match_number)` row receives the URL; assert a duplicate match number in another run is unchanged; assert persistence failure is returned or recorded.
- **Risk:** Low to medium; the query must preserve compatibility for existing identifiers while preventing cross-run updates.

## P1 — correctness and reliability

### 8. Make the presentation timeline renderer-owned

- **Affected:** `presentation_timeline.py`, `grf_renderer.py`, both replay engines, timeline API and frontend seeking.
- **Problem:** One default timeline is written for renderers with different intro, halftime, full-time, and goal-replay frame sequences.
- **Implementation:** Record segments while frames are emitted, or pass an explicit renderer profile. Publish timeline beside the MP4 only after decoded frame count matches.
- **Tests:** Goal before/after halftime; no-goal match; multiple goals on a step; each render mode; decoded frame count and event PTS.
- **Risk:** Medium; existing timeline files need a version bump/fallback.

### 9. Finish media lifecycle hardening

- **Affected:** `grf_renderer.py`, replay encoders, native runner.
- **Problem:** Some writers are not closed in `finally`; completion validation checks only nonempty/decode-open output; background simulation can advertise a video before publication.
- **Implementation:** Give each capture/writer one failure-safe owner, validate complete decode and expected duration, keep `video_url` null until atomic replace, and retain authoritative sources until success.
- **Tests:** Early EOF, encoder exit, callback exception, disk-full simulation, cancellation, previous-good-output preservation, stale partial cleanup.
- **Risk:** Medium; complete decode adds finalization latency.

### 10. Make run-scoped match identity explicit in APIs

- **Affected:** `database/match_db.py`, match/video/timeline routes, schemas, frontend links.
- **Problem:** Some numeric and filename fallback lookups can select an arbitrary run when match numbers repeat.
- **Implementation:** Use a stable match resource ID or require `run_id` where ambiguity exists. Return run identity in match summaries and artifact URLs.
- **Tests:** Same season/match number in two runs; latest-run default; explicit old-run lookup; artifact isolation.
- **Risk:** Medium; compatibility routes need deprecation handling.

## P2 — architecture and performance evidence

### 11. Replace the synthetic scaling benchmark

- **Affected:** `backend/benchmarks/benchmark_harness.py`, CLI, CI jobs.
- **Problem:** `worker_counts` is not used to execute work; smoke mode is synthetic and sequential.
- **Implementation:** Invoke the real pool with a fixed fixture corpus. Separate cold startup, warm steady-state, trajectory, full-state, 2D render, 3D render, and encode workloads. Record throughput, p50/p95, failures, RSS, disk, CPU, GPU, and hashes.
- **Tests:** Harness self-test proves requested concurrency is observed and intentional nondeterminism fails the gate.
- **Risk:** Low to product behavior; medium CI/runtime cost.

### 12. Split the API module at service boundaries

- **Affected:** `api_fastapi.py`, new simulation/render/report/artifact services, repositories and routers.
- **Problem:** HTTP handlers own filesystem traversal, SQL queries, background work, and report construction.
- **Implementation:** Extract services incrementally while preserving response contracts. Centralize typed errors, timeouts, configuration, and ownership rules.
- **Tests:** Existing API contract suite plus service-level failure tests.
- **Risk:** Medium; do after P0/P1 contracts stabilize.

## P3 — integration and product completion

1. Use one frontend API-base resolver for Axios and WebSocket; apply settings without stale module state.
2. Consolidate simulation/season server state under React Query or a clearly bounded store.
3. Add accessible replay controls and renderer-accurate event seeking.
4. Stream canonical trajectory data into a browser-native 2D replay.
5. Add heatmaps, passing networks, xG flow, run comparison, and artifact inspection after the event schema and benchmark gates are stable.

## Required order

1. Migration bootstrap and backups.
2. Simulation submission contract and durable ownership.
3. Worker lease race.
4. Unsafe deserialization, path containment, and the ML evaluation contract.
5. Timeline/media lifecycle.
6. Run-scoped resource APIs.
7. Real benchmark harness.
8. Service extraction.
9. Frontend state and product features.
