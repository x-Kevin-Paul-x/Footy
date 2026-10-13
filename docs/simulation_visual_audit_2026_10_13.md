# Simulation appearance and broadcast audit

Inspected: 13 October 2026. This is a source/asset audit with isolated native frame probes, not an implementation change. The installed native engine is loaded from the neighbouring Baller GRF checkout. The Burnley–Bournemouth recording is an existing video: changing the website theme does not change graphics already encoded inside it.

## Current situation

| Area | Verified current behaviour |
| --- | --- |
| Showcase video | 1280×720, 10 fps, 310.7 seconds and 3,107 frames, per its tracked verification manifest. |
| Native scene rendering in production | 1280×720 in both replay engines and the native dump path. |
| Highest explicit export option | 1920×1080 in the state replay engines; the 3D scene is resized from 720p. The public render request currently has no resolution/FPS field. |
| Higher native resolution feasibility | Fresh-process probes produced real 1920×1080 and 3840×2160 RGB frames. These are single-frame checks, not full-video performance or replay compatibility certification. See [raw probe](evidence/visual_resolution_probe.json). |
| Team graphic colours | A hash of the team name selects one of 15 colours. Burnley becomes `#2196f3`; Bournemouth becomes `#ff5722`. This is deterministic but is not a club identity/kit registry. |
| Native 3D kits | The native match uses built-in TeamData IDs 3 and 8, with Barcelona/Real Madrid texture paths and a shared goalkeeper-kit path. Footy's team-name colours only reach graphics/radar; no per-club kit binding reaches native players. |
| Player names | Footy lineup names map to native roster indices, allowing named events and graphics. This is logical identity, not an appearance binding. |
| Shirt numbers | Real squad numbers exist in the database and assignment helper. The starting-XI screen and 2D tokens print lineup index + 1. The trajectory manifest has names but no roster ID/jersey-number arrays. There is no demonstrated Footy-number binding to native shirts. |
| Faces/body/hair | Native PlayerData supplies built-in/default height, skin and hair values. GRFPlayerProfile carries names/IDs and football ratings, but no visual appearance fields. A Footy player does not have a persistent linked visual avatar. |
| Cameras | Native C++ contains wide, bird's-eye and tele camera branches and a goal-scorer close-up. `camMethod` is hardcoded to wide (1); Python/public API does not expose a camera preset/director. |
| Presentation | OpenCV draws static intro/half-time/full-time cards with Hershey fonts, square panels and yellow titles. These do not share the frontend's CSS theme or Outfit/Inter fonts. |
| Timing | State replay defaults to 10 output fps, matching recorded 0.1-second states. Its intro/half-time/full-time holds are 3/3/4 seconds. A legacy dump path writes 15 fps. |

### Code evidence

- `backend/src/logic/grf_renderer.py`: name-hash palette; lineup-index numbering; static cards; 2D tokens and goal replay treatment.
- `backend/src/logic/replay/persistent_replay_engine.py`: 720p native environment, optional 1080p resize, one frame per recorded step, native goal states and card holds.
- `backend/src/logic/replay/replay_pipeline.py`: corresponding production state replay/export path.
- `backend/src/schemas.py`: render request exposes mode/force, not resolution, FPS or cameras.
- `backend/src/logic/squad_numbers.py` and `backend/src/database/models.py`: persistent squad-number capability.
- `backend/src/logic/footy_grf_adapter.py` and `backend/src/logic/grf_trajectory.py`: profile/manifest identity fields and missing visual identity fields.
- Native `src/data/matchdata.cpp`, `teamdata.cpp`, `playerdata.cpp`, `onthepitch/team.cpp` and `onthepitch/match.cpp`: default teams, kit loading, appearance and cameras.

The initial higher-resolution probe reused an already initialized 720p graphics engine and failed with a frame-size mismatch. Separate processes correctly rendered 1080p and 4K. A future resolution setting must recreate or correctly key cached renderer environments; simply changing the Python config on a reused engine is insufficient.

## Native animation inventory

The inspected native data contains **293 `.anim` files**, including ten templates. This is an asset count, not 293 distinct actions guaranteed to appear in a match. Motion selection/blending creates additional variations.

| Category | Files | Purpose |
| --- | ---: | --- |
| movement | 49 | Locomotion and directional movement |
| movement_special | 16 | Special movement variants |
| ballcontrol | 45 | Ball-control/dribbling movements |
| trap | 40 | Receiving/control movements |
| pass | 37 | Passing variants |
| highpass | 15 | Lofted-passing variants |
| shot | 17 | Shooting variants |
| deflect | 28 | Deflections and saving-related variants |
| interfere | 7 | Challenges/interference |
| sliding | 6 | Sliding variants |
| trip | 19 | Trips/falls |
| celebration | 3 | `happy_extreme`, `happy_normal`, `sad_normal` |
| special | 1 | Special-purpose clip |
| templates | 10 | Animation templates |

[Complete inventory](evidence/visual_animation_inventory.json). Native goal/celebration frames can be replayed when the corresponding `.goals.json` and `.goals.grfstate` sidecars were recorded. Older recordings without these states cannot recover the original missing animation merely from the final score.

## Recommended visual improvements

### 1. Establish team and player visual identity

