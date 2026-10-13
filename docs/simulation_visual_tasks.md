# Simulation visual upgrade checklist

Update this list only after implementation and its relevant checks pass. Keep unfinished native-engine work unchecked.

## Baseline
- [x] Audit production resolution, team/player identity, animations and cameras.
- [x] Probe genuine 1080p and 4K frames in isolated native processes.
- [x] Inventory native animations and research open-licensed alternatives.

## First delivery — broadcast identity and presentation
- [x] Add a shared club-colour registry with aliases and deterministic unknown-club fallback.
- [x] Carry actual roster IDs, shirt numbers and positions into recorded match metadata.
- [x] Show real shirt numbers in starting-XI cards and 2D player markers; label missing historical numbers honestly.
- [x] Replace start, half-time and full-time screens with frontend-themed rounded cards and matching fonts.
- [x] Apply club colours consistently to team panels, score graphics and radar.
- [x] Generate and inspect preview screens; test compatibility with existing recordings and canonical match results.
- [ ] Add frontend selection of the implemented warm/light video-card theme (default broadcast remains midnight).

## Native identity
- [ ] Add selected home/away/goalkeeper kit definitions and clash rules.
- [ ] Bind club kit textures and player numbers to native 3D players.
- [ ] Persist player appearance by player ID and bind it to native models.
- [ ] Freeze visual identity in each match so replays preserve it.

## Resolution and motion
- [ ] Make native renderer resolution configurable and handle cached renderer environments correctly.
- [ ] Expose verified 720p/1080p profiles in API and frontend controls.
- [ ] Benchmark full native 1080p playback and validate frame count, timing and publication.
- [ ] Prototype smooth 30 fps presentation without changing simulation timing or physics.
- [ ] Benchmark 4K before exposing it as a supported full-match profile.

## Cameras and animation
- [ ] Expose native presentation-only camera presets and controlled transitions.
- [ ] Add an event-driven replay/camera director and scorer close-ups.
- [ ] Improve native goal/celebration presentation and transitions.
- [ ] Prototype a verified open-licensed celebration clip and rig conversion.
- [ ] Verify camera/animation changes preserve scores, attribution and authoritative ball paths.

## Delivery verification
- [x] Run portable tests, appropriate native replay checks, frontend checks and visual review for the implemented milestone.
- [x] Produce a short recorded before/after sample.
- [x] Commit and push the tested milestone; record remaining limitations.

Reference: [visual audit](simulation_visual_audit_2026_10_13.md).

## First milestone evidence
- Six screen previews: `docs/evidence/simulation_visuals/` (illustrative statistics; unknown historical numbers shown as dashes).
- Recorded replay: 200 existing steps re-rendered; source SHA256, physics hash and summary preserved (`replay-proof.json`).
- Local video comparison: `backend/verification/tmp/clay-before-after.mp4`.
- Targeted broadcast/replay checks: 21 passed. Frontend: 13 tests passed; lint has zero errors; production build passed.
- Full host backend suite including available WSL adapter checks: 190 passed, 11 skipped in 255 seconds.
- Installable package checked for both bundled fonts and their SIL OFL notices.
- Implementation pushed as `2a957ce` on `codex/project-roadmap-updates`. Native kits/models, video resolution controls, motion and cameras remain pending above.
