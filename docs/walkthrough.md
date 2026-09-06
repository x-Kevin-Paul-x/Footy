# Walkthrough: Audit Remediation Verification

Verified: **6 September 2026**

This walkthrough explains what the current implementation actually does after the P0–P4 remediation work. It supersedes the earlier completion narrative, which overstated migration, job, timeline, archive-security, and benchmark readiness.

## 1. Season execution

`League.generate_schedule()` builds explicit rounds using the circle method. A 20-team league produces 38 matchdays, ten fixtures per matchday, and 380 total fixtures. `main.py` consumes `schedule_rounds`, applies between-round operations once per matchday, persists committed results, and performs successful season rollover.

```text
League.generate_schedule
  -> schedule_rounds
  -> prepare matchday fixtures
  -> GRF batch/process pool
  -> persist results under simulation_run_id
  -> training/recovery/finance checkpoint
  -> report and season rollover
```

This path has regression coverage. A long five-to-ten-season resource and economy soak was not rerun during this verification.

## 2. Canonical GRF execution

`backend/src/logic/simulation/match_executor.py` contains `SimulationSpec`, `SimulationTransition`, `CanonicalMatchResult`, and `GRFMatchExecutor`. `SimulationWorker` subclasses the executor, while the WSL simulation worker delegates to it. The executor owns environment initialization, deterministic seed setup, tactical transforms, event/stat tracking, trajectory/state capture, finalization, and cleanup.

Away-team observations are transformed into canonical attacking space before tactical modulation, then directional actions are mirrored back once. Event attribution uses pre-step ownership/action context. The full GRF suite passes in the configured WSL environment.

The process-pool supervisor is still incomplete. It puts fixtures on a shared queue before establishing supervisor-owned leases. A worker that dies after dequeue and before publishing ownership can leave the supervisor unable to identify the lost fixture. Existing crash tests pass but do not target that exact window.

## 3. Persistence and saves

Match identity is constrained by `(simulation_run_id, season_year, match_number)`. Query helpers generally select the latest run when the caller does not provide one. `SimulationRun` stores lifecycle timestamps, progress, cancellation intent, and error detail.

Database save/load uses SQLite’s online backup API, checks integrity, disposes SQLAlchemy connections around restore, and checkpoints WAL state. The live database passed integrity and foreign-key checks at Alembic revision `879f4c01467a`.

The migration story is not complete. Running `alembic upgrade head` on a blank isolated database fails when `c7c6ac0ab9c1` tries to alter `Match`, because the base revision creates only `SeasonReport` and `TransferReport`. Application startup can create tables through SQLAlchemy, but Alembic is not yet a self-contained fresh-install bootstrap.

## 4. Simulation jobs and API

Core resources have `/api/v1` routes with deprecated root aliases. Request schemas validate on-demand match inputs and settings.

Season simulation still runs as a FastAPI in-process background task guarded by an `asyncio.Lock` and a process-global boolean. The trigger responds before `SimulationRun` is created and omits `run_id`. The frontend expects that ID, so its progress flow is not contract-correct. Restart reconciliation can mark stale rows interrupted, but it cannot resume work.

ML evaluation has a separate contract failure. Its endpoint accepts work with HTTP 202 but returns no report, job ID, or polling URL. The frontend service extracts a nonexistent `report`, and the benchmark page immediately reads it. Evaluation episodes are synchronous work executed inside the async background coroutine, so a long run can block other requests. Model inputs should also be stable IDs resolved under the configured model directory rather than caller-controlled filesystem paths.

The on-demand match endpoint can run GRF, reuse an existing recording, or schedule fallback rendering. Fallback currently predicts a video URL before the artifact is published; clients must continue polling and cannot assume that URL exists.

A live showcase generation also verified that the endpoint's video-link update imports the domain `models.match.Match` class where SQLAlchemy expects `database.models.Match`. The match and MP4 complete, but the database link fails with a warning. This must use an explicit ORM import and a run-scoped repository update.

## 5. Trajectory, replay, and video

New trajectory NPZ files store manifest JSON without object arrays and are written through a staging file. Media wrappers stage MP4 output, check that it is nonempty and decodable, then atomically replace the target. Replay encoders continuously drain FFmpeg stderr and have bounded close/abort behavior.

Full-state archives remain trusted-local artifacts. Their chunks use pickle and the reader automatically falls back to legacy pickle when a known header is absent. The trajectory compatibility loader also opens legacy NPZ with `allow_pickle=True`. Do not expose arbitrary uploaded archives to these readers.

The presentation timeline module maps simulation steps, football minutes, and presentation timestamps. The 2D trajectory renderer’s default inserts match its 3-second intro, 4-second halftime, 5-second full-time, and goal replay sequence. The AVI transcode and persistent 3D replay engines use other durations and no equivalent goal replay inserts. Their generated timeline metadata is therefore not frame-accurate yet.

## 6. Frontend

The frontend uses React 19, TypeScript, Material UI, React Query, Zustand, Recharts, and Vite. Formation positions are percentage-based, match changes clear stale replay state, and render polling uses completion-scheduled timers instead of overlapping intervals.

The UI has two integration gaps:

- Dashboard/store simulation polling expects a returned `run_id`, but the backend omits it.
- ML evaluation expects an immediate report even though the backend only acknowledges background work and exposes no job-status resource.
- The settings dialog writes `footy_api_url`; the WebSocket hook reads it, while the Axios client keeps its module-load-time base URL.
- The season-report API helper catches all failures and returns `null`, so server and network errors are presented as missing/empty data.

The replay player consumes `.timeline.json` when present and otherwise estimates event positions. Until renderer timeline parity is fixed, seeking in some 3D videos remains approximate.

## 7. Performance harness

`backend/benchmarks/run_benchmark.py` emits structured machine/config metadata, latency summaries, throughput fields, and hashes. Smoke mode is useful only as a quick harness sanity check: it generates synthetic football values and sleeps. Full mode calls the canonical executor, but `run_suite()` still executes fixtures sequentially; `worker_counts` changes labels rather than concurrency.

The reproduced smoke output was approximately 49 synthetic fixtures/second. This is not a GRF capacity baseline and should not guide process counts, GPU batching, or encoding choices.

## 8. Verification results

```text
Python source/test compilation     PASS
Targeted regression/API suites     23 passed
Full backend suite with WSL        95 passed, 9 skipped (210.69s)
Frontend Jest                      2 suites, 6 tests passed
TypeScript no-emit                 PASS
Vite production build             PASS (2,225 modules)
Existing SQLite integrity          ok; 0 FK violations
Existing Alembic revision          879f4c01467a
Fresh empty Alembic upgrade        FAIL at c7c6ac0ab9c1
Synthetic benchmark smoke          PASS as harness sanity check
```

## 9. Next implementation order

1. Repair the empty and legacy migration paths using isolated database copies.
2. Persist a queued simulation run before returning HTTP 202 and return `run_id`.
3. Move execution ownership to a durable worker lease and close the shared-queue race.
4. Reject automatic legacy pickle loading in normal paths.
5. Enforce resolved path containment for recordings and model selection.
6. Implement a durable, nonblocking ML evaluation job contract.
7. Make each renderer emit its exact presentation frame ledger.
8. Finish writer cleanup and complete-file validation.
9. Replace the synthetic/sequential benchmark with real process-pool workloads.
10. Consolidate API service boundaries and frontend server state.

See [Current Implementation Status](05_current_status.md) for the full matrix and [Backend Audit Remediation Plan](Backend_audit_PLAN.md) for implementation details.
