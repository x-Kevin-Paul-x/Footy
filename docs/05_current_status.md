# 05. Current implementation status

Reviewed and tested: **13 October 2026**. See [dated verification](verification_2026_10_13.md) and [raw evidence](evidence/). Earlier audits and the renamed September plan are historical context.

| Area | Status | Evidence / remaining work |
| --- | --- | --- |
| Fresh and legacy schema upgrades | Implemented, tested | Frozen additive baseline, guarded historical revisions, campaign/job revisions, SQLite batch upgrades, pre-migration backup and integrity checks. |
| Accepted simulation jobs | Implemented, tested | Persisted run/job IDs before HTTP 202; idempotency; unique active ownership; leases, cancellation and expiry reconciliation. Interrupted jobs preserve results and do not automatically resume. |
| Fixture ownership | Implemented, tested | Supervisor assignment precedes per-worker dequeue; retries are bounded; stale tokens rejected; output order preserved. |
| Evaluation jobs and UI | Implemented, tested | Registered model IDs, bounded separate process, persisted results, status polling and refresh recovery. |
| Saves | Implemented, tested | WAL-safe SQLite snapshots, pinned recording manifests, guarded restoration and invalidated prior worker ownership. Snapshot restoration is not live campaign reconstruction. |
| Historical campaign state | Implemented for new runs | Run-scoped reports/transfers, frozen squads/finances and persisted cash entries; Saved campaigns exposes history. Older runs cannot retroactively acquire missing snapshots. |
| Replay input/publication | Implemented, tested | Safe V3 byte chunks, restricted legacy conversion, object-free NPZ, contained paths, run-scoped video linking, emitted-frame timelines and complete decode validation. |
| Manager AI evidence | Measured | Three training seeds and thirty held-out evaluation seeds. DQN advantage was not established; synthetic environment and tabular decision fallback are documented. |
| Native worker evidence | Measured | Nine distinct direct-Linux tests: six-seed topology checks, operating modes, event/stat correspondence, broadcast publication, worker assignment and proven worker SIGKILL recovery. |
| Economy and availability | Implemented, tested | Cashflow reconciliation; attendance cash; merit broadcasting; loan squad/wage/expiry rules; release and sell-on clauses; persisted injury/bans/contracts; positional replenishment and capped academies. |
| Statistical realism | Open research | A sourced calibration report measures the retained native season's scoring discrepancy. No score postprocessing is used. |
| In-match changes / home advantage | Experimental opt-in | Deterministic conditional changes and venue-dependent policy modulation under FOOTY_DYNAMIC_TACTICS=1; keep official TiKick default until calibrated. |
| Native substitutions | Unsupported | Existing legacy substitutions and stored benches do not establish native hot-swap support. |
| Installation and CI | Implemented, tested locally and on GitHub | Editable package, cross-platform launcher, full portable tests/coverage, lint, scoped typing, hooks and explicit native workflow. [Clean Linux CI and demo deployment passed](https://github.com/x-Kevin-Paul-x/Footy/actions/runs/38470099412). |
| Documentation and distribution | Demo deployed; release drafted | Updated claims, platform setup, model provenance, contribution/issue templates, changelog and third-party notices. [Read-only demo](https://x-kevin-paul-x.github.io/Footy/) is live; v0.1.0 is an unpublished draft with generated checkpoints and checksums. |

The implementation preserves the current default artifact retention setting. Creating a new save pins the run directories referenced by that snapshot; deleting the save releases those retention references. Keep curated match assets separate from disposable runtime recordings.

The six-seed native topology rerun compares strict trajectory archives after policy provenance was made identical across direct and pooled execution. Performance claims describe their measured workload and include cold-start overhead rather than implying a universal real-time multiplier.
