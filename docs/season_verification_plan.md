# Full-season verification plan

Run a fresh, isolated 20-team, 380-fixture season through the production league,
GRF executor, persistence, and replay paths. Do not reset the user's database.

Acceptance checks:

1. Every ordered home/away pairing occurs once; every club plays 38 matches.
   Recompute points, wins, draws, losses and goals from persisted results.
2. A completed match must reach the native engine's terminal state. A step
   budget cutoff is an incomplete simulation, never a fabricated 90-minute game.
   Use the installed scenario's 3,000-step duration and native second-half restart.
3. Record halftime only when the engine actually enters its halftime kickoff;
   verify the second half resumes. Goal events must match actual score changes
   at the exact recorded frames. Audit observed set pieces and disciplinary changes.
4. Match ID, team identity, score and event ledger must agree across the result,
   database record, trajectory manifest, and state archive. Matchday results must
   be associated by ID, even if workers return them in a different order.
5. Restore recorded states and compare player positions, ball, score and game
   mode against recorded trajectory frames. Replay generation must not simulate
   a second match. Render representative complete matches and validate video.
6. Run automated regressions. Retain a machine-readable season audit, progress,
   final standings and playable replay evidence. Report failures and unsupported
   rules explicitly; a test skipped for missing GRF is not evidence of success.

First findings: the default 1,200-step cutoff was presented as full time despite
the installed scenario using 3,000 steps and second half at 1,500. Halftime was
synthetic. Batch results were assigned to fixtures by position. Match lookup
could select a different run through unscoped/substring fallbacks. Batch runs
did not supply state archive paths for later 3D playback.

Additional findings and fixes:

- GRF already gives each controlled side its own canonical observations and
  rotates away actions. Removing Footy's second rotation restores correct away
  control. Features were compared against TiKick's upstream encoder for both sides.
- Use each observation's actual active-player ID; GRF's ten controlled players
  are not simply outfield player IDs 1 through 10.
- Load `backend/checkpoints/tikick/actor.pt` strictly and record its SHA-256 in
  every match. Expose direct football actions 0–18; action 19 delegates to GRF's
  built-in AI, which previously dominated the actor's selections.
- GRF's Python renderer can return a cached kickoff image after restoring a
  state. Explicitly redraw the native engine without stepping physics, then
  check the restored ball, players, score and game mode before encoding.
- Capture native goal-crossing states before GRF advances past stopped play.
  Show those recorded states before the corresponding kickoff reset, and derive
  the scoreboard from the native score. Render no new match simulation.
- Invalidate videos made with the stale-frame renderer and reject video sidecars
  whose match ID differs. Keep replay lookup within the selected season run.

Run `backend/verification/run_season.py` to create an isolated season. Follow with
`audit_native_replays.py` in the installed GRF environment and `audit_season.py`
after completion. `export_replay_views.py` makes every verified match playable;
`render_sample.py` produces a complete native 3D sample from its original archive.

This validates the installed GRF scenario's football rules and replay contract.
It does not certify all IFAB provisions: regulation stoppage time, a complete
substitution system, injuries and extra time require separate gameplay work.

Completed evidence (4 October 2026): run `run_1791069061_b159ac` passed all 380
fixtures, 1,140,380 restored canonical states and 394 native goal states. Every
club played 38 matches; the published final table matched recomputed results.
All 380 recorded matches are playable, with a complete native 3D sample.
Artifacts are in `backend/verification/season_20261004_001100`; its
`season_audit.json` records no failures and `verification_results.md` states
the checks and limits. The local viewer is served at `http://127.0.0.1:8768/`.

Follow-up: the official checkpoint was verified byte-for-byte against TiKick's
published download. Its original Kaggle action allowance is 20, not 19. Current
inference restores that allowance and disables Footy's action overrides by
default. The archived 380-match run remains evidence for its earlier modified
profile; it is not a season run with the restored profile. A fresh full native
match with restored inference passed 3,001 state comparisons and seven goal
state checks. See `tikick_checkpoint_verification.md` for the comparison and
the actual project frontend on port 5173.

Fresh full-season evidence (5-6 October 2026): run `run_1791240220_7b08d5`
uses the restored 20-action TiKick Kaggle profile with tactical overrides disabled.
All 380 fixtures passed 1,140,380 native state comparisons and 1,874 goal-state
checks. Chelsea won with 68 points; every club played 38 games and the final
published table matched recomputed results. Both seven-player benches are saved
for every fixture; all 2,862 players have attributes and valid club squad numbers.
The successful season took 38m 38s on 10 CPU workers, verification 8m 30s, and
a complete 720p native replay sample 2m 52s. Timing artifacts and verification
notes are in `backend/verification/season_20261005_234339`.
The actual project frontend refreshes after each committed batch. Native replay
rendering now publishes frame progress and atomically publishes finalized video;
refreshing the page restores job progress and waits for loaded video data.
Native substitutions remain a separate unsupported gameplay feature.
