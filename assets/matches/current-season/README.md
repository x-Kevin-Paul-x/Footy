# Fresh-season README showcase — 14 October 2026

Footy generated a new isolated season and simulated four fixtures through the
production GRF/TiKick season pipeline. This is a partial season sample, not a
380-fixture verification run. Players are generated squad members, with their
actual persistent IDs, shirt numbers and cosmetics recorded in each manifest.

A uniform random choice from the four finished fixtures selected **West Ham
4–4 Bournemouth**. The selection seed (`3596853041`), candidate order, match
results and full selected manifest are retained in `showcase.json`.

The season ran with `FOOTY_ENGINE_MODE=GRF`, `FOOTY_NUM_SEASONS=1`,
`FOOTY_MAX_MATCHES=4`, `FOOTY_GRF_MAX_STEPS=3200`,
`FOOTY_PARALLEL_WORKERS=2`, `FOOTY_SYNC_VIDEO_RENDER=0`, and isolated
`FOOTY_DATA_DIR` / `FOOTY_REPORTS_DIR` directories. Existing saves were untouched.
Fixture simulation took 69.85 seconds; setup and management processing brought
the isolated run to 89.636 seconds.

All four native archives were checked by `backend/verification/audit_native_replays.py`:
12,004 states and 30 native goal frames passed, with native full time reached in
every match. Audit details are retained in `showcase.json`.

## Retained files

- `west-ham-bournemouth.mp4`: complete native 720p, 10 fps replay with midnight
  studio cards, club kits, recorded identity, clay HUD/radar and director camera.
- `west-ham-bournemouth.timeline.json`: emitted-frame and event timestamps.
- `west-ham-bournemouth.benchmark.json`: render throughput and unchanged source hashes.
- `showcase.json`: selection, squad identity, canonical events, audits and media evidence.
- `start.png`, `half-time.png`, `full-time.png`, `gameplay.png`, `goal.png`:
  frames extracted from this replay, with recorded statistics rather than preview values.
- `../../readme/native-goal.gif`: an eight-second, 720×405, 10 fps infinite loop
  beginning at video time 72.1 seconds, around Ernest Byrd's opening goal at
  74.1 seconds. GIF playback preserves the original recorded speed.

## Rendering

The native visual extension was built as described in `backend/native/README.md`.
The complete match was rendered from its original `.grfstate` / `.npz` pair using:

```sh
python backend/benchmarks/benchmark_replay_presentation.py \
  <recording-directory>/trace_match_2026_18_3.grfstate \
  assets/matches/current-season/west-ham-bournemouth.mp4 \
  --resolution 720p --theme dark --camera director
```

The large native archives and generated per-player kit textures remain local
verification artifacts. This curated directory is retained independently of
runtime recording cleanup. Earlier season recordings remain historical evidence;
the README now showcases this fresh recording.
