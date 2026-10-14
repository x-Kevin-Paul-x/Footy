# Contributing to Footy

Use Python 3.12 for the backend and Node 20 for the frontend. Install from the repository root; the editable package provides backend imports and command entry points.

## Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ml,media]"
npm ci
npm --prefix frontend ci
npm run dev
```

## Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,ml,media]'
npm ci
npm --prefix frontend ci
npm run dev
```

Real GRF needs its compatible Linux runtime, TiKick actor checkpoint and FFmpeg; installing Footy's extras does not install the native football engine. Windows runs native matches through the configured WSL environment. macOS supports the portable application/domain checks; native setup must be verified separately. Restart the application and persistent native workers after upgrading replay formats.

## Verification

```text
python -m pytest backend/tests -ra --cov=backend/src
python -m pytest backend/commentary/tests -ra
python -m ruff check backend/src backend/tests backend/benchmarks
python -m mypy
npm --prefix frontend test -- --runInBand
npm --prefix frontend run lint
npm --prefix frontend run build
```

Tests isolate database state. Set `FOOTY_REPORTS_DIR` to a disposable directory when running integration checks. Native tests should be run inside the GRF environment as well; Windows skips do not prove those tests pass. Coverage is reported without implying that untested rendering/physics paths are verified. Ruff currently gates runtime/syntax errors; mypy starts with path containment and frame timelines and will expand incrementally.

Production schema changes use `footy-migrate` (or `python -c "from database.migrations import main; main()"`). It makes a SQLite-backup snapshot before pending upgrades and verifies foreign keys. Test empty, metadata-created and legacy stamped databases before changing revision history. Database saves preserve committed data and pinned artifacts; they do not resume an interrupted in-memory match.

## Reproduce manager results

For each training seed 42, 43 and 44:

```text
python -m ml.train_rl train --episodes 100 --seed 42 --teams 6 --season-length 20 --output-dir docs/evidence/training/seed_42
python -m ml.train_rl compare --models backend/src/ml/models/dqn_seed_42.pt backend/src/ml/models/dqn_seed_43.pt backend/src/ml/models/dqn_seed_44.pt backend/src/ml/models/dqn_best.pt --episodes 30 --seed 1000 --teams 6 --season-length 20 --report-dir backend/reports/ml_reports
```

Copy each final training checkpoint to its corresponding registered `dqn_seed_<seed>.pt` filename before comparing a newly trained set. The published manifest records model hashes. Manager evaluation uses the synthetic management environment; TiKick drives the native players. DQN performance need not exceed the baselines for a valid result.

## Long-run and native checks

```text
python backend/verification/stress_campaign.py --seasons 5 --seed 42 --output backend/verification/tmp/stress.json
python backend/run_3_seasons.py
```

The first checks domain/economy rollover without GRF. The second uses the configured match engine in isolated data/report directories and can take hours. Canonical results, event attribution, fixture uniqueness, and archive integrity must stay deterministic across worker counts. `FOOTY_DYNAMIC_TACTICS=1` is an experimental, opt-in policy-modulation profile; measure its native outcomes before changing the default.

The manual native workflow requires a self-hosted Linux runner labelled `grf`, with Footy's dependencies, GRF, the actor checkpoint, FFmpeg, and compatible rendering/encoding drivers already configured. Its broadcast certification uses the current NVIDIA/D3D12 profile. The workflow fails its preflight when the required native import or checkpoint is absent; standard hosted CI does not provide this runtime.

To build the read-only demo: `python scripts/export_demo.py`. Serve the output with `python -m http.server --directory backend/verification/tmp/demo 8080`. The manual GitHub Pages workflow publishes only curated static recordings and evidence.

Do not commit databases, runtime archives, downloaded speech models, private environment files, or generated verification workspaces. Keep new features reviewable across schema, domain, API, client types, UI and failure tests.
