# Footy v0.1.0 — draft release notes

This release candidate adds durable simulation and evaluation jobs, tested fresh/legacy database migrations, safe replay archives and media publication, run-scoped campaign history, and a financial ledger with loan and transfer-contract rules. The Saved campaigns page exposes retained squads, contracts, availability and cash movements. Existing commentary work is included with a reproducible golden-match fixture and asset attribution.

Manager results now include three training seeds and thirty held-out scenarios per policy. The measured DQN runs did not outperform the random baseline; the rule-based policy scored highest in this sample. The manager environment is synthetic and separate from TiKick's native player policy. Native worker topology and controlled crash-recovery checks preserve strict archive hashes.

Setup and reproducibility commands are in [CONTRIBUTING](../CONTRIBUTING.md). The [verification report](verification_2026_10_13.md) distinguishes portable, Windows/WSL and direct Linux checks. New manager checkpoint hashes and training provenance are in [the manifest](../backend/src/ml/models/manifest.json); release asset checksums are in [the checksum file](evidence/release_checksums.sha256).

## Known limitations

- Native substitutions remain unsupported; dynamic tactical modulation is experimental and opt-in.
- Database snapshots preserve committed campaign history and pinned recordings. Automatic continuation of an interrupted in-memory campaign is not implemented.
- The retained native season averages 4.93 goals per match against 3.28 in the chosen 2023/24 Premier League reference. Calibration remains open research; scores are not altered to fit a target.
- Native matches require the configured Linux GRF runtime and checkpoint. The API bridge currently uses Windows/WSL; portable CI deliberately skips unavailable native integration checks.
- A read-only demo uses curated recordings and evidence. It does not expose simulation or save-data mutations.

Keep this as a draft while reviewing the branch. The root MIT license applies to original Footy code; external assets retain the terms in [third-party notices](../THIRD_PARTY_NOTICES.md).