Create one team-ID registry containing display colours, home/away/goalkeeper kits and clash rules. Club graphics and selected match-kit colours should be related but distinguishable: an away kit can differ from a club's primary brand colour. Burnley's traditional claret/blue and Bournemouth's red/black are supported by [Burnley's club description](https://www.burnleyfootballclub.com/media-article/2023-24-home-kit-for-our-premier-league-return) and [Bournemouth's current home shirt](https://superstore.afcb.co.uk/products/mens-home-shirt-26-27-red-black).

Persist player appearance by player ID: jersey number, body preset, height, skin/hair choices and boots. Freeze the selected roster IDs/numbers/appearances and kit IDs in the match manifest. Use that same mapping in lineup cards, scorer graphics, radar and native kit/avatar setup. Do not infer a player's appearance from their name or shuffle it with lineup position.

### 2. Improve sharpness and motion together

Start with a true 1080p scene and a scalable overlay layout. 4K frames are possible, but full-match runtime, VRAM/storage and encoding still need a benchmark. 1080p and 4K contain 2.25× and 9× the pixels of 720p, respectively; that is not a measured runtime multiplier.

Aim for 30 fps presentation before chasing 4K. Existing captures contain roughly ten states per second. Merely changing the encoder to 30 fps makes a one-frame-per-state replay run three times faster. Repeating frames retains timing but does not add smooth motion. Interpolated visual poses/camera motion or a renderer that draws between saved states is needed; goal/ball-contact frames must remain faithful to the authoritative timeline. Changing simulation physics stepping to obtain smooth video would change the match.

Improve encoding quality, antialiasing, turf/lighting consistency and readable HUD sizing after the resolution/timing contract is correct. Higher resolution alone will not modernize old models and animation blending.

### 3. Match the broadcast screens to the frontend

- Use the frontend's light/dark colour tokens, rounded clay panels, restrained inner highlights, Outfit headings and Inter body text.
- Keep global Footy branding in navy/cream/teal/orange; use actual club colours for team cards, score chips and accents. Avoid changing the whole brand palette to whichever club is playing.
- Pre-match: two team cards, genuine squad numbers/positions, formation diagrams and optional benches. Allow enough reading time or staged reveals rather than displaying 22 names for only three seconds.
- Half-time: actual first-half score/stat snapshot, clear comparison bars and concise scorers/events. Use the first-half timeline, not final-match totals.
- Full-time: prominent score, scorers with times, final stats and a player-of-the-match card only when supported by recorded data.
- Add gentle fades/slides and a short branded replay transition. Keep the in-play scorebug small enough to preserve the view of the ball.

Use shared design tokens and resolution-aware typography. HTML/CSS or SVG templates can reuse the visual system; a cached image/compositing path can avoid expensive per-frame UI rendering. Re-render a video from its recording to change its encoded presentation; redeploying the webpage alone cannot restyle old video cards.

### 4. Add a restrained camera director

First expose the existing native camera controls for presentation: stable wide camera for play, slower eased tracking, modest shot zoom, scorer close-up after goals, and replay-only tele/behind-goal views. Cuts should follow recorded events, not arbitrary timers. A cropped 2D frame does not create a genuine new 3D angle; alternate angles need a native camera override after restoring the recorded state.

Keep camera, kit texture and celebratory presentation changes separate from match outcome generation. Preserve scores, player attribution, recorded ball path and replay timings.

## Open-source/open-licensed candidates

| Candidate | Verified licensing / suitability | Integration reality |
| --- | --- | --- |
| [KayKit Character Animations](https://kaylousberg.com/game-assets/character-animations) | Creator lists CC0, 133 humanoid animations, including waving/cheering and locomotion. Useful for celebration prototypes. | FBX/glTF; needs rig retargeting and a GRF exporter or another presentation renderer. Not a football-specific kick/save library. |
| [MakeHuman/MPFB core assets](https://static.makehumancommunity.org/about/license.html) | Core graphical assets are CC0; application code has separate GPL/AGPL terms. Useful for configurable bodies/faces. | An appearance-generation option, not a complete football animation pack. Check community assets separately. |
| [Kenney Animated Characters](https://kenney.nl/assets/animated-characters-protagonists) | Creator labels the pack CC0. Suitable for a deliberately stylised prototype. | A different visual style from the current native models; not an automatic GRF replacement. |
| [Godot + Phantom Camera](https://github.com/ramokz/phantom-camera) | MIT camera plugin with damped following, group framing and camera transitions. | Relevant to a separate Godot presentation renderer, not a plugin for GRF's C++ engine. |

[Mixamo](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) permits royalty-free characters/animations in projects, but is not an open-source asset library; do not assume raw files can be redistributed in this public repository.

Quaternius animation-pack pages still advertise CC0, while its [general licence](https://quaternius.com/license.html), updated August 2026, restricts standalone asset redistribution. Treat this as a pack/archive-specific verification item before bundling assets; do not label every current download CC0 based on older recommendations.

Generic libraries help with cheering and movement, but convincing ball contact, goalkeeper saves and knee-slide celebrations may still need custom football clips. GRF uses its own `.anim`/object/skeleton pipeline; FBX/glTF clips are not drop-in replacements. Gameplay animation can affect touch physics, so replacing it is more invasive than adding cosmetic post-goal presentation.

## Suggested delivery order

1. Shared club-colour registry, correct lineup numbers and frontend-themed start/half/full-time cards.
2. Genuine 1080p render profile, renderer-cache handling, quality settings and resolution controls.
3. Stable player appearance and native kit/number integration.
4. Smooth presentation timing, camera presets and native goal/replay polish.
5. Only then prototype imported celebration clips or a separate presentation renderer.

Keeping GRF for match physics and improving its existing broadcast path is the smaller first investment. A Godot presentation layer offers more control over modern rigs, cameras and effects, but needs a faithful trajectory/pose bridge and its own visual regression tests. The [GRF upstream repository](https://github.com/google-research/football) is currently archived, so native enhancements should be treated as maintained project code rather than expected upstream features.
