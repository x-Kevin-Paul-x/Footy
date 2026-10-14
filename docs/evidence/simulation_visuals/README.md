# Broadcast presentation previews

Dark and light PNGs demonstrate the new card renderer. Starting-XI names match
the supplied screenshot, but that historical image did not contain persistent
shirt numbers, so previews display a dash. Full-time statistics are illustrative
preview values, not a newly simulated or reconstructed match.

New recorded manifests capture player IDs, assigned positions and persistent
jersey numbers through the existing squad-profile pipeline. Legacy recordings
remain valid; absent identity is never reconstructed from today's database.

`replay-proof.json` records a separate 200-step existing trajectory re-render.
The source archive SHA256, physics hash and canonical summary stayed unchanged.
Its generated video is a local verification artifact at
`backend/verification/tmp/clay-recorded-replay.mp4`.

Broadcast cards default to the midnight theme. The warm theme is implemented
and selectable through the replay controls, alongside 720p/1080p quality and
native camera presets. The second delivery connects native club kits, shirt
numbers, cosmetics and recorded player labels through the isolated visual
runtime described in `backend/native/README.md`.

`native-gameplay.png` and `native-goal.png` come from the final complete director
export of an isolated generated match. Its generic player names are recorded
fixture names. `native-kits-closeup.png` and the celebration preview use an
explicit synthetic cosmetic fixture (including shirt 47) on unchanged saved
states; they do not reconstruct historical identity.

`native-upgrade-proof.json` includes complete 1080p/4K throughput results and
final camera/material/animation checks. 30 fps optical flow and the CC0 cheer
conversion remain experimental; 4K is not a public supported profile.

The README hero GIF at `assets/readme/native-goal.gif` is an eight-second
excerpt of that same final director export, beginning at 34.2 seconds around
the first goal (event timestamp 36.2 seconds). It is encoded at 720×405 and
10 fps with an infinite loop; playback uses the original recorded speed.
