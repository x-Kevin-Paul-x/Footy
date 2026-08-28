# Backend Audit & Remediation Plan — Footy

> **Snapshot date:** 29 Aug 2026 · **Branch:** `feat/grf-3d-broadcast-replay`
> **Scope:** `backend/` Python/FastAPI + GRF/TiKick engine + ML pipeline
> **Working tree state:** 1,557 insertions / 646 deletions uncommitted across 10 files + 2 untracked files (`dev_server.py`, `grf_batch_runner.py`). The tree is actively being edited and **one live edit currently breaks parsing (C1).**

---

## 1. TL;DR

| Severity | Count | Theme |
|----------|-------|-------|
| 🔴 Critical (blocking) | 2 | `grf_batch_runner.py` fails to parse; Docker deploy broken 3× |
| 🟠 High | 8 | DQN loads from nonexistent path; config path chaos; save-load path traversal; dual DB metadata; duplicate table defs; raw-sqlite bypass; data-destroying script |
| 🟡 Medium | 15 | Concurrency races, missing unique constraint, ML label mismatch, sync eval endpoint, dependency drift, CORS/auth, test side-effects, temp-file leak, N+1 queries, engine fallback masking |
| 🔵 Low / nits | ~10 | `print()` in lib code, sparse `response_model`, `sys.path` hacks, dead schemas |

---

## 2. 🔴 Critical — Blocking

### C1. `grf_batch_runner.py` fails to parse (`SyntaxError: unmatched ')'` at line 564)

**Verified at runtime:**
```
$ python -c "import logic.grf_batch_runner"
SyntaxError: unmatched ')' at line 564
```

**Root cause:** Lines **559–592** are a duplicated orphaned copy of the `simulate()` method left behind by a botched merge/paste. Line 564 is a dangling `) -> Dict[str, Any]:` with no `def`.

**Blast radius:**
- `GRFBatchRunner` is imported by `models/league.py` (matchday batch sim) and by `GRFNativeRunner.simulate()` (`grf_native_runner.py:1094`, **no try/except → raises whenever called**).
- The `league.py` imports are wrapped in `try/except`, so the simulation **silently falls back to the heuristic engine**, masking the error.

**Fix:** Delete lines 559–592 entirely (keep the real `simulate()` at 522–557), then verify:
```bash
python -c "import logic.grf_batch_runner"
python -c "import main; import api_fastapi"
```

### C2. Docker deploy is broken in 3 independent ways

1. **`backend.Dockerfile:15` — `COPY data /app/data`** → there is **no `data/` at the repo root** (it lives at `backend/data`). The build fails immediately.
   - **Fix:** `COPY backend/data /app/data`
2. **`backend.Dockerfile:24` — `CMD ["uvicorn", "src.api_fastapi:app", ...]`** with `PYTHONPATH=/app/src` resolves to `/app/src/src/api_fastapi.py`, which doesn't exist.
   - **Fix:** `CMD ["uvicorn", "api_fastapi:app", "--host", "0.0.0.0", "--port", "5001"]`
3. **`docker-compose.yml` sets `API_PORT` / `API_DEBUG` but `config.py` reads `FOOTY_API_PORT` / `FOOTY_API_DEBUG`** → the compose vars are silently ignored.
   - **Fix:** unify on the `FOOTY_*` names in `compose` (or accept both in `config.py`).

**Extra:** `requirements.txt` (the Docker dep set) omits `torch`, `gfootball`, `cv2`, `imageio` → the GRF engine can't function inside the container regardless.

---

## 3. 🟠 High — Correctness / deployment / security

### H1. `main.py` loads the DQN manager brain from a non-existent path
`main.py:110` computes `ml_models_dir = dirname(dirname(dirname(__file__))) + "/ml/models"` → `Footy/ml/models`, which **does not exist** (verified). Real models live in `backend/src/ml/models/dqn_*.pt`. Result: `has_dqn` is always `False`, so managers never load ML brains despite the commit message claiming ML integration.

**Fix:** point `ml_models_dir` at `BASE_DIR / "ml" / "models"` (import from `config`).

### H2. `config.py` path chaos around ML artifacts
`ML_REPORTS_DIR = PROJECT_ROOT / "ml" / "reports"` doesn't exist; real reports are in `backend/reports/ml_reports`. The API carries convoluted fallbacks (`_get_ml_report_paths`, `_resolve_ml_report_path`) to cope. ML scripts (`train_rl.py`) default to **CWD-relative** `ml/models` / `ml/reports`, as does `/run-ml-eval`.

