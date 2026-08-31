import json
import logging
import os
import sys
import asyncio
import io
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, Response
from urllib.parse import unquote

# DB query functions (these currently use raw sqlite)
from database.session import get_db_session
from database.models import Match, Team, Player, Manager as DBManager
from database.team_db import get_all_teams
from database.player_db import get_all_players
from database.match_db import get_matches_for_season, get_match_details
from database.report_db import get_all_season_reports, get_season_report_by_year, get_all_transfer_reports, get_transfer_report_by_year
from config import (
    API_DEBUG,
    API_PORT,
    BASE_DIR,
    MATCH_REPORTS_DIR,
    ML_MODELS_DIR,
    ML_REPORTS_DIR,
    PROJECT_ROOT,
    RECORDINGS_DIR,
    REPORTS_DIR,
    SEASON_REPORTS_DIR,
    SIMULATION_SCRIPT,
    SIMULATION_TIMEOUT_SECONDS,
    TRANSFER_LOGS_DIR,
    ensure_report_directories,
)

# For running simulation in-process
import main as footy_main

logger = logging.getLogger("footy.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ensure_report_directories()

app = FastAPI(title="Footy API", description="FastAPI Backend for Footy Simulation")

# Middleware to safely handle client disconnects (browser refresh / cancelled streaming)
@app.middleware("http")
async def client_disconnect_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        logger.debug(f"Client disconnected gracefully during request to {request.url.path}")
        return JSONResponse(status_code=499, content={"detail": "Client closed connection"})
    except Exception as e:
        err_msg = str(e).lower()
        if "10054" in err_msg or "forcibly closed" in err_msg or "broken resource" in err_msg or "endofstream" in err_msg:
            logger.debug(f"Connection reset handled gracefully for {request.url.path}")
            return JSONResponse(status_code=499, content={"detail": "Client closed connection"})
        raise

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resilient Video Streaming endpoint with full Range support and disconnect safety
@app.get("/recordings/{filename:path}")
async def stream_recording(filename: str, request: Request):
    clean_name = os.path.basename(filename)
    file_path = RECORDINGS_DIR / clean_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        stat_result = file_path.stat()
        file_size = stat_result.st_size
    except OSError:
        raise HTTPException(status_code=404, detail="Could not read recording file")

    if file_size == 0:
        return Response(status_code=204)

    range_header = request.headers.get("range")
    content_type = "video/mp4" if clean_name.endswith(".mp4") else "application/octet-stream"

    if not range_header:
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache",
            }
        )

    try:
        range_str = range_header.replace("bytes=", "").strip()
        parts = range_str.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            return Response(
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{file_size}",
                    "Accept-Ranges": "bytes"
                }
            )
    except Exception:
        start = 0
        end = file_size - 1

    chunk_length = end - start + 1

    async def file_chunk_generator():
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_length
                while bytes_left > 0:
                    read_size = min(bytes_left, 1024 * 64)
                    data = f.read(read_size)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            logger.debug(f"Client disconnected while streaming video {clean_name}")
            return
        except Exception as exc:
            err_text = str(exc).lower()
            if "10054" in err_text or "forcibly closed" in err_text or "broken resource" in err_text:
                return
            logger.warning(f"Error during video streaming {clean_name}: {exc}")

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": content_type,
        "Cache-Control": "no-cache",
    }
    return StreamingResponse(
        file_chunk_generator(),
        status_code=206,
        headers=headers,
        media_type=content_type
    )

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
        except Exception as e:
            logger.debug(f"Failed to accept websocket: {e}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

    async def broadcast_event(self, event: str, message: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        payload = json.dumps({"event": event, "message": message, "data": data})
        await self.broadcast(payload)

manager = ConnectionManager()

def _load_json_file(file_path: Path):
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def build_simulation_env():
    env = os.environ.copy()
    pythonpath_entries = [str(BASE_DIR)]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return env

from schemas import (
    TeamRead,
    PlayerRead,
    SeasonReportSummary,
    TransferReportSummary,
    SimulationStatusResponse,
    SaveStateItem,
    SaveStateResponse,
    WebSocketEventFrame,
    MatchSimulationRequest,
    MatchSimulationResponse
)
import shutil
from database.session import DB_FILE

SAVES_DIR = Path(DB_FILE).parent / "saves"
SAVES_DIR.mkdir(parents=True, exist_ok=True)

simulation_lock = asyncio.Lock()
simulation_started = False

def _set_simulation_running(value: bool):
    global simulation_started
    simulation_started = value

async def run_simulation_task():
    """Runs the simulation as a background task asynchronously with lock protection."""
    global simulation_started
    if simulation_lock.locked() or simulation_started:
        logger.warning("Simulation task requested while another simulation is in progress.")
        await manager.broadcast_event("WARNING", message="Simulation already running.")
        return

    simulation_started = True
    try:
        async with simulation_lock:
            logger.info("Starting background simulation task")
            ensure_report_directories()

            await manager.broadcast_event("SIMULATION_START", message="Simulation starting...")

            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, footy_main.main)
                await manager.broadcast_event("SIMULATION_COMPLETE", message="Simulation completed successfully!")
            except Exception as e:
                logger.error(f"Simulation failed with error {e}")
                await manager.broadcast_event("SIMULATION_ERROR", message=f"Simulation failed: {e}")
    finally:
        _set_simulation_running(False)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, ConnectionResetError, BrokenPipeError, asyncio.CancelledError, Exception):
        pass
    finally:
        manager.disconnect(websocket)

