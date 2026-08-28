import os
import sys
import glob
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.session import DB_FILE
from database.db_setup import initialize_fresh_database
from config import REPORTS_DIR

def clean_old_seasons():
    print("--- 1. Cleaning old season reports and database ---")
    # Delete old season reports
    season_reports = glob.glob(str(REPORTS_DIR / 'season_reports' / '*.json'))
    for f in season_reports:
        try:
            os.remove(f)
            print(f"Deleted {os.path.basename(f)}")
        except Exception as e:
            print(f"Error removing {f}: {e}")

    transfer_reports = glob.glob(str(REPORTS_DIR / 'transfer_logs' / '*.json'))
    for f in transfer_reports:
        try:
            os.remove(f)
            print(f"Deleted {os.path.basename(f)}")
        except Exception as e:
            print(f"Error removing {f}: {e}")

    # Remove database file if exists
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"Deleted database {DB_FILE}")
        except Exception as e:
            print(f"Error removing database: {e}")

    # Re-initialize clean tables
    initialize_fresh_database()
    print("Clean database ready!\n")

def run_seasons():
    print("--- 2. Simulating 3 Fresh Seasons on the new Engine ---")
    os.environ["FOOTY_NUM_SEASONS"] = "3"
    import config
    config.NUM_SEASONS = 3
    import main as footy_main
    footy_main.NUM_SEASONS = 3
    footy_main.main()
    print("--- 3 Seasons Successfully Simulated! ---")

if __name__ == "__main__":
    clean_old_seasons()
    run_seasons()
