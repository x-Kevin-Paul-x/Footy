import os
import shutil
import subprocess
import json # <--- Add this import
from flask import Flask, jsonify
from flask_cors import CORS

# Import DB query functions
from team_db import get_all_teams
from player_db import get_all_players
from match_db import get_matches_for_season, get_match_details

app = Flask(__name__)
CORS(app)  # Enable CORS for local development

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEASON_REPORTS_DIR = os.path.join(BASE_DIR, "season_reports")
MATCH_REPORTS_DIR = os.path.join(BASE_DIR, "match_reports")
TRANSFER_LOGS_DIR = os.path.join(BASE_DIR, "transfer_logs")
SIMULATION_SCRIPT = os.path.join(BASE_DIR, "main.py")

def clear_directory(directory_path):
    """Removes all files and subdirectories in the given directory."""
    if os.path.exists(directory_path):
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print(f"Cleared directory: {directory_path}")
    else:
        print(f"Directory not found, creating: {directory_path}")
        os.makedirs(directory_path)


@app.route('/run-simulation', methods=['POST'])
def run_simulation():
    try:
        print("Received request to run simulation.")
        
        # 1. Clear old report directories
        print("Clearing old report directories...")
        clear_directory(SEASON_REPORTS_DIR)
        clear_directory(MATCH_REPORTS_DIR)
        clear_directory(TRANSFER_LOGS_DIR)
        print("Old report directories cleared.")

        # 2. Run the main.py simulation script
        print(f"Running simulation script: {SIMULATION_SCRIPT}")
        # Ensure main.py is executable or run with python interpreter
        process = subprocess.Popen(['python', SIMULATION_SCRIPT],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   cwd=BASE_DIR) # Run from project root
        
        stdout, stderr = process.communicate() # Wait for the process to complete
        
        print("Simulation script stdout:")
        print(stdout)
        
        if process.returncode == 0:
            print("Simulation completed successfully.")
            # Check if season reports were generated
            if not os.listdir(SEASON_REPORTS_DIR):
                 print("Warning: Simulation completed but no season reports found.")
                 return jsonify({"status": "success", "message": "Simulation completed, but no season reports were generated."}), 200
            return jsonify({"status": "success", "message": "Simulation completed successfully. New reports generated."}), 200
        else:
            print(f"Simulation failed. Return code: {process.returncode}")
            print("Simulation script stderr:")
            print(stderr)
            return jsonify({"status": "error", "message": "Simulation failed.", "details": stderr}), 500

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-seasons', methods=['GET'])
def get_seasons():
    try:
        if not os.path.exists(SEASON_REPORTS_DIR):
            return jsonify({"seasons": [], "message": "Season reports directory not found."}), 200
        
        report_files = [f for f in os.listdir(SEASON_REPORTS_DIR) if f.startswith("season_report_") and f.endswith(".json")]
        seasons = []
        for report_file in report_files:
            try:
                year = report_file.replace("season_report_", "").replace(".json", "")
                seasons.append(int(year))
            except ValueError:
                print(f"Could not parse year from filename: {report_file}")
        
        seasons.sort(reverse=True) # Show newest first
        return jsonify({"seasons": seasons}), 200
    except Exception as e:
        print(f"Error getting seasons: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-season-report/<int:year>', methods=['GET'])
def get_season_report(year):
    """
    Return the season report JSON but augment it with DB-backed transfer history if available.
    This keeps the season report authoritative while ensuring completed transfers persistently
    stored in the DB are surfaced to the frontend.
    """
    try:
        report_path = os.path.join(SEASON_REPORTS_DIR, f"season_report_{year}.json")
        if not os.path.exists(report_path):
            return jsonify({"status": "error", "message": f"Season report for {year} not found."}), 404

        with open(report_path, 'r') as f:
            data = json.load(f)

        # Attempt to enrich the report with TransferHistory rows from the DB (durable source)
        try:
            import sqlite3
            from db_setup import DB_FILE

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

            conn.close()
        except Exception as e:
            # Non-fatal: log and return original report if DB read fails
            print(f"Warning: failed to read TransferHistory from DB: {e}")

        return jsonify(data), 200
    except Exception as e:
        print(f"Error getting season report for {year}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/teams', methods=['GET'])
def get_teams():
    teams = get_all_teams()
    # Normalize: convert tuples to dicts
    keys = ["team_id", "name", "budget", "weekly_budget", "transfer_budget", "wage_budget", "manager_id"]
    teams_json = [dict(zip(keys, t)) for t in teams]
    return jsonify({"teams": teams_json}), 200

@app.route('/players', methods=['GET'])
def get_players():
    players = get_all_players()
    # Already normalized as dicts by player_db.py
    return jsonify({"players": players}), 200

@app.route('/matches/<int:season_year>', methods=['GET'])
def get_matches_by_season(season_year):
    """API endpoint to get all matches for a given season."""
    try:
        matches = get_matches_for_season(season_year)
        if not matches:
            return jsonify({"matches": [], "message": f"No matches found for season {season_year}."}), 200
        return jsonify({"matches": matches}), 200
    except Exception as e:
        print(f"Error getting matches for season {season_year}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/match/<int:match_id>', methods=['GET'])
def get_match(match_id):
    """API endpoint to get detailed information for a single match."""
    try:
        match_details = get_match_details(match_id)
        if not match_details:
            return jsonify({"status": "error", "message": f"Match with ID {match_id} not found."}), 404
        return jsonify(match_details), 200
    except Exception as e:
        print(f"Error getting match details for match {match_id}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Ensure directories exist before starting
    os.makedirs(SEASON_REPORTS_DIR, exist_ok=True)
    os.makedirs(MATCH_REPORTS_DIR, exist_ok=True)
    os.makedirs(TRANSFER_LOGS_DIR, exist_ok=True)
    app.run(debug=True, port=5001) # Using port 5001 to avoid conflict with React dev server
