# Fresh season verification and timing

Run: run_1791240220_7b08d5

- Successful full-season wall time: 2317.940 seconds (38m 38s).
- Time inside 38 sequential native matchday batches: 2165.708 seconds (36m 6s).
- Setup, transfers, database synchronization and season reports: 152.232 seconds (2m 32s).
- Native replay audit: 506.046 seconds; complete verification: 509.803 seconds (8m 30s).
- Complete 720p 3D sample render: 171.610 seconds (2m 52s), match row 1.
- Matchday timing range: 49.719 to 64.925 seconds.
- Effective throughput: 6.100 seconds per completed fixture. This is throughput with 10 parallel CPU workers, not individual match latency.
- Initial attempt stopped after 547.022 seconds (9m 7s) for a player attribute synchronization fix. It is preserved separately and excluded from the successful run's timing.
- Recordings directory: 49.20 GiB, including videos rendered in the app.

## Verified results

380 unique fixtures, 20 clubs with 38 games each. Chelsea won with 68 points.
Every saved result, goal event and published final standing matches its recording.
1,140,380 native states and 1,874 goal states restored without mismatches.
Each match reached native full time, reset at halftime, and moved the ball from kickoff.
The checkpoint hash is 5e8157c79353cc916464faa0b2feba07ab4bdcf7b521060c85a19e86686dcef5.
Original TiKick Kaggle inference is used: all 20 actions available, builtin AI allowed, Footy tactical action overrides disabled.

All 2862 players have saved attributes, club squad numbers are unique, and all 760 benches have seven selected players.
Native substitutions are still unsupported; recorded benches are not evidence of substitutions.
Assists are shown as untracked when no real assist event exists.

## Frontend and replay loading

The project frontend is connected to this isolated season on port 5173; earlier seasons remain intact.
It polls the run and refreshes standings, results and player data whenever a new batch commits, including externally started seasons.
Observed automatic progression from 20 to 40 fixtures, and final table at 38 games per club.
The current production loop commits groups of 20 matches, with 10 at each half's end.

Replay progress is now written during native frame rendering, with a persisted job start time.
Refreshing an active job restores its progress and elapsed time even if a stale video URL was supplied.
An MP4 is not ready without a complete index; native videos also require the matching native timeline.
The native renderer encodes to a temporary file and publishes the final file after encoding and timeline validation.
Playback controls wait for actual loaded video data; failures expose retry controls.
A real refresh recovered 52% and 105 seconds elapsed, then automatically loaded a 310.4-second replay with readyState 4 and controls enabled.

Validation: 19 targeted backend tests, 9 frontend tests and production frontend build passed.

The user's match 372 also loads with readyState 4, enabled controls and a 310.7-second duration. Its six goal highlights appear once each. The fixed match page is left open in the project frontend.

Final completion metadata also agrees with the saved fixtures: 380/380. The stale halftime completion counter was fixed to count persisted rows, with a regression test excluding fixtures from other runs. The expanded season audit passes again.

## Final release checks and curated recording

- Full backend suite: 128 passed, 9 skipped in 221.85 seconds.
- Frontend: all 9 tests passed; production build passed.
- Burnley 2–4 Bournemouth full recording compressed to 37,349,145 bytes (37.35 MB), preserving 1280×720, 10 fps, 3,107 frames and 310.7 seconds.
- Video SSIM against the original: 0.980933.
- README GIF: 2,893,813 bytes (2.89 MB), 480×270 at 6 fps, ten-second opening-goal excerpt.
- Runtime recording replaced with the same compressed MP4, and matching native-timeline readiness validation passed.
- Curated copy, timeline and provenance: `assets/matches/full-match-recordings/`.
- New simulations now remove previous runtime recordings by default; these curated assets are preserved.
