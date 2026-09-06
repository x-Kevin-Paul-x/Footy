# 02. Backend Logic and Simulation

Last verified: **6 September 2026**

## Canonical match execution

`GRFMatchExecutor` accepts a `SimulationSpec` and returns `CanonicalMatchResult`. `SimulationWorker` is a thin subclass used by the process pool. The WSL simulation worker converts JSON payloads into the same executor rather than maintaining a second physics/event implementation.

```text
fixture/domain context
  -> SimulationSpec
  -> GRFMatchExecutor initialization
  -> GRF environment reset
  -> TiKick or fallback policy actions
  -> pre-step attribution + environment step
  -> score/event/stat updates
  -> trajectory/state capture
  -> CanonicalMatchResult
  -> close environment and artifact writers
```

The executor seeds Python, NumPy, and PyTorch from the match seed. It converts away-team observations and formation anchors into canonical attacking space and mirrors directional actions back to physical GRF space once.

## Event and statistic handling

- Ball ownership and last-touch state are captured before stepping so goals and shots can be attributed to the acting player.
- Possession is based on owned frames.
- Shot xG is computed from observed geometry and context.
- Pass attempts/completions use ownership transitions.
- Events carry simulation steps where the executor can determine them.

These calculations are implementation-defined football metrics. They have deterministic and semantic tests, but they have not been calibrated to an external Opta dataset.

## Batch and worker lifecycle

`GRFBatchRunner` builds fixture payloads and calls `SimulationProcessPool`. The pool bounds process count, loads policy inside workers, reports results through a queue, retries failures, and terminates stuck workers after a watchdog threshold.

The current shared task queue is still vulnerable to a narrow lost-ownership window: a worker can dequeue a fixture and die before writing the fixture ID into shared in-flight state. The supervisor-owned lease design in the remediation plan remains required.

## Replay modes

| Mode | Output | Intended use |
| --- | --- | --- |
| `none` | Result/statistics only | Fast season simulation when no replay is needed. |
| `trajectory` | `.npz` coordinates/actions/scores/ownership plus manifest | 2D rendering and analysis. |
| `full_state` | Trajectory plus `.grfstate` state archive | 3D state restoration. |

New NPZ manifests are JSON strings. The loader still enables pickle for legacy compatibility. `.grfstate` chunks are compressed pickles, and unknown headers fall back to legacy `pickle.load`; only trusted local artifacts may be opened.

## Rendering and encoding

There are three related pipelines:

1. `render_video_from_trajectory()` draws a 2D tactical broadcast from recorded arrays.
2. `transcode_live_avi_to_broadcast_mp4()` overlays a live GRF AVI and writes H.264 MP4.
3. The persistent replay engines restore `.grfstate` frames, draw HUD content, and stream RGB frames to FFmpeg.

Trajectory/AVI imageio paths use libx264 CRF 28. The direct software encoder uses libx264 CRF 22; NVENC uses CQ 24. MP4 wrappers write staging files and atomically replace published output after basic decode validation.

The presentation timeline currently matches the 2D trajectory defaults: 45 intro frames, 60 halftime frames, 75 full-time frames, and goal replay inserts at 15 fps. The 3D paths use different insert counts and must not claim exact PTS parity until they emit their actual frame ledger.

## Season execution

`main.py` runs structured rounds, applies between-round training/recovery/finance work, commits match results, checkpoints run progress, writes reports, and advances years. `FOOTY_MAX_MATCHES` supports shortened validation runs; `FOOTY_NUM_SEASONS` controls CLI season count.

## Error behavior

- Executor/environment setup and normal shutdown are covered by tests.
- Replay queues have bounded waits and cancellation signals.
- FFmpeg stderr is drained continuously and finalization has a timeout.
- Failed background rendering records an error progress file, but the on-demand match endpoint can still return a predicted URL before publication.
- API season jobs cannot resume after process restart.

## Performance status

No production GRF throughput baseline is established. The current smoke benchmark is synthetic. Full benchmark mode invokes matches sequentially and does not use its worker-count field to drive the process pool. See [Current Status](05_current_status.md) and [Backend Audit Remediation Plan](Backend_audit_PLAN.md).
