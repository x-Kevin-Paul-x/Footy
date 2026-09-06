# 05. Current Implementation Status

Last verified: **6 September 2026**

This is the authoritative status page for the audit remediation. It records what was checked against code and what remains incomplete. Passing tests show that covered behavior works in the configured environment; they do not close an item whose production path or acceptance criterion is not exercised.

## Overall assessment

The repository is substantially healthier than the original audit baseline. Scheduling, season rollover, canonical match execution, run-scoped match identity, WAL-safe backups, replay queue shutdown, atomic media publication, API version aliases, responsive formation positioning, and frontend replay polling all have concrete implementations and regression coverage.

The remediation is **not complete**. The highest-priority remaining problems are:

1. A new empty database cannot be built with `alembic upgrade head`.
2. Simulation submission and frontend progress tracking disagree about `run_id`; the job is still process-local.
3. The worker supervisor retains a shared-queue/in-flight publication race after worker death.
4. Presentation timeline metadata does not match every 3D renderer’s actual frame inserts.
5. The performance harness does not exercise worker concurrency, and smoke mode does not run GRF.
6. Full-state archives still deserialize pickle automatically and must be treated as trusted local files.
7. ML evaluation returns no report or job resource even though the frontend immediately expects a report, and its synchronous evaluation loop runs on the API event loop.

## Reproduced validation

| Check | Result | Scope |
| --- | --- | --- |
| Python compile | Passed | `backend/src`, `backend/tests` |
| Targeted P0–P4/API suites | 23 passed | Regression, certification, API contracts |
| Full backend suite with WSL access | **95 passed, 9 skipped** in 210.69s | Includes real GRF integration available on this host |
| Frontend Jest | **2 suites, 6 tests passed** | Existing component tests |
| TypeScript | Passed | `tsc --noEmit` |
| Frontend production build | Passed; 2,225 modules | Vite 6.3.5 |
| Live SQLite database | `integrity_check=ok`, 0 FK violations, revision `879f4c01467a` | Existing `backend/data/football_sim.db` |
| Fresh Alembic bootstrap | **Failed** | `c7c6ac0ab9c1` tries to alter missing `Match` table |
| Smoke benchmark | Ran successfully | Synthetic sequential sanity check only |

The first sandboxed full-suite attempt produced three WSL access errors. Re-running with host WSL access passed the full suite, so those were environment restrictions rather than engine failures.

## Remediation matrix

