# Backend Audit Verification Report

Verified: **6 September 2026**

## Assessment

Footy now has a credible canonical GRF execution core, stronger matchday scheduling, safer SQLite snapshots, run-scoped match persistence, bounded replay queues, atomic media publication, and broad deterministic/integration coverage. The configured host completed the full backend suite with **95 passed and 9 skipped**.

The backend is not ready to be described as fully remediated or production-grade. The API still owns background jobs in process memory, the submitted-run and ML-evaluation contracts are inconsistent with the frontend, the worker supervisor can lose ownership in a narrow crash window, the migration chain cannot create a fresh database, replay timelines differ from some rendered videos, and state archives still load pickle automatically.

## Strongest implemented areas

- Circle-method double round-robin schedule with explicit matchdays.
- `GRFMatchExecutor` as the main simulation implementation, with `SimulationWorker` as an adapter.
- Canonical away-team perspective handling and event correspondence tests.
- SQLite online backup/restore with integrity validation and engine disposal.
- Match identity scoped by run, season, and match number.
- Replay encoder stderr draining, queue cancellation, bounded shutdown, and atomic MP4 replacement.
- Versioned `/api/v1` aliases for core resources.

## Highest-risk open areas

| Severity | Area | Verified issue |
| --- | --- | --- |
| High | Migrations | Empty `alembic upgrade head` fails at `c7c6ac0ab9c1` because `Match` does not exist. |
| High | Jobs/API | Simulation trigger returns no `run_id`; job ownership is process-local and cannot resume after restart. |
| High | ML evaluation | The accepted response has no report or job resource, the frontend immediately expects a report, synchronous episodes block the event loop, and model paths are not constrained to the model root. |
| High | Match persistence | On-demand rendering imports the domain `Match` class for an ORM query, so a generated video is published but its URL is not linked to the database row. |
| High | Multiprocessing | Shared queue assigns work before a supervisor-owned lease exists. |
| High | Replay correctness | Timeline defaults do not match all 3D renderer frame inserts. |
| High | Security | State and legacy trajectory readers still invoke pickle automatically. |
| High when exposed | File serving | Recording paths are not validated through resolved root containment. |
| High | Performance evidence | Worker-count benchmark rows are produced by sequential execution; smoke numbers are synthetic. |
| Medium | Media lifecycle | Some writer handles lack failure-safe closure and background rendering advertises a predicted file URL. |

## Validation evidence

```text
Python compile:                  passed
Targeted regression/API tests:  23 passed
Full backend + available GRF:   95 passed, 9 skipped, 210.69 seconds
SQLite live DB:                 integrity ok; 0 FK violations; revision 879f4c01467a
Fresh Alembic DB:               failed at c7c6ac0ab9c1
```

The smoke benchmark completed at roughly 49 synthetic fixtures/second. That value is determined by its artificial sleep and must not be used as GRF throughput evidence.

## Decision

Keep the completed fixes. Address migration bootstrap, durable run submission, worker leasing, timeline parity, and unsafe deserialization before declaring the original P0/P1 remediation complete. Build the real performance harness before changing worker counts, GPU policy evaluation, replay persistence, codecs, or queue sizes.

See [Current Implementation Status](05_current_status.md) for the item-by-item matrix and [Backend Audit Remediation Plan](Backend_audit_PLAN.md) for execution order.