@app.post("/run-simulation", response_model=SimulationStatusResponse)
async def trigger_simulation(background_tasks: BackgroundTasks):
    if simulation_lock.locked() or simulation_started:
        return SimulationStatusResponse(status="busy", message="Simulation is already running")
    background_tasks.add_task(run_simulation_task)
    return SimulationStatusResponse(status="success", message="Simulation started in the background")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Footy API"}

@app.get("/saves", response_model=List[SaveStateItem])
async def list_saves():
    try:
        saves = []
        if SAVES_DIR.exists():
            for f in os.listdir(SAVES_DIR):
                if f.endswith(".db"):
                    fpath = SAVES_DIR / f
                    stat = fpath.stat()
                    save_id = f.replace(".db", "")
                    saves.append(
                        SaveStateItem(
                            save_id=save_id,
                            filename=f,
                            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            size_bytes=stat.st_size
                        )
                    )
        saves.sort(key=lambda s: s.created_at, reverse=True)
        return saves
    except Exception as e:
        logger.error(f"Error listing save states: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list saves: {e}")

@app.post("/saves", response_model=SaveStateResponse)
async def create_save():
    try:
        from database.session import init_db
        if not os.path.exists(DB_FILE):
            init_db()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_id = f"save_{timestamp}"
        target_path = SAVES_DIR / f"{save_id}.db"
        shutil.copy2(DB_FILE, target_path)
        return SaveStateResponse(status="success", message="Save state created successfully", save_id=save_id)
    except Exception as e:
        logger.error(f"Error creating save state: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create save state: {e}")

