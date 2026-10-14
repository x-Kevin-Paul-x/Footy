# CC0 celebration conversion prototype

`kaykit_cheer_prototype.anim` is an isolated retargeting experiment from the
official KayKit Adventurers `Knight.glb` **Cheer** animation by Kay Lousberg.
The original licence notice is retained as `KayKit-LICENSE.txt`.

Source: https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0
Asset: `addons/kaykit_character_pack_adventures/Characters/gltf/Knight.glb`
Verified SHA256: `60428e3abc09ba83e595d256e3af8c5c976b46cdae599f0802fc82b4a3445168`
Licence: CC0 1.0, confirmed by the creator's repository and included notice.

The converter samples local/global joint rotations, changes glTF Y-up to
native Z-up, maps thirteen native bones and pins root movement. It produces
168 native animation frames. Source and target rest poses differ; this is a
rig conversion prototype for artistic review, not a production goal animation.

It is **not** installed into GRF's simulation animation collection, so existing
state archives keep their animation ordering. Native preview checks validate
the clip parser and mesh pose while requiring exact unchanged player/ball
observations, score and match clock.

Reproduce with `backend/benchmarks/convert_celebration_clip.py` using the verified
source GLB and the compatible native `happy_normal/000.anim` rest-pose template.