| Plan item | Status | Evidence / remaining work |
| --- | --- | --- |
| P0.1 valid matchdays | Verified | Circle-method `schedule_rounds`; regression covers 38 rounds and 380 fixtures for 20 teams. |
| P0.2 multi-season control flow | Verified by tests | Normal completion performs report/rollover; shortened-season paths have coverage. A long multi-season soak is still recommended. |
| P0.3 worker leases and terminal results | **Partial** | Watchdog/retry tests pass, but `simulation_process_pool.py` still uses one shared task queue and worker-owned in-flight publication. A worker can die after dequeue and before the supervisor learns fixture ownership. |
| P0.4 GRF cleanup | Mostly verified | Executor and replay paths close environments/archives in normal and tested failures. Some imageio writers rely on reaching an explicit `close()` and should be placed in `finally`. |
| P0.5 canonical side handling | Verified by tests | Away observations/actions are mirrored into canonical attacking space. |
| P0.6 event/stat attribution | Verified by tests | Pre-step touch/action attribution and event correspondence tests pass. External statistical calibration is separate. |
| P0.7 safe media publication | Partial | Staging plus atomic replacement is implemented. Validation checks nonempty/decodable output, but does not decode every frame or compare duration to timeline. |
| P0.8 replay queue/encoder lifecycle | Verified by tests | Bounded queue, stderr drain, cancellation, timeout, and abort behavior implemented. |
| P0.9 run-scoped persistence | Mostly verified | Match uniqueness is `(run, season, match_number)` and latest-run queries exist. Some API match lookups remain ambiguous across runs. |
| P0.10 WAL-safe save/load | Verified | Uses SQLite backup API, integrity checks, engine disposal, and WAL checkpointing. |
| P0.11 safe migration baseline | **Open** | Existing DB is healthy at head; empty-database upgrade fails. Historical migration retains unreachable destructive generated code after an early `return`. |
| P1.1 durable jobs | **Open** | `SimulationRun` has lifecycle fields, but FastAPI uses process-global booleans/`asyncio.Lock` and in-process background tasks. No durable lease, resume, or multi-worker coordination. |
| P1.2 canonical executor | Verified | `SimulationWorker` subclasses `GRFMatchExecutor`; WSL simulation adapter delegates to it. |
| P1.3 canonical artifact package | Partial | Typed spec/result and versioned trajectory/state files exist. Artifact identity and lifecycle are still spread across filenames, DB fields, and compatibility lookup rules. |
| P1.4 separate simulation/rendering | Partial | On-demand render endpoint exists and trajectories can be rendered without policy re-evaluation. Other requests still support synchronous live 3D capture. |
| P1.5 daemon idempotency | Partial | Request-size limit and bounded response cache exist. It is still a synchronous custom daemon without durable ownership. |
| P2.1 repository/service boundaries | Open | `api_fastapi.py` remains a large module mixing HTTP, persistence, orchestration, filesystem access, and report construction. |
| P2.2 versioned API | Mostly verified | Core `/api/v1` routes and deprecated aliases exist. Schemas are incomplete on several endpoints and errors are not fully uniform. |
| P2.3 configuration ownership | Partial | Core paths/settings are centralized, but runtime settings also mutate environment variables and frontend API configuration is split. |
| P2.4 retention policy | Verified | Historical runs are retained by default; explicit count retention and stale-temp cleanup are implemented. |
| P3.1 canonical presentation timeline | **Partial / incorrect for 3D** | Builder and API exist. Its default 4s half-time, 5s full-time, and goal-replay inserts match the 2D trajectory renderer, not the AVI transcode or persistent 3D paths. |
| P3.2 halftime statistics | Partial | 2D trajectory and persistent replay compute first-half counters. AVI transcode filters events but still displays final possession/shots/xG at halftime. |
| P3.3 2D timing/color | Mostly verified | Exact event-step mapping and RGB conversion are implemented. Renderer resource cleanup needs hardening. |
| P3.4 safe deserialization | **Open** | New NPZ metadata is JSON, but the compatibility loader calls `np.load(..., allow_pickle=True)` and `GRFStateArchiveReader` automatically calls `pickle.load/loads`. |
| P3.5 simulation/ML job UX | **Open** | Season simulation omits the `run_id` expected by the frontend. ML evaluation returns neither a report nor a job ID/status resource, while the frontend immediately dereferences `report` from the accepted response. |
| P3.6 frontend server state | Partial | React Query is used broadly, but Zustand duplicates season/simulation state. |
| P3.7 replay polling/stale media | Verified | Completion-scheduled timers and state reset on match changes are implemented. |
| P3.8 responsive formation/accessibility | Responsive fix verified | Formation coordinates use percentages. Accessibility coverage remains small. |
| P3.9 remove inert settings | Partial | Simulation settings persist, but the local API URL does not reconfigure the Axios client. |
| P4.1 benchmark/correctness gate | **Open** | Hash and percentile reporting exist. Worker count is a label only; all fixtures execute sequentially. Smoke mode sleeps and generates synthetic results. |
| P4.2 bounded execution | Partial | Process count is bounded, but the shared queue is unbounded and P0.3 ownership remains unresolved. |
| P4.3 persistent environments | Needs benchmark | Daemon/replay persistence exists; no valid comparative throughput or memory result yet. |
| P4.4 profile-driven render optimization | Open | Encoder choices exist, but there is no representative before/after profile gate. |
| P4.5 browser-native 2D replay | Open | Current match experience is MP4-oriented; no trajectory streaming/canvas replay implementation was verified. |
| P4.6 analytics/inspector features | Open | Heatmaps, passing networks, xG flow, artifact inspection, and run comparison remain roadmap work. |

## Verified defects requiring follow-up

### V-01 — Fresh migration chain is not a bootstrap

- **Severity:** High
- **Files:** `backend/alembic/versions/f1279028ebae_add_season_and_transfer_reports.py`, `c7c6ac0ab9c1_sync_schema_to_models.py`, later migrations
- **Evidence:** On an empty isolated directory, upgrade creates only report tables, then `c7c6ac0ab9c1` executes `ALTER TABLE "Match" ...` and fails with `no such table: Match`.
- **Fix:** Establish a real baseline containing the complete legacy schema or make the synchronization revision create missing tables safely. Test empty upgrade, populated legacy upgrade, and downgrade policy using temporary copies.