@app.post("/load/{save_id}", response_model=SaveStateResponse)
async def load_save(save_id: str):
    try:
        clean_save_id = os.path.basename(save_id.strip())
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", clean_save_id):
            raise HTTPException(status_code=400, detail="Invalid save_id.")
        source_path = SAVES_DIR / f"{clean_save_id}.db"
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Save state file not found.")
        if simulation_lock.locked() or simulation_started:
            raise HTTPException(status_code=409, detail="Cannot load save state while simulation is running.")
        shutil.copy2(source_path, DB_FILE)
        return SaveStateResponse(status="success", message=f"Loaded save state '{clean_save_id}' successfully.", save_id=clean_save_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading save state: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load save state: {e}")

@app.get("/teams", response_model=List[TeamRead])
async def get_teams():
    try:
        teams = get_all_teams()
        return [
            TeamRead(
                id=t[0],
                name=t[1],
                budget=t[2],
                weekly_budget=t[3],
                transfer_budget=t[4],
                wage_budget=t[5]
            )
            for t in teams
        ]
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/players", response_model=List[PlayerRead])
async def get_players():
    try:
        players = get_all_players()
        return [
            PlayerRead(
                id=p["player_id"],
                name=p["name"],
                age=p["age"],
                position=p["position"],
                team_id=p["team_id"],
                potential=p["potential"],
                wage=p["wage"],
                contract_length=p["contract_length"],
                squad_role=p["squad_role"]
            )
            for p in players
        ]
    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/season-reports", response_model=List[SeasonReportSummary])
async def get_season_reports():
    try:
        reports = get_all_season_reports()
        return [
            SeasonReportSummary(
                id=r[0],
                season=r[1],
                champion=r[2],
                created_at=r[3]
            )
            for r in reports
        ]
    except Exception as e:
        logger.error(f"Error fetching season reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/season-reports/{season_year}")
async def get_season_report_detail(season_year: int):
    try:
        report_data = get_season_report_by_year(season_year)
        if not report_data:
            raise HTTPException(status_code=404, detail="Report not found for given year.")
        return report_data
    except Exception as e:
        logger.error(f"Error fetching season report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transfer-reports", response_model=List[TransferReportSummary])
async def get_transfer_reports():
    try:
        reports = get_all_transfer_reports()
        return [
            TransferReportSummary(
                id=r[0],
                season=r[1],
                created_at=r[2]
            )
            for r in reports
        ]
    except Exception as e:
        logger.error(f"Error fetching transfer reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transfer-reports/{season_year}")
async def get_transfer_report_detail(season_year: int):
    try:
        report_data = get_transfer_report_by_year(season_year)
        if not report_data:
            raise HTTPException(status_code=404, detail="Transfer report not found for given year.")
        return report_data
    except Exception as e:
        logger.error(f"Error fetching transfer report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/get-seasons')
async def get_seasons():
    try:
        seasons_set = set()
        if os.path.exists(SEASON_REPORTS_DIR):
            report_files = [f for f in os.listdir(SEASON_REPORTS_DIR) if f.startswith("season_report_") and f.endswith(".json")]
            for report_file in report_files:
                try:
                    year = report_file.replace("season_report_", "").replace(".json", "")
                    seasons_set.add(int(year))
                except ValueError:
                    pass

        try:
            with get_db_session() as db:
                db_seasons = db.query(Match.season_year).distinct().all()
                for row in db_seasons:
                    if row[0]:
                        seasons_set.add(int(row[0]))
        except Exception:
            pass

        seasons = sorted(list(seasons_set), reverse=True)
        return JSONResponse(status_code=200, content={"seasons": seasons})
    except Exception as e:
        logger.exception("Error getting seasons")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


def build_live_season_report_from_db(year: int) -> dict:
    try:
        with get_db_session() as db:
            teams = db.query(Team).all()
            if not teams:
                return {}
            team_map = {t.team_id: t.name for t in teams}

            matches = db.query(Match).filter(Match.season_year == year).all()
            table_dict = {}
            for t in teams:
                table_dict[t.name] = {
                    "played": 0, "won": 0, "drawn": 0, "lost": 0,
                    "gf": 0, "ga": 0, "gd": 0, "points": 0, "recent_form": []
                }

            for m in matches:
                h_name = team_map.get(m.home_team_id, f"Team {m.home_team_id}")
                a_name = team_map.get(m.away_team_id, f"Team {m.away_team_id}")

                if h_name not in table_dict: table_dict[h_name] = {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0, "recent_form": []}
                if a_name not in table_dict: table_dict[a_name] = {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0, "recent_form": []}

                table_dict[h_name]["played"] += 1
                table_dict[a_name]["played"] += 1
                table_dict[h_name]["gf"] += m.home_goals
                table_dict[h_name]["ga"] += m.away_goals
                table_dict[a_name]["gf"] += m.away_goals
                table_dict[a_name]["ga"] += m.home_goals
                table_dict[h_name]["gd"] += (m.home_goals - m.away_goals)
                table_dict[a_name]["gd"] += (m.away_goals - m.home_goals)

                if m.home_goals > m.away_goals:
                    table_dict[h_name]["won"] += 1
                    table_dict[h_name]["points"] += 3
                    table_dict[h_name]["recent_form"].append("W")
                    table_dict[a_name]["lost"] += 1
                    table_dict[a_name]["recent_form"].append("L")
                elif m.home_goals < m.away_goals:
                    table_dict[a_name]["won"] += 1
                    table_dict[a_name]["points"] += 3
                    table_dict[a_name]["recent_form"].append("W")
                    table_dict[h_name]["lost"] += 1
                    table_dict[h_name]["recent_form"].append("L")
                else:
                    table_dict[h_name]["drawn"] += 1
                    table_dict[h_name]["points"] += 1
                    table_dict[h_name]["recent_form"].append("D")
                    table_dict[a_name]["drawn"] += 1
                    table_dict[a_name]["points"] += 1
                    table_dict[a_name]["recent_form"].append("D")

            sorted_table = sorted(
                table_dict.items(),
                key=lambda item: (item[1]["points"], item[1]["gd"], item[1]["gf"]),
                reverse=True
            )

            # Bulk load and group players by team_id for fast serializing
            all_db_players = db.query(Player).all()
            players_by_team = {}
            for p in all_db_players:
                if p.team_id not in players_by_team:
                    players_by_team[p.team_id] = []
                players_by_team[p.team_id].append({
                    "name": p.name,
                    "age": p.age,
                    "position": p.position,
                    "team": team_map.get(p.team_id, "Free Agent"),
                    "potential": p.potential,
                    "wage": p.wage,
                    "contract_length": p.contract_length,
                    "squad_role": p.squad_role,
                    "market_value": p.potential * 150000,
                    "overall_rating": round(p.potential * 0.8, 1),
                    "form": [7, 7, 8, 7, 8],
                    "attributes": {},
                    "stats": {"goals": 0, "assists": 0, "appearances": 0, "clean_sheets": 0, "fitness": 100},
                })

            all_teams_details = []
            for t in teams:
                team_players = players_by_team.get(t.team_id, [])
                all_teams_details.append({
                    "id": t.team_id,
                    "name": t.name,
                    "budget": t.budget,
                    "manager_name": t.manager.name if t.manager else "N/A",
                    "manager_formation": t.manager.formation if t.manager else "4-3-3",
                    "players_count": len(team_players),
                    "players": team_players,
                })

            total_m = len(matches)
            total_g = sum(m.home_goals + m.away_goals for m in matches)

            return {
                "season_year": year,
                "champions": sorted_table[0][0] if sorted_table else "TBD",
                "champions_manager": {},
                "table": sorted_table,
                "transfers": {"total_transfers": 0, "biggest_spenders": [], "most_active": [], "all_completed_transfers": []},
                "best_players": [],
                "season_stats": {
                    "total_matches": total_m,
                    "total_goals": total_g,
                    "average_goals_per_match": round(total_g / max(1, total_m), 2),
                    "best_attack": [sorted_table[0][0], {"gf": sorted_table[0][1]["gf"]}] if sorted_table else ["N/A", {"gf": 0}],
                    "best_defense": [sorted_table[0][0], {"ga": sorted_table[0][1]["ga"]}] if sorted_table else ["N/A", {"ga": 0}],
                },
                "all_teams_details": all_teams_details,
                "financial_summary": [],
                "transfer_summary": {},
            }
    except Exception as e:
        logger.error(f"Error building live season report from DB: {e}")
        return {}


@app.get("/get-season-report/{year:int}")
async def get_season_report(year: int):
    """
    Return the season report JSON but augment it with DB-backed transfer history if available.
    This keeps the season report authoritative while ensuring completed transfers persistently
    stored in the DB are surfaced to the frontend.
    """
    try:
        # Dynamically build live season report from the database in real-time
        data = build_live_season_report_from_db(year)
        if not data or not data.get("table"):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Season report for {year} not found."})

        conn = None
        try:
            import sqlite3
            from database.db_setup import DB_FILE

            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            cur.execute(
                "SELECT transfer_id, player_id, from_team_id, to_team_id, amount, day, season_year FROM TransferHistory WHERE season_year = ? ORDER BY transfer_id ASC",
                (year,),
            )
            rows = cur.fetchall()

            db_transfers = []
            for tr in rows:
                transfer_id, player_id, from_team_id, to_team_id, amount, day, season_year_row = tr

                # Resolve human-readable names where possible
                player_name = None
                from_team_name = None
                to_team_name = None

                try:
                    cur.execute("SELECT name FROM Player WHERE player_id = ?", (player_id,))
                    pr = cur.fetchone()
                    if pr:
                        player_name = pr[0]
                except Exception:
                    player_name = None

                try:
                    cur.execute("SELECT name FROM Team WHERE team_id = ?", (from_team_id,))
                    fr = cur.fetchone()
                    if fr:
                        from_team_name = fr[0]
                except Exception:
                    from_team_name = None

                try:
                    cur.execute("SELECT name FROM Team WHERE team_id = ?", (to_team_id,))
                    trn = cur.fetchone()
                    if trn:
                        to_team_name = trn[0]
                except Exception:
                    to_team_name = None

                db_transfers.append({
                    "transfer_id": int(transfer_id),
                    "player_id": int(player_id) if player_id is not None else None,
                    "player": player_name or f"player[{player_id}]",
                    "from_team_id": int(from_team_id) if from_team_id is not None else None,
                    "from_team": from_team_name or f"team[{from_team_id}]",
                    "to_team_id": int(to_team_id) if to_team_id is not None else None,
                    "to_team": to_team_name or f"team[{to_team_id}]",
                    "amount": float(amount),
                    "day": int(day),
                    "season_year": int(season_year_row),
                })

            # Attach DB transfers into the report under a common key expected by frontend
            if "transfers" not in data or not isinstance(data.get("transfers"), dict):
                data["transfers"] = {}

            # Prefer existing 'all_completed_transfers' if present, but override with DB-backed list when available
            if db_transfers:
                data["transfers"]["all_completed_transfers"] = db_transfers

            # Add a small summary from DB counts if useful
            try:
                cur.execute("SELECT COUNT(*) FROM TransferHistory WHERE season_year = ?", (year,))
                count = cur.fetchone()[0]
                data["transfers"]["db_transfers_count"] = int(count)
            except Exception:
                data["transfers"]["db_transfers_count"] = None

        except Exception as e:
            # Non-fatal: log and return original report if DB read fails
            logger.warning("Failed to read TransferHistory from DB: %s", e)
        finally:
            if conn:
                conn.close()

        return JSONResponse(status_code=200, content=data)
    except Exception as e:
        logger.exception("Error getting season report for %d", year)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


def _get_ml_report_paths() -> list[Path]:
    paths = []
    seen = set()
    search_dirs = [ML_REPORTS_DIR]
    if ML_REPORTS_DIR.exists():
        direct_files = list(ML_REPORTS_DIR.glob("*.json"))
        if not direct_files and REPORTS_DIR.exists():
            search_dirs.append(REPORTS_DIR / "ml_reports")
    elif REPORTS_DIR.exists():
        search_dirs.append(REPORTS_DIR / "ml_reports")

    for directory in search_dirs:
        if directory.exists():
            for p in sorted(list(directory.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True):
                if p.name not in seen:
                    seen.add(p.name)
                    paths.append(p)
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)


def _build_ml_report_summary(report_path: Path, payload: dict) -> dict:
    summary = payload.get("summary") or {}
    policies = payload.get("policies") or {}
    return {
        "file_name": report_path.name,
        "report_type": report_path.stem.split("_", 1)[0],
        "generated_at": payload.get("generated_at") or payload.get("created_at") or str(report_path.stat().st_mtime),
        "primary_policy": summary.get("primary_policy"),
        "best_policy_by_reward": summary.get("best_policy_by_reward"),
        "best_policy_by_points": summary.get("best_policy_by_points"),
        "best_policy_by_position": summary.get("best_policy_by_position"),
        "policy_count": len(policies),
        "config": payload.get("config") or {},
    }


def _resolve_ml_report_path(report_name: str) -> Path | None:
    safe_name = os.path.basename(report_name)
    target_path = ML_REPORTS_DIR / safe_name
    if target_path.exists():
        return target_path
    fallback_path = REPORTS_DIR / "ml_reports" / safe_name
    if fallback_path.exists():
        return fallback_path
    return None



@app.get("/ml-reports")
async def get_ml_reports():
    try:
        reports = []
        for report_path in _get_ml_report_paths():
            try:
                payload = _load_json_file(report_path)
                reports.append(_build_ml_report_summary(report_path, payload))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable ML report %s: %s", report_path, exc)
        return JSONResponse(status_code=200, content={"reports": reports})
    except Exception as e:
        logger.exception("Error getting ML reports")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/ml-reports/{report_name}")
async def get_ml_report(report_name):
    try:
        report_path = _resolve_ml_report_path(report_name)
        if report_path is None or not report_path.exists():
            return JSONResponse(status_code=404, content={"status": "error", "message": "ML report not found."})

        payload = _load_json_file(report_path)
        payload["report_name"] = report_path.name
        payload["report_type"] = report_path.stem.split("_", 1)[0]
        return JSONResponse(status_code=200, content=payload)
    except json.JSONDecodeError:
        logger.exception("ML report %s is not valid JSON", report_name)
        return JSONResponse(status_code=500, content={"status": "error", "message": "ML report is invalid JSON."})
    except Exception as e:
        logger.exception("Error getting ML report %s", report_name)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/ml-models")
async def get_ml_models():
    """List all available ML model checkpoints in the system."""
    try:
        models = []
        search_dirs = [
            PROJECT_ROOT / "ml" / "models",
            BASE_DIR / "ml" / "models",
            BASE_DIR / "models",
        ]
        seen = set()
        for d in search_dirs:
            if d.exists():
                for f in d.glob("*.pt"):
                    if f.name not in seen:
                        seen.add(f.name)
                        stat = f.stat()
                        models.append({
                            "name": f.name,
                            "path": str(f),
                            "size_bytes": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        })
        return JSONResponse(status_code=200, content={"models": models})
    except Exception as e:
        logger.exception("Error getting ML models")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


ml_eval_lock = asyncio.Lock()
ml_eval_started = False


async def run_ml_eval_task(episodes: int, teams: int, season_length: int, fast_mode: bool, models: list):
    """Run the DQN benchmark evaluation in the background and broadcast the result report."""
    global ml_eval_started
    try:
        async with ml_eval_lock:
            _ = int(episodes), int(teams), int(season_length), bool(fast_mode)
            if not models:
                models = [str(ML_MODELS_DIR / "dqn_best.pt")]

            from ml.train_rl import run_episode
            from ml.footy_env import FootyEnv
            from ml.dqn_agent import DQNAgent
            from ml.evaluation import (
                build_evaluation_report,
                save_evaluation_report,
                summarize_episode_results,
            )
            import time

            env = FootyEnv(num_teams=teams, season_length=season_length, fast_mode=fast_mode)
            start_time = time.time()
            summaries = {}
            policy_models = {}

            if len(models) == 1:
                model_path = models[0]
                agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim)
                if Path(model_path).exists():
                    agent.load(model_path)
                policies_to_test = ["trained", "random", "do_nothing", "youth_focus"]
                for pol in policies_to_test:
                    episodes_data = [
                        run_episode(env, agent=agent, policy=pol, training=False, epsilon=0.0)
                        for _ in range(episodes)
                    ]
                    summaries[pol] = summarize_episode_results(pol, episodes_data)
                policy_models["trained"] = model_path
                primary_name = "trained"
            else:
                for m_path in models:
                    p_name = f"model_{Path(m_path).stem}"
                    agent = DQNAgent(obs_dim=env.obs_dim, action_dim=env.action_dim)
                    if Path(m_path).exists():
                        agent.load(m_path)
                    policy_models[p_name] = m_path
                    episodes_data = [
                        run_episode(env, agent=agent, policy="trained", training=False, epsilon=0.0)
                        for _ in range(episodes)
                    ]
                    summaries[p_name] = summarize_episode_results(p_name, episodes_data)
                base_data = [run_episode(env, policy="random") for _ in range(episodes)]
                summaries["baseline_random"] = summarize_episode_results("baseline_random", base_data)
                primary_name = list(summaries.keys())[0]

            runtime = {
                "elapsed_seconds": round(time.time() - start_time, 2),
                "episodes_per_policy": episodes,
            }
            cfg = {
                "num_teams": teams,
                "season_length": season_length,
                "fast_mode": fast_mode,
            }
            report = build_evaluation_report(
                model_path=";".join(models),
                config=cfg,
                runtime=runtime,
                policy_summaries=summaries,
                primary_policy_name=primary_name,
                policy_models=policy_models,
            )
            out_dir = str(REPORTS_DIR / "ml_reports")
            report_file = save_evaluation_report(report, out_dir)
            report["report_name"] = Path(report_file).name
            await manager.broadcast_event("ML_EVAL_COMPLETE", message="ML evaluation completed", data=report)
    except Exception as e:
        logger.exception("Error running ML evaluation")
        await manager.broadcast_event("ML_EVAL_ERROR", message=f"ML evaluation failed: {e}")
    finally:
        ml_eval_started = False


@app.post("/run-ml-eval")
async def trigger_ml_evaluation(request: Request):
    """Trigger a benchmark evaluation in the background (non-blocking)."""
    global ml_eval_started
    if ml_eval_lock.locked() or ml_eval_started:
        return JSONResponse(status_code=409, content={"status": "busy", "message": "ML evaluation already running."})

    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        models = body.get("models", [str(ML_MODELS_DIR / "dqn_best.pt")])
        episodes = int(body.get("episodes", 10))
        teams = int(body.get("teams", 6))
        season_length = int(body.get("season_length", 20))
        fast_mode = bool(body.get("fast_mode", True))

        ml_eval_started = True
        asyncio.create_task(run_ml_eval_task(episodes, teams, season_length, fast_mode, models))
        return JSONResponse(status_code=202, content={"status": "accepted", "message": "ML evaluation started in the background."})
    except Exception as e:
        ml_eval_started = False
        logger.exception("Error parsing ML evaluation request")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/match/{match_id}")
async def get_match(match_id):
    """API endpoint to get detailed information for a single match."""
    try:
        match_details = get_match_details(match_id)
        if not match_details:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Match with ID {match_id} not found."})
        return JSONResponse(status_code=200, content=match_details)
    except Exception as e:
        logger.exception("Error getting match details for match %s", match_id)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/v1/engine/status")
async def get_engine_status():
    """Returns the current status of the match engine and TiKick multi-agent system."""
    try:
        from models.match import get_grf_simulator
        from config import ENGINE_MODE, BALLER_DIR, TIKICK_CHECKPOINT_PATH
        sim = get_grf_simulator()
        is_grf_ready = sim is not None and sim.is_available()
        engine_in_use = "GRF+TiKick" if is_grf_ready else "heuristic"
        
        return JSONResponse(status_code=200, content={
            "engine_mode": ENGINE_MODE,
            "engine_in_use": engine_in_use,
            "grf_available": is_grf_ready,
            "device": getattr(sim, "device", "cpu") if sim else "none",
            "checkpoint_found": os.path.exists(str(TIKICK_CHECKPOINT_PATH)),
            "baller_dir": str(BALLER_DIR),
            "recordings_dir": str(RECORDINGS_DIR)
        })
    except Exception as e:
        logger.exception("Error getting engine status")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/v1/match/{match_id}/video")
async def get_match_video(match_id: str):
    """Get video replay metadata for a specific match."""
    try:
        clean_id = str(match_id)
        v1 = RECORDINGS_DIR / f"{clean_id}.mp4"
        v2 = RECORDINGS_DIR / f"match_{clean_id}.mp4"
        v_target = v1 if v1.exists() else (v2 if v2.exists() else None)
        if v_target:
            return JSONResponse(status_code=200, content={
                "match_id": match_id,
                "video_url": f"/recordings/{v_target.name}",
                "size_bytes": v_target.stat().st_size,
                "available": True
            })
        return JSONResponse(status_code=200, content={
            "match_id": match_id,
            "video_url": None,
            "available": False,
            "message": "No broadcast replay video generated for this match."
        })
    except Exception as e:
        logger.exception("Error checking match video for %s", match_id)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/v1/match/{match_id}/render-status")
async def get_match_render_status(match_id: str):
    """Get live 3D replay rendering progress and stage details."""
    try:
        clean_id = str(match_id)
        v1 = RECORDINGS_DIR / f"{clean_id}.mp4"
        v2 = RECORDINGS_DIR / f"match_{clean_id}.mp4"
        v_target = v1 if v1.exists() else (v2 if v2.exists() else None)

        prog_file = RECORDINGS_DIR / f"progress_{clean_id}.json"
        if prog_file.exists():
            # Robust read with micro-retry in case WSL is writing atomically
            for _ in range(3):
                try:
                    with open(prog_file, "r", encoding="utf-8") as pf:
                        data = json.load(pf)
                        if v_target and data.get("completed"):
                            data["video_url"] = f"/recordings/{v_target.name}"
                            try:
                                prog_file.unlink()
                            except Exception:
                                pass
                        return JSONResponse(status_code=200, content=data)
                except Exception:
                    await asyncio.sleep(0.05)

            # If prog_file exists but is temporarily locked, report in-progress rather than resetting to idle
            return JSONResponse(status_code=200, content={
                "status": "rendering",
                "progress": 50,
                "stage": "Rendering 3D Match Broadcast...",
                "video_url": f"/recordings/{v_target.name}" if v_target else None,
                "completed": False
            })

        if v_target:
            if prog_file.exists():
                try:
                    prog_file.unlink()
                except Exception:
                    pass
            return JSONResponse(status_code=200, content={
                "status": "completed",
                "progress": 100,
                "match_minute": 90,
                "stage": "3D Replay Available",
                "video_url": f"/recordings/{v_target.name}",
                "completed": True
            })

        return JSONResponse(status_code=200, content={
            "status": "idle",
            "progress": 0,
            "match_minute": 0,
            "stage": "Ready to Render",
            "video_url": None,
            "completed": False
        })
    except Exception as e:
        logger.exception("Error checking render status for %s", match_id)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/api/v1/match/simulate-grf", response_model=MatchSimulationResponse)
async def simulate_grf_match(req: MatchSimulationRequest):
    """
    Execute on-demand match simulation between two teams with 720p HD broadcast video generation.
    On first call for a match_id: runs GRF neural policy, saves episode dump as trace.
    On repeat calls: loads trace and replays exact same actions — score and goals are identical.
    """
    try:
        from models.team import Team
        from models.player import FootballPlayer
        from models.match import Match, get_grf_simulator
        from models.manager import Manager
        from database.match_db import get_match_details
        from logic.grf_native_runner import GRFNativeRunner, team_color_from_name
        from datetime import datetime

        match_id_str = str(req.match_id) if req.match_id else f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Fetch existing match context (team names, rosters, colours, trace)
        existing_match = None
        seed_val = None
        trace_file = None
        if req.match_id:
            try:
                existing_match = get_match_details(int(req.match_id) if str(req.match_id).isdigit() else req.match_id)
                if existing_match:
                    trace_file = existing_match.get("trace_file")
                    sy = existing_match.get("season_year")
                    hid = existing_match.get("home_team_id")
                    aid = existing_match.get("away_team_id")
                    if sy and hid and aid:
                        import hashlib
                        seed_val = int(hashlib.md5(f"match_{sy}_{hid}_{aid}".encode()).hexdigest()[:8], 16) % 100000
            except Exception:
                pass

        h_team = existing_match.get("home_team_name", req.home_team_name) if existing_match else req.home_team_name
        a_team = existing_match.get("away_team_name", req.away_team_name) if existing_match else req.away_team_name

        # Pull player names from stored lineup (home_lineup / away_lineup from get_match_details)
        h_players = [p.get("name", "") for p in (existing_match or {}).get("home_lineup", [])]
        a_players = [p.get("name", "") for p in (existing_match or {}).get("away_lineup", [])]

        # Kit colours — deterministic from team name (no DB migration needed)
        h_color = team_color_from_name(h_team)
        a_color = team_color_from_name(a_team)

        steps = min(max(req.max_steps, 100), 5000) if req.max_steps else 1200
        should_render_video = bool(req.generate_video)

        # Execute authentic GRF simulation (Phase A - pure physics, fast)
        native_runner = GRFNativeRunner()
        grf_out = await asyncio.to_thread(
            native_runner.simulate,
            home_team=h_team,
            away_team=a_team,
            max_steps=steps,
            home_players=h_players if len(h_players) >= 11 else None,
            away_players=a_players if len(a_players) >= 11 else None,
            home_formation=req.home_formation or "4-3-3",
            away_formation=req.away_formation or "4-2-3-1",
            home_color=h_color,
            away_color=a_color,
            match_id=match_id_str,
            seed_val=seed_val,
            render_video=False,
        )

        h_score    = int(grf_out.get("score", [0, 0])[0])
        a_score    = int(grf_out.get("score", [0, 0])[1])
        real_events= grf_out.get("events", [])
        real_poss  = grf_out.get("possession", [50.0, 50.0])
        real_shots = grf_out.get("shots", [h_score, a_score])
        real_xg    = grf_out.get("xg", [round(h_score * 0.45, 2), round(a_score * 0.45, 2)])
        video_url  = None

        # Phase B - Standalone Video Rendering if requested
        if should_render_video:
            trace_dump = str(RECORDINGS_DIR / f"trace_{match_id_str}.dump")
            prog_file = RECORDINGS_DIR / f"progress_{match_id_str}.json"
            try:
                with open(prog_file, "w") as pf:
                    json.dump({
                        "status": "rendering",
                        "progress": 5,
                        "step": 0,
                        "total_steps": steps,
                        "match_minute": 0,
                        "stage": "Rendering 3D Match Broadcast...",
                        "score": [h_score, a_score],
                        "completed": False
                    }, pf)
            except Exception:
                pass

            # Start video render as background task so HTTP request returns quickly
            async def _bg_render():
                try:
                    await asyncio.to_thread(
                        native_runner.render_replay,
                        match_id=match_id_str,
                        home_team=h_team,
                        away_team=a_team,
                        dump_file=trace_dump,
                        home_players=h_players if len(h_players) >= 11 else None,
                        away_players=a_players if len(a_players) >= 11 else None,
                        home_formation=req.home_formation or "4-3-3",
                        away_formation=req.away_formation or "4-2-3-1",
                        home_color=h_color,
                        away_color=a_color,
                    )
                except Exception as ex:
                    logger.error("Background render error for %s: %s", match_id_str, ex)
                    try:
                        with open(prog_file, "w") as pf:
                            json.dump({"status": "error", "message": str(ex), "completed": True}, pf)
                    except Exception:
                        pass

            asyncio.create_task(_bg_render())
            video_url = f"/recordings/match_{match_id_str}.mp4"

        return MatchSimulationResponse(
            match_id=match_id_str,
            home_team=h_team,
            away_team=a_team,
            home_score=h_score,
            away_score=a_score,
            possession={"home": float(real_poss[0]), "away": float(real_poss[1])},
            shots={"home": int(real_shots[0]), "away": int(real_shots[1])},
            xg={"home": float(real_xg[0]), "away": float(real_xg[1])},
            timeline=real_events,
            video_url=video_url,
        )
    except Exception as e:
        logger.exception("Error simulating GRF match")
        raise HTTPException(status_code=500, detail=f"Match simulation failed: {e}")

@app.get("/team-history/{team_name}")
async def get_team_history(team_name):
    """Get historical league positions and stats for a team across all seasons."""
    try:
        history = []
        if not os.path.exists(SEASON_REPORTS_DIR):
            return JSONResponse(status_code=200, content={"history": [], "team_name": team_name})

        report_files = [f for f in os.listdir(SEASON_REPORTS_DIR) if f.startswith("season_report_") and f.endswith(".json")]
        
        for report_file in report_files:
            try:
                year = int(report_file.replace("season_report_", "").replace(".json", ""))
                report_path = os.path.join(SEASON_REPORTS_DIR, report_file)
                with open(report_path, 'r') as f:
                    data = json.load(f)
                
                # Find team in table
                table = data.get("table", [])
                for pos, (name, stats) in enumerate(table, 1):
                    if name == team_name:
                        history.append({
                            "season": year,
                            "position": pos,
                            "points": stats.get("points", 0),
                            "won": stats.get("won", 0),
                            "drawn": stats.get("drawn", 0),
                            "lost": stats.get("lost", 0),
                            "gf": stats.get("gf", 0),
                            "ga": stats.get("ga", 0),
                            "gd": stats.get("gd", 0)
                        })
                        break
            except Exception as e:
                logger.warning("Error processing %s: %s", report_file, e)
                continue
        
        # Sort by season
        history.sort(key=lambda x: x["season"])
        return JSONResponse(status_code=200, content={"history": history, "team_name": team_name})
    except Exception as e:
        logger.exception("Error getting team history for %s", team_name)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/financial-summary")
async def get_financial_summary():
    """Get league-wide financial summary directly from SQLite database."""
    try:
        with get_db_session() as db:
            teams = db.query(Team).all()
            if not teams:
                return JSONResponse(status_code=200, content={
                    "season": 2026,
                    "league_totals": {"total_budget": 0, "average_budget": 0, "total_revenue": 0, "total_expenses": 0, "net_position": 0},
                    "health_distribution": {},
                    "top_5_richest": [],
                    "bottom_5": []
                })

            financial_summary = []
            for t in teams:
                financial_summary.append({
                    "name": t.name,
                    "budget": t.budget,
                    "annual_revenue": getattr(t, "annual_revenue", 0.0),
                    "annual_expenses": getattr(t, "annual_expenses", 0.0),
                    "financial_health": getattr(t, "financial_health", "Good"),
                })

            total_budget = sum(f.get("budget", 0) for f in financial_summary)
            total_revenue = sum(f.get("annual_revenue", 0) for f in financial_summary)
            total_expenses = sum(f.get("annual_expenses", 0) for f in financial_summary)

            health_counts = {}
            for f in financial_summary:
                health = f.get("financial_health", "Good")
                health_counts[health] = health_counts.get(health, 0) + 1

            sorted_by_budget = sorted(financial_summary, key=lambda x: x.get("budget", 0), reverse=True)

            return JSONResponse(status_code=200, content={
                "season": 2026,
                "league_totals": {
                    "total_budget": total_budget,
                    "average_budget": total_budget / len(financial_summary) if financial_summary else 0,
                    "total_revenue": total_revenue,
                    "total_expenses": total_expenses,
                    "net_position": total_revenue - total_expenses
                },
                "health_distribution": health_counts,
                "top_5_richest": sorted_by_budget[:5],
                "bottom_5": sorted_by_budget[-5:] if len(sorted_by_budget) >= 5 else sorted_by_budget
            })
    except Exception as e:
        logger.exception("Error getting financial summary")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/matches/{season_year}")
async def get_matches_by_season(season_year: int):
    """API endpoint to get all matches for a given season from DB."""
    try:
        from database.match_db import get_matches_for_season
        matches = get_matches_for_season(season_year)
        if not matches:
            return JSONResponse(status_code=200, content={"matches": [], "message": f"No matches found for season {season_year}."})
        return JSONResponse(status_code=200, content={"matches": matches})
    except Exception as e:
        logger.exception("Error getting matches for season %s", season_year)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/youth-prospects")
async def get_youth_prospects():
    """Get top youth prospects directly from SQLite Player table."""
    try:
        with get_db_session() as db:
            teams = db.query(Team).all()
            team_map = {t.team_id: t.name for t in teams}

            players = db.query(Player).filter(Player.age <= 21).all()
            all_youth = []
            for p in players:
                all_youth.append({
                    "name": p.name,
                    "team": team_map.get(p.team_id, "Free Agent"),
                    "age": p.age,
                    "position": p.position,
                    "potential": p.potential,
                    "current_rating": p.potential * 0.8
                })

            all_youth.sort(key=lambda x: (x["potential"], x["current_rating"]), reverse=True)
            return JSONResponse(status_code=200, content={
                "prospects": all_youth[:15],
                "total_youth": len(all_youth)
            })
    except Exception as e:
        logger.exception("Error getting youth prospects")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/transfer-activity")
async def get_transfer_activity():
    """Get recent transfer activity directly from TransferHistory table."""
    try:
        with get_db_session() as db:
            transfers = db.query(TransferHistory).order_by(TransferHistory.transfer_id.desc()).limit(20).all()
            teams = {t.team_id: t.name for t in db.query(Team).all()}
            players = {p.player_id: p.name for p in db.query(Player).all()}

            tr_list = []
            for t in transfers:
                tr_list.append({
                    "player": players.get(t.player_id, f"Player {t.player_id}"),
                    "from_team": teams.get(t.from_team_id, "Free Agent"),
                    "to_team": teams.get(t.to_team_id, "Unknown"),
                    "amount": t.amount,
                    "season_year": t.season_year,
                    "day": t.day
                })

            return JSONResponse(status_code=200, content={
                "transfers": tr_list,
                "summary": {
                    "total_transfers": len(tr_list),
                    "total_volume": sum(t.get("amount", 0) for t in tr_list)
                }
            })
    except Exception as e:
        logger.exception("Error getting transfer activity")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/all-seasons-overview")
async def get_all_seasons_overview():
    """Get aggregated overview data across all seasons directly from DB."""
    try:
        with get_db_session() as db:
            distinct_years = [r[0] for r in db.query(Match.season_year).distinct().order_by(Match.season_year.desc()).all() if r[0]]
            if not distinct_years:
                return JSONResponse(status_code=200, content={"seasons": [], "team_position_trends": {}, "total_seasons": 0})

            all_seasons_data = []
            team_positions = {}
            for yr in distinct_years:
                rep = build_live_season_report_from_db(yr)
                if rep and rep.get("table"):
                    table = rep.get("table", [])
                    season_stats = rep.get("season_stats", {})
                    transfer_summary = rep.get("transfer_summary", {})
                    champ_name = rep.get("champions", "")
                    champ_pts = table[0][1].get("points", 0) if table else 0

                    for pos, (tname, stats) in enumerate(table, 1):
                        if tname not in team_positions:
                            team_positions[tname] = []
                        team_positions[tname].append({"season": yr, "position": pos, "points": stats.get("points", 0)})

                    all_seasons_data.append({
                        "season_year": yr,
                        "champions": champ_name,
                        "champion_points": champ_pts,
                        "top_scorer": None,
                        "total_goals": season_stats.get("total_goals", 0),
                        "total_matches": season_stats.get("total_matches", 0),
                        "avg_goals_per_match": season_stats.get("average_goals_per_match", 0),
                        "best_attack": {"team": champ_name, "goals": table[0][1].get("gf", 0) if table else 0},
                        "best_defense": {"team": champ_name, "goals_conceded": table[0][1].get("ga", 0) if table else 0},
                        "transfers_completed": transfer_summary.get("transfers_completed", 0),
                        "total_market_value": transfer_summary.get("total_market_value", 0)
                    })

            return JSONResponse(status_code=200, content={
                "seasons": all_seasons_data,
                "team_position_trends": team_positions,
                "total_seasons": len(all_seasons_data)
            })
    except Exception as e:
        logger.exception("Error getting all seasons overview")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_fastapi:app", host="0.0.0.0", port=API_PORT, reload=API_DEBUG)
