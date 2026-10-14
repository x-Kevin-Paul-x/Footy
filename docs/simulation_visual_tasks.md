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
- [x] Add frontend selection of the implemented warm/light video-card theme (default broadcast remains midnight).

## Native identity
- [x] Add selected home/away/goalkeeper kit definitions and clash rules.
- [x] Bind club kit textures and player numbers to native 3D players.
- [x] Persist player appearance by player ID and bind it to native models.
- [x] Freeze visual identity in each match so replays preserve it.

## Resolution and motion
- [x] Make native renderer resolution configurable and handle cached renderer environments correctly.
- [x] Expose verified 720p/1080p profiles in API and frontend controls.
- [x] Benchmark full native 1080p playback and validate frame count, timing and publication.
- [x] Prototype smooth 30 fps presentation without changing simulation timing or physics.
- [x] Benchmark 4K before exposing it as a supported full-match profile.

## Cameras and animation
- [x] Expose native presentation-only camera presets and controlled transitions.
- [x] Add an event-driven replay/camera director and scorer close-ups.
- [x] Improve native goal/celebration presentation and transitions.
- [x] Prototype a verified open-licensed celebration clip and rig conversion.
- [x] Verify camera/animation changes preserve scores, attribution and authoritative ball paths.

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
- First milestone pushed as `2a957ce` on `codex/project-roadmap-updates`. The remaining work is covered by the second delivery below.


## Second delivery verification
- [x] Add native club kits, real jersey textures, persistent cosmetics and recorded player labels.
- [x] Verify 720p → 1080p → 720p context changes, cameras and isolated celebration poses against exact saved observations.
- [x] Benchmark complete 1080p/4K recordings and the final native director presentation; preserve all source hashes.
- [x] Verify 30 fps prototype duration and event timestamps without changing the original replay.
- [x] Run backend suite (196 passed, 11 skipped), final affected checks (17 passed), frontend tests (14 passed), lint, typing and production build.
- [x] Verify names-only recording compatibility and defensive freezing of cosmetics (29 targeted checks passed).
- [x] Commit and push the remaining simulation visual upgrades.

Evidence: `docs/evidence/simulation_visuals/native-upgrade-proof.json` and native gameplay/goal screenshots.
Implementation pushed as `4b42df8` on `codex/project-roadmap-updates`.
Full recording: 3,108 frames. 1080p: 292.85 seconds; private 4K benchmark: 1,008.23 seconds; final 720p director export: 160.48 seconds.
The first 1080p/4K runs measured native rendering throughput; the final RGB/orientation, HUD, kit and camera presentation was visually reviewed in the 720p director export and 720p/1080p native checks.

Production controls expose 720p/1080p, warm/midnight studio cards and broadcast/overhead/sideline/director cameras. The isolated native visual runtime is built locally; reproducible build instructions are in `backend/native/README.md`.
The 30 fps optical-flow export and CC0 cheer rig conversion remain explicitly experimental prototypes. 4K remains a private benchmark profile because of its full-match render cost.
Legacy recordings retain unknown IDs/numbers; native cosmetics are frozen for new recordings. Native close-up/animation proof screenshots use a deliberately synthetic cosmetic fixture to demonstrate number 47 and appearance binding on unchanged recorded match states.