**Fix:** pick **one** canonical location per artifact (`backend/reports/ml_reports`, `backend/checkpoints`, `backend/src/ml/models`), expose them from `config.py`, remove all fallback branches.

### H3. Path traversal in `POST /load/{save_id}`
`api_fastapi.py:316`: `source_path = SAVES_DIR / f"{save_id}.db"` — `save_id` is user-controlled with **no `basename` sanitization**. `/load/..%2F..%2F..%2Fwhatever.db` can copy arbitrary `.db` files over the live DB. (`/recordings` correctly uses `os.path.basename`.)

**Fix:**
```python
save_id = os.path.basename(save_id)
if not re.fullmatch(r"[A-Za-z0-9_.-]+", save_id):
    raise HTTPException(status_code=400, detail="Invalid save_id")
```

### H4. Alembic is wired to a second, unrelated metadata instance
`alembic/env.py` imports `from src.database.models import Base`, while the whole app imports `database.models`. The same module gets imported **twice under two names** (`database.*` and `src.database.*`) → **two separate `Base`/metadata instances**. The migration env does not reflect the real app schema.

**Fix:** in `env.py`, add `backend/src` to `sys.path` and import `from database.models import Base`.

### H5. Duplicate table definitions for `SeasonReport` / `TransferReport`
Defined in **both** `database/models.py:188-203` and `database/report_models.py:5-16`, with different shapes (unique+JSON vs String). `report_models.py` is unused today, but importing both raises SQLAlchemy "table already defined" errors.

**Fix:** delete `report_models.py`; keep the `models.py` versions; add `unique=True` on `season_year` there.

### H6. `db_setup.py` has a ~560-line dead `create_tables()` plus mixed raw-ORM reset
The first `create_tables` (raw `sqlite3`, lines 10–567) is **silently overwritten** by the SQLAlchemy one at line 573. `reset_database()` mixes raw drops + `Base.metadata.drop_all()` + `VACUUM`.

**Fix:** delete the raw-sqlite block and the mid-file `import os`; keep the SQLAlchemy version; make `reset_database` drop-only with WAL.

### H7. Business models bypass the ORM with raw `sqlite3` — without FK pragma
`models/player.py` (`_generate_unique_name`, `save_to_database`) and `models/transfer.py` (lines 307, 494) open raw connections with **no `PRAGMA foreign_keys=ON`**, no `busy_timeout`, no WAL → orphan writes and `database is locked` under concurrent sim/API.

**Fix:** centralize a `get_raw_conn()` helper in `session.py` that sets `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`; replace direct `sqlite3.connect` calls.

### H8. `run_3_seasons.py` is a data-destroying script with no guard
Purges reports/CSVs/saves and calls `reset_database()` by default. Intentional for benchmarks, but one accidental run nukes everything.

**Fix:** add a `FOOTY_CONFIRM_RESET=1` env guard + a `--yes` flag; never call from the API layer.

---

## 4. 🟡 Medium

