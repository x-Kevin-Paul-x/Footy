# 03. Data Models and Schemas

Last verified: **6 September 2026**

## SQLite and SQLAlchemy

The default database is `backend/data/football_sim.db`, or `${FOOTY_DATA_DIR}/football_sim.db` when overridden. Connections enable foreign keys, WAL, and a 10-second busy timeout.

### Core records

| Model | Identity and important fields |
| --- | --- |
| `League` | `league_id`, `name`, `season_year`; many-to-many teams. |
| `Team` | `team_id`, unique `name`, budgets, optional manager relation. |
| `Player` | `player_id`, unique `name`, age, position, optional `team_id`, potential, wage, contract, squad role. |
| `Manager` | identity, formation, experience and performance counters. |
| `SimulationRun` | string `run_id`, season, lifecycle timestamps, status, render mode, match totals, cancellation flag, error and metadata. |
| `Match` | integer PK, nullable run FK, match number, season, team IDs, score/stat fields, trace path, video URL. |
| `MatchEvent` | event PK, match FK/index, minute, type, player, team, text details. |
| `MatchShots` | `(match_id, team)` composite PK with totals/on-target count. |
| `SeasonReport` / `TransferReport` | one report row per season year. |

`Match` has a uniqueness constraint on `(simulation_run_id, season_year, match_number)`. `home_team_id` and `away_team_id` are integer identifiers in the current ORM but are not declared foreign keys. `MatchEvent` also lacks dedicated step, xG, on-target, and structured-details columns.

Lifecycle status values used by the code include `running`, `completed`, `failed`, `cancelled`, and `interrupted`. Timestamps are ISO-formatted strings.

## Match trajectory

```python
@dataclass
class MatchTrajectory:
    match_id: str
    seed: int
    total_steps: int
    player_coords: np.ndarray       # (T, 22, 2), float32
    player_dirs: np.ndarray         # (T, 22, 2), float32
    ball_coords: np.ndarray         # (T, 3), float32
    ball_dirs: np.ndarray           # (T, 3), float32
    actions: np.ndarray             # (T, 20), uint8
    scores: np.ndarray              # (T, 2), uint8
    manifest: MatchManifest
    game_mode: np.ndarray | None    # (T,), int8
    ball_owned_team: np.ndarray | None
    ball_owned_player: np.ndarray | None
```

`MatchManifest` contains teams, final score, totals, events, lineups/formations, colors, engine fingerprint, optional video URL, and creation time. Array shapes, dtypes, categorical domains, and finite floats are validated. Hashes cover the physics arrays and full artifact metadata.

NPZ writing currently uses `np.savez_compressed` directly in the implementation visible during this review; callers should not assume crash-atomic publication unless the surrounding executor stages the target. Loading uses `allow_pickle=True` for legacy compatibility, so arbitrary uploads are not safe inputs.

## Full-state archive

`.grfstate` V2 stores a magic header, fixed metadata/index region, compressed chunks, per-chunk checksums, and a global hash. Chunk payloads use pickle. The reader also supports V1 and automatically treats unknown magic as a legacy pickle file. This is a trusted-local format pending P3.4.

## API schemas

`schemas.py` defines typed responses for teams, players, reports, saves, simulation status, match simulation/rendering, and simulation settings. `MatchSimulationRequest` validates match IDs, team-name length, formations, `max_steps` from 100 to 5000, and render mode (`2d`, `3d`, `auto`). `SimulationSettings` validates render mode, steps, and model filename shape.

Many read endpoints still return ad hoc dictionaries/`JSONResponse` without response models. Versioned API coverage is therefore broad but not complete.

## Backup and restore

`backup_database()` uses SQLite’s online backup API into a staging database, runs `PRAGMA integrity_check`, and atomically publishes the save. `restore_database()` validates the source, disposes pooled connections, uses the backup API into the live DB, checkpoints WAL, and disposes again.

## Migration state

The live database was verified at revision `879f4c01467a`, with `integrity_check=ok` and zero foreign-key violations. The chain is not a clean bootstrap: on an empty isolated database, `f1279028ebae` creates only report tables and `c7c6ac0ab9c1` then fails while altering missing `Match`.

Fresh setup currently relies on SQLAlchemy `create_all()` plus compatibility DDL in `create_tables()`. Do not run schema experiments against the live database. Repair and test empty and legacy migration paths in isolated copies before making Alembic the sole schema owner.