### V-02 — Simulation API contract breaks progress UX

- **Severity:** High
- **Files:** `backend/src/api_fastapi.py`, `frontend/src/services/api.ts`, `frontend/src/store/simulationStore.ts`, `frontend/src/pages/Dashboard.tsx`
- **Evidence:** The trigger queues `run_simulation_task()` and returns `SimulationStatusResponse` without `run_id`. The background task creates the run later. Both frontend consumers compare/poll using `result.run_id`.
- **Fix:** Create and persist the run before returning HTTP 202, return its ID, and pass that ID into the worker. Add status and cancellation resources scoped to the returned ID.

### V-03 — Worker ownership can still be lost

- **Severity:** High
- **Files:** `backend/src/logic/simulation/simulation_process_pool.py`
- **Evidence:** Fixtures are placed on a shared queue before a supervisor-owned lease is recorded; the worker publishes ownership through a manager dictionary after dequeue. Death between those operations leaves no fixture associated with the dead process.
- **Fix:** Have the supervisor assign one leased fixture to a worker-specific queue before dispatch, or use a durable queue whose acknowledgement/visibility timeout provides the lease.

### V-04 — Timeline metadata diverges from rendered video

- **Severity:** High
- **Files:** `backend/src/logic/presentation_timeline.py`, `backend/src/logic/grf_renderer.py`, `backend/src/logic/replay/replay_pipeline.py`, `persistent_replay_engine.py`
- **Evidence:** Timeline defaults are 60 half-time frames, 75 full-time frames, and 70 extra frames per goal at 15 fps. AVI transcode and persistent 3D replay use different insert durations and no equivalent goal replay sequence.
- **Fix:** Make renderers emit the exact frame ledger they wrote, or pass a renderer profile into one timeline builder and test total frame count plus event PTS against decoded video.

### V-05 — Benchmark does not measure worker scaling

- **Severity:** High
- **Files:** `backend/benchmarks/benchmark_harness.py`, `run_benchmark.py`
- **Evidence:** `worker_counts` only controls report rows. `run_suite()` calls `run_single_simulation()` in a nested sequential loop. Smoke mode creates synthetic values and sleeps up to 20ms.
- **Fix:** Benchmark the real process-pool entry point, separate startup/warm/steady-state phases, run sufficient repetitions, record failures and resource peaks, and compare identical fixture corpora.

### V-06 — Automatic pickle loading remains

- **Severity:** High when artifacts are untrusted; Medium for local-only use
- **Files:** `backend/src/logic/grf_state_archive.py`, `backend/src/logic/grf_trajectory.py`
- **Evidence:** Unknown state-archive magic falls back to `pickle.load`; compressed chunks use `pickle.loads`; trajectory compatibility opens NPZ with `allow_pickle=True`.
- **Fix:** Require explicit trusted legacy-import mode. Use a non-executable serialization for new state chunks and reject unknown magic in normal API/render paths.

### V-07 — Recording path validation is incomplete

- **Severity:** High if the API is exposed beyond localhost
- **Files:** `backend/src/api_fastapi.py::stream_recording`
- **Evidence:** It checks for the substring `..`, but does not resolve and prove containment under `RECORDINGS_DIR`; it also falls back to a top-level basename.
- **Fix:** Resolve `(RECORDINGS_DIR / relative_path)`, require `relative_to(RECORDINGS_DIR.resolve())`, remove basename fallback, and test absolute paths, drive-qualified paths, encoded traversal, and valid Range requests.

### V-08 — Background render advertises an unfinished file

- **Severity:** Medium
- **Files:** `backend/src/api_fastapi.py::simulate_grf_match`
- **Evidence:** When fallback rendering is scheduled, the response immediately sets a predicted MP4 URL even though rendering may fail or choose a mode-specific filename.
- **Fix:** Return a render job/status URL with `video_url=null` until atomic publication succeeds.

### V-09 — API URL setting is disconnected

- **Severity:** Medium
- **Files:** `frontend/src/components/HeaderSettingsModal.tsx`, `frontend/src/services/api.ts`, `frontend/src/hooks/useSimulationSocket.ts`
- **Evidence:** The modal writes `footy_api_url`; WebSocket reads it, Axios does not. The API module uses `process.env` through a Vite compatibility define.
- **Fix:** Resolve the base URL in one helper and update Axios through a request interceptor or explicit client recreation.

### V-10 — Renderer handles need failure-safe closure