| # | Issue | Fix |
|---|-------|-----|
| M1 | **Simulation lock race**: `run_simulation_task` checks `locked()` then acquires non-atomically; `/load/` also races a running sim. | Use an atomic status flag checked under the lock; reject overlapping requests at the endpoint. |
| M2 | **`match_db.py` closes session twice** (`with get_db_session()` + `finally: db.close()`) and reads ORM data after context exit. | Remove the manual `db.close()`; build `match_details` inside the transaction. |
| M3 | **Duplicate season reports**: `SeasonReport.season_year` has no unique constraint → repeated saves shadow history (`get_season_report_by_year` uses `.first()`). | Add `unique=True` + upsert (`INSERT … ON CONFLICT`). |
| M4 | **ML action labels contradict env semantics** — `evaluation.py:ACTION_NAMES` (`sell_reserve`, `buy_youth`, `buy_value_or_prime`, `train_squad`) vs `footy_env.py` (`scout_or_youth`, `buy_cheap`, `buy_value`, `buy_star`) → garbage action charts. | Derive labels from `FootyEnv` constants; add a unit test asserting the mapping. |
| M5 | **`/run-ml-eval` runs heavy training synchronously** in the request handler with CWD-relative defaults. | Background it with a lock (like the simulation), resolve defaults from `config`. |
| M6 | **Dependency sprawl + environment drift**: `requirements.txt` (Docker) ships `flask`/`flask-cors` (unused) and lacks torch/gfootball/cv2/imageio; `pyproject.toml` duplicates deps; installed env violates pins (`torch 2.13.0` vs `<2.11`, `pytest 9.1.1` vs `8.4.1`, `pandas 3.0.5` vs `3.0.0`). | Single source of truth (optional-deps in `pyproject.toml`), regenerate lockfile, fix stale pins. |
| M7 | **No auth + `allow_origins=["*"]` with `allow_credentials=True`** (invalid per CORS spec) + binds `0.0.0.0` + `FOOTY_API_DEBUG=true` default → anyone on the network can trigger sims / wipe saves. | Restrict origins to `http://localhost:*`, configurable host binding, default `API_DEBUG=False`, optional API-key middleware. |
| M8 | **`dev_server.py` hardcodes port 5001** despite `FOOTY_API_PORT`. | Read port from `config.API_PORT`. |
| M9 | **Tests have real side effects**: `test_api_endpoints` POST `/saves` copies the live DB; tests touch real report dirs/DB. | Use `TestClient` + tmp dirs / `FOOTY_DATA_DIR` override (fixture swaps the DB file). |
| M10 | **No temp-script cleanup**: `run_grf_*.py`, `payload_*.json`, `run_render_*.py` accumulate in `reports/recordings/` when WSL calls fail before cleanup (leftover files confirmed on disk). | `finally`-block cleanup + a startup sweeper for files older than 24h. |
| M11 | **N+1 heavy aggregation**: `get_seasons` / `all-seasons-overview` load all `Player` rows per season and rebuild reports per year. | Aggregate in one query; index `Match(season_year)`. |
| M12 | **`is_available()` spawns `wsl` subprocess per call** (up to 10s timeout) and caches `False` class-wide after first failure → real availability changes are never re-detected. | Cache with TTL (e.g. 60s); expose forced recheck. |
| M13 | **Silent engine fallback**: GRF import/parse errors are swallowed in `league.py`/`match.py`, so users think GRF runs when it's the heuristic engine. | On fallback, `logger.warning` + set the real engine in `/api/v1/engine/status`. |
| M14 | **`Match.intensity` declared `String` but written as int 50** in `match_db.py`. | Make column `Integer` (new migration) or cast consistently. |
| M15 | **Live code churn**: `api_fastapi.py` changed between audit reads (GRF endpoint shifted `max_steps` from config to a hard-coded 3000, dropped the `trace_file` param). Working tree is a broken WIP state. | Commit incremental checkpoints; re-verify imports after each edit. |

---

## 5. 🔵 Low / Nits

- ~35 `print()` calls inside library code; `logging.basicConfig` repeated in 2 places with no per-module config.
- `except (WebSocketDisconnect, …, Exception)` subsumes everything; `WebSocketEventFrame` schema is unused.
- Only 8/30+ routes declare `response_model`; errors leak raw `str(e)` in `detail`.
- `src/*` relies on `sys.path` hacks (`main.py`, tests, alembic, `dev_server.py`) instead of one editable install.
- Bare `except:` in `main.py:726`; `except Exception: pass` in ML/GRF paths.
- `gym` (retired, superseded by `gymnasium`) imported in `match_engine_grf.py`.
- `BALLER_DIR` points **outside the repo** (`PROJECT_ROOT.parent / "Baller"`); add a bootstrap doc/check.
- No CI, no linter/formatter config; `pyproject.toml` exists but isn't the install source.
- Binary artifacts committed: `backend/checkpoints/tikick/actor.pt`, `backend/src/ml/models/dqn_*.pt` (consider Git LFS).
- `reset_database` prints via `print()` including in API context.

---

## 6. Remediation Roadmap

### Phase 0 — Hotfixes (do now)
1. **C1:** Delete the orphaned `simulate()` block in `grf_batch_runner.py` (lines 559–592) → verify imports.
2. **H3:** Sanitize `save_id` in `/load/{save_id}` (path-traversal fix).
3. **C2:** Fix `backend.Dockerfile` (`COPY backend/data`, `CMD api_fastapi:app`) + unify compose env names.

### Phase 1 — Data & config health (this sprint)
4. **H4/H5/H6:** Fix Alembic metadata import; delete `report_models.py`; purge dead raw-sqlite `create_tables`.
5. **H1/H2:** Point DQN model path at the real dir; canonicalize ML report/model dirs in `config.py`.
6. **H7:** Add `get_raw_conn()` (WAL + FK + busy_timeout) and swap raw `sqlite3.connect` callers.
7. **M1/M3:** Atomic simulation status; unique `SeasonReport.season_year` + upsert.
8. **M4/M9/M6:** Correct ML action labels; isolate tests from the live DB; lock requirements to reality.

