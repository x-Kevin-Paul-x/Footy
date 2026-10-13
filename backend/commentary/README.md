# Local match commentary

Commentary is generated from the saved simulation trajectory and presentation timeline.
It adds audio to the existing video; it never runs another match. The video stream is copied
and its packet hash is verified against the source.

The default example is Burnley 2–4 Bournemouth, match `match_2026_20_3`.
Keep the original silent GitHub asset and the earlier commentary output for comparison.
The revised output is under `output/improved/`; runtime artifacts are under
`artifacts/improved/`. These paths, downloaded models, binaries and the isolated
speech environment are ignored by Git.

## Changes and findings

- The original 46-clip manifest contained **19 clips exceeding their windows**.
  The old mixer moved later speech and extended the speech timeline beyond the video.
  The new synthesizer tries complete shorter alternatives, permits at most 10% time
  compression, and fails explicitly if nothing fits. The mixer preserves event anchors.
- Clips were cached by ID alone. Cache signatures now include all text alternatives,
  speaker, style, window and model revision; modifying a line invalidates its audio.
- The old prompts explicitly prescribed the repeated partner-name and “clinical finish”
  exchanges. Ryan now handles live action; Aiden gives occasional concise aftermath.
  Recent-line memory spans 12 accepted lines, and stock phrases are rejected.
- Every alternative is checked, including emergency lines: current score, scorer,
  known player identity, temporal fact availability, unsupported movements and player
  gender. A future goal cannot enter a buildup fact whitelist.
- Observed possession and goalward ball acceleration supply pre-goal anticipation.
  Built-in GRF AI actions do not expose every kick. An unowned volley cannot safely
  identify its shooter from proximity alone, so it remains unnamed until the recorded
  goal attribution becomes available.
- The RTX 5070 passed an actual CUDA operation after upgrading the isolated speech
  environment to PyTorch 2.7.1/CUDA 12.8. Qwen speech now uses the GPU automatically.
  A neural failure is reported rather than silently swapping both speakers for SAPI.
- Replaced the 75 Hz synthetic hum with a credited stadium sample, quiet crossfades,
  event-driven swells, speech ducking and final loudness control. This general crowd
  recording is **not** authentic audio from the simulated match. See
  [sound attribution](assets/ATTRIBUTION.md).

## Research behind the changes

[MatchTime, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.99.pdf) treats fine-grained
video/commentary alignment as a central problem. Here timestamps belong to Python and
the recorded trajectory; the language model cannot choose or move them.

[Qwen3-TTS documentation](https://github.com/QwenLM/Qwen3-TTS) describes natural-language
delivery instructions for CustomVoice. The revised instructions distinguish a measured
analyst from urgent live calls, avoiding a screaming instruction on every goal.

[FFmpeg filter documentation](https://ffmpeg.org/ffmpeg-filters.html) provides the
resampling, time adjustment and loudness tools used in the audio stages.
[PyTorch 2.7 announcement](https://pytorch.org/blog/pytorch-2-7/) documents Blackwell
support with CUDA 12.8.

## Running

From the repository root, with the local models and speech environment installed:

```powershell
.venv/Scripts/python.exe -m backend.commentary.cli --tts-engine qwen --artifacts-dir backend/commentary/artifacts/new-run --output-dir backend/commentary/output/new-run
```

Use a separate artifact directory to preserve earlier versions. The saved trajectory
default points to the current local season and must exist; video alone cannot establish
all factual player events. CLI paths can select a different video, timeline, trace, verification file and goal metadata.
The supplied verification/goal defaults describe the example match; adapting the pipeline
to arbitrary matches also requires their matching metadata. Pass --verification-path and --goals-json-path for those files.

Run regressions with:

```powershell
.venv/Scripts/python.exe -m pytest backend/commentary/tests/unit -q
```

## Validation of the revised example

Twenty tests passed. All six goals have recorded pre-goal buildup.
The 47 final clips fit their windows with no speech overlap. Voice signal onset at each
goal is approximately 15–17 ms after the recorded crossing timestamp; the equalizer
buildup starts at 87.6 s and its reaction at 89.5 s. The original video packets are
unchanged. The output remains 310.7 s, 720p, with 48 kHz stereo AAC audio.

Detailed results: `artifacts/improved/quality_report.json`.
The final script, actual selected spoken alternatives, CUDA execution details and
rejected candidate lines are retained alongside it.

These are timing, factual-rule and audio measurements. Audio listening is not available
in this agent session, so this does not claim a perceptual broadcast-quality score.
The validator is deliberately conservative; its factual fallback can be less expressive
than a human commentator. Crowd audio is added in post-production and must retain its credit.
