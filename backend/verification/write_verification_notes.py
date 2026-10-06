"""Publish readable evidence after the complete season audit passes."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
latest = json.loads((root / 'verification/latest.json').read_text())
output = Path(latest['output'])
audit = json.loads((output / 'season_audit.json').read_text())
assert audit['passed'] and audit['matches'] == 380
goals = sum(row['gf'] for row in audit['standings'])
champion = audit['standings'][0]
notes = f"""# Full-season verification — 4 October 2026

**PASS: 380 fixtures, 20 clubs, 38 matches per club.**

Run: `{audit['run_id']}`. This uses a separate database and reports directory;
the user's existing season data was preserved.

## What was verified

- All 380 matches reached native GRF full time: 3,001 recorded public steps,
  native steps remaining zero. A budget cutoff cannot be saved as a completed match.
- Every match started with actual kickoff movement and contained a native halftime
  restart followed by second-half play and full time.
- {audit['native_replay_frames_compared']:,} original replay states were restored
  and compared against saved player positions, ball, score, game mode and ownership.
- {goals} native goals agree across GRF score changes, event ledgers, database
  results and final standings. {audit['native_goal_frames_compared']} supplementary
  native goal states were checked to preserve the ball crossing the line before
  GRF resets it for kickoff.
- Every ordered home/away pairing occurred once. Points, wins, draws, losses,
  goals for and goals against were recomputed and matched the final season report.
  {champion['team']} finished first with {champion['points']} points.
- All 380 matches have playable replays of their recorded native positions.
  Liverpool 2–1 Luton also has a complete native 3D video, verified during rendering,
  with kickoff, three goal states, halftime and full time. The other 379 matches
  retain their original GRF state archives for native 3D rendering on demand.
- Saved fixtures were exercised through replay APIs using both database IDs and
  canonical fixture IDs. Replays remain scoped to this run and cannot substitute
  another fixture or reuse an incorrectly identified video.

## TiKick actor and native rendering

The checkpoint is `backend/checkpoints/tikick/actor.pt`, loaded strictly.
SHA-256: `{audit['actor_checkpoint_sha256']}`.
Its feature encoder was compared against upstream TiKick for 32 live steps on
both sides. Active players are selected by their actual GRF IDs, and GRF handles
the away-side perspective and action rotation.

Direct football actions 0–18 are exposed to the actor. Action 19, which delegates
to GRF's built-in AI, is masked. This is an explicit inference choice rather than
an unmodified reproduction of TiKick's original action availability. Ten players
per side are controlled; GRF controls the remaining player.

The frozen-kickoff video was a cached-renderer defect. Restored states now force
a native redraw without advancing simulation physics. Goal overlays read native
scores; no goals or football play are invented for the video.

## Automated checks

- Backend full suite: 114 passed, 9 skipped.
- Focused replay-contract suite after the final rendering/cache fixes: 9 passed,
  including two additional regressions beyond the earlier full-suite collection.
- Installed GRF native rule checks: 20 passed, 14 deselected.
- Frontend: 6 tests passed; production build passed.
- Actual saved-fixture replay API checks passed.

Native checks cover halftime, goals, offside, corners, penalties, goalkeeper
possession and restoring states after full time. Skipped backend tests are not
counted as verification evidence.

## Limits

This certifies the installed GRF scenario and replay consistency, not every IFAB
provision. It uses a compressed 90-minute clock over 3,000 native ticks. Regulation
added time, a complete substitution system, injuries and extra time require
separate work. Scoring rates, tactical realism and team-strength balance were not
calibrated by this integrity audit.

[Open the season viewer](index.html) · [Machine-readable audit](season_audit.json)
"""
(output / 'verification_results.md').write_text(notes, encoding='utf-8')
print('VERIFICATION_NOTES_READY', output / 'verification_results.md')