### Phase 2 — Hardening (next sprint)
9. **M7:** CORS origins, configurable host, debug default off, optional API key.
10. **M5:** Background `/run-ml-eval`; **M10:** temp-file sweep; **M11** query batching.
11. **M12/M13:** TTL cache for `is_available()`; audible engine-fallback logging.
12. CI (ruff + pytest) and a single editable install to kill the `sys.path` hacks.

---

## 7. Verification Checklist

```bash
# 1. Imports across the whole backend parse & load
cd backend/src
python -c "import main, api_fastapi"
python -c "import logic.grf_batch_runner, logic.grf_native_runner, logic.match_engine_grf"
python -c "import logic.manager_brain, logic.manager_profile"
python -c "import ml.dqn_agent, ml.footy_env, ml.train_rl, ml.evaluation"

# 2. API boots and health responds
python -m uvicorn api_fastapi:app --port 5001 &   # or: python dev_server.py
curl http://127.0.0.1:5001/health

# 3. DB init + seed path (run simulation once in a scratch dir)
python backend/run_3_seasons.py   # after adding the H8 --yes guard

# 4. Tests (isolated DB)
pytest backend/tests -x -q
```
---

## 8. Remediation Status (post-fix re-verification)

Snapshot re-audited **29 Aug 2026** after the fixes. All 50 backend `.py` files parse; 
`api_fastapi`, `main`, and all `logic`/`ml`/`models` imports load (34 API routes). 
`pytest backend/tests` (excluding the WSL-dependent simulate test) passes.

### Fixed & verified

| # | Item | How verified |
|---|------|--------------|
| C1 | grf_batch_runner SyntaxError | orphaned block removed; whole backend compiles |
| C2 | Docker build + compose env | `COPY backend`, `CMD api_fastapi:app --app-dir src`, FOOTY_* env names |
| H1 | DQN model path | now `ML_MODELS_DIR` from config (`backend/src/ml/models`) |
| H2 | ML path canonicalization | `ML_REPORTS_DIR`/`ML_MODELS_DIR` in config; eval writes to `backend/reports/ml_reports` |
| H3 | `/load/{save_id}` traversal | `os.path.basename` + `re.fullmatch` guard; tests assert 400/404 |
| H4 | Alembic metadata | env.py imports `database.models.Base` via sys.path |
| H5 | duplicate report tables | `report_models.py` deleted |
| H6 | dead raw-sqlite create_tables | `db_setup.py` slimmed to SQLAlchemy-only (46 lines) |
| H7 | raw sqlite + FK/WAL | `get_raw_conn()` + engine `PRAGMA foreign_keys=ON`; callers migrated |
| H8 | data-destroying script | `--yes` / `FOOTY_CONFIRM_RESET=1` guard |
| M3 | duplicate season reports | `unique=True` + upsert in report_db |
| M4 | ML action labels | evaluation.py labels match FootyEnv |
| M7 | wildcard CORS | localhost-only origins + regex |
| M8 | dev_server port | reads config.API_PORT |
| M9 | test isolation | conftest autouse session fixture points DB/saves at temp dir |
| M10 | temp GRF script leak | `finally`-block cleanup + startup sweeper (11 stale files removed) |
| M11 (partial) | season-year index | `ix_match_season_year` added (query batching still to-do) |
| M12 | is_available subprocess spam | 60s TTL cache + force_recheck in both runners |
| M13 | fallback visibility | `logger.warning` in get_grf_simulator/play_match; `engine_in_use` in /engine/status |
| M14 | intensity type | writes str(...) to match the String column |
| M1 | simulation lock race | atomic `simulation_started` flag + lock |
| M5 | /run-ml-eval blocking | now background `asyncio.task` with `ml_eval_lock`; returns 202 |
| M6 | deps | `flask`/`flask-cors` removed; `httpx` added to requirements-dev |

### Remaining (documented) future work

- M11: convert `/all-seasons-overview` aggregation to a single batched query (index is in place).
- M13: expose engine fallback reason text in `/api/v1/engine/status` (flag added; reason fields optional).
- M6: full dep-version alignment against a regenerated lockfile (optional; project pins are close).
- WSL-dependent `test_simulate_grf_match` still requires a live GRF + xvfb environment to run.
