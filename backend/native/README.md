# Native visual runtime

This adds render-only materials, recorded player labels, camera presets and an
isolated animation preview to the compatible GRF runtime used by Footy. It does
not install over GRF, modify the neighbouring Baller checkout, add animation
entries to GRF's authoritative collection, or change serialized physics fields.

Build in WSL with the same Python/Boost version as the existing GRF installation:

```sh
/root/venv_baller/bin/python3 backend/native/build_visual_runtime.py \
  /mnt/c/Users/kevin/OneDrive/Desktop/Projects/Baller/third_party/gfootball/third_party/gfootball_engine
```

The builder copies source into ignored `backend/native/runtime/visual`, patches
only that copy, records source hashes, builds it, and atomically publishes the
extension. `--incremental` rebuilds this copy after local changes. A new source
checkout should use a fresh runtime directory. Replay workers select the built
extension before importing GRF; simulation workers retain the existing runtime.

Without this build, ordinary saved-state replay remains available. Native kit,
appearance and camera enhancements require these bindings. Camera requests fail
clearly when they are unavailable. Existing opaque GRF state archives must be
compatible with the source checkout used for the build.

Player appearances are stored under `FOOTY_DATA_DIR/player_appearances.json`
with file locking, then frozen alongside roster IDs, shirt numbers and selected
kits in each new match manifest. Only cosmetics are changed: body height and
physical ratings retain their recorded behavior. Older recordings do not gain
invented player IDs or shirt numbers.

Native 720p/1080p rendering uses matching framebuffers. The unkeyed idle GRF
renderer cache is discarded when creating a new context; frame dimensions are
checked rather than silently resized. The renderer reads RGB pixels directly
and corrects OpenGL's vertical origin. Footy's HUD and radar replace the native
debug scoreboard/radar, and recorded names replace hardcoded debug names.

Public replay settings are resolution (720p/1080p), studio theme (midnight/warm)
and camera (broadcast/overhead/sideline/director). The director reads canonical
goal events and eases into a close-up of the recorded scorer. It advances no
physics. Rendering requires a saved state archive for HD/camera presets; older
dump-only playback retains its compatibility path.

Experimental work is kept separate:

- `logic.replay.smooth_video.export_smooth_video` makes a separate 30 fps optical
  flow export. Duration and event PTS stay fixed; interpolated frames are marked
  as such. Fast motion can show interpolation artifacts.
- The benchmark CLI accepts 4K privately. Full software rendering was much
  slower than 1080p, so 4K is not a public supported profile.
- `render_presentation_clip` previews the CC0 cheer on a frozen native state.
  This prototype does not replace gameplay or register animation IDs. Rig
  conversion needs further artistic refinement before production use.

Verification commands are in `backend/benchmarks/benchmark_replay_presentation.py`
and `backend/benchmarks/verify_native_visuals.py`. Evidence is summarized in
`docs/evidence/simulation_visuals/native-upgrade-proof.json`.