- **Severity:** Medium
- **Files:** `backend/src/logic/grf_renderer.py`
- **Evidence:** Imageio writers are closed at the end of the happy path. Exceptions before that point can leave handles/processes open until garbage collection.
- **Fix:** Wrap capture/writer ownership in `try/finally`, abort failed encodes, and remove staging files after handles close.

### V-11 — ML evaluation API and frontend contracts are incompatible

- **Severity:** High
- **Files:** `backend/src/api_fastapi.py::trigger_ml_evaluation`, `backend/src/api_fastapi.py::run_ml_eval_task`, `frontend/src/services/api.ts::runMlEvaluation`, `frontend/src/pages/MlBenchmarks.tsx`
- **Evidence:** The backend accepts the request with HTTP 202 and returns only status/message fields. It does not return a report, job ID, or polling URL. The API client returns `response.data.report`, and the page immediately reads fields such as `report.runtime`. The background coroutine also executes synchronous model episodes directly on the event-loop thread. Request-provided model paths flow into model loading without containment under the configured model directory.
- **Fix:** Persist and return a typed evaluation job resource, run CPU-bound evaluation in a worker/executor, expose status/result/cancel endpoints, and accept model IDs resolved under `ML_MODELS_DIR` rather than arbitrary paths. Update the frontend to poll the job and render explicit queued/running/failed states.

### V-12 — Season report transport failures are presented as missing data

- **Severity:** Medium
- **Files:** `frontend/src/services/api.ts::getSeasonReportData`, `frontend/src/pages/LeagueOverview.tsx`, `frontend/src/pages/YouthAcademy.tsx`, `frontend/src/pages/TransferMarket.tsx`
- **Evidence:** `getSeasonReportData` catches every Axios/network/server error and returns `null`. Callers' error branches therefore do not run for backend outages, timeouts, or 500 responses and may render empty data instead.
- **Fix:** Return `null` only for an intentional 404/no-report response and rethrow all other failures. Add explicit error UI where a consumer currently assumes nullable data means an empty result.

### V-13 — On-demand video persistence imports the wrong `Match` class

- **Severity:** High
- **Files:** `backend/src/api_fastapi.py::simulate_grf_match`
- **Evidence:** A live Arsenal–Chelsea 3D generation published its MP4 successfully, then logged `Column expression, FROM clause, or other columns clause element expected, got <class 'models.match.Match'>`. The handler imports the domain `models.match.Match`, shadowing the ORM `database.models.Match` used in the database query.
- **Fix:** Give domain and ORM classes unambiguous import names, query the ORM class, and move artifact linking into the match repository/service. Add an API integration test that generates a video and verifies the intended database row receives its run-scoped URL.

### V-14 — Match-list and match-detail routes used the same path shape

- **Severity:** High — fixed during visual verification
- **Files:** `backend/src/api_fastapi.py::get_matches_by_season`, `frontend/src/services/api.ts::getMatchesBySeason`
- **Evidence:** Both resources were registered as `/api/v1/matches/{value}`. Because the single-match route was registered first, `/api/v1/matches/2026` returned match ID 2026 rather than the season collection, and Match Reports failed while spreading `undefined`.
- **Fix applied:** The canonical collection is now `/api/v1/seasons/{season_year}/matches`; single-match detail remains `/api/v1/match/{match_id}` and the old root `/matches/{season_year}` compatibility alias remains available.
- **Validation:** Exercise both canonical URLs with the same numeric value and assert one returns `{matches: [...]}` while the other returns one match resource.

## Release gates

Before calling the remediation complete:

1. Pass a clean empty-database migration and a copied legacy-database migration.
2. Add an API integration test that submits a run, receives `run_id`, observes progress, cancels it, and verifies restart reconciliation.
3. Add a deterministic worker-death test for the dequeue-before-ownership window.
4. Decode a 2D and 3D video and prove timeline total frames/event PTS match.
5. Replace the synthetic worker-scaling table with real pool measurements.
6. Disable implicit legacy pickle loading in network-reachable paths.
7. Add path-containment tests for recordings and saved artifacts.
8. Add an ML evaluation contract test covering accepted job, nonblocking API responsiveness, result polling, failure, cancellation, and model-path rejection.
9. Verify season-report consumers distinguish 404 empty state from transport and server failures.
10. Generate an on-demand recording and verify its URL is persisted against the correct ORM match row.
