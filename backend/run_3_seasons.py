import os
import sys
import glob
import time
import shutil
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.session import DB_FILE
from database.db_setup import initialize_fresh_database
from config import REPORTS_DIR, DATA_DIR


def clean_all_data():
    print("═" * 78)
    print(" 🗑️  STEP 1: PURGING ALL EXISTING DATA, REPORTS, DUMPS & RECORDINGS")
    print("═" * 78)

    # 1. Clean reports subdirectories
    subdirs = ['season_reports', 'transfer_logs', 'match_reports', 'ml_reports', 'recordings']
    for s in subdirs:
        target_dir = REPORTS_DIR / s
        if target_dir.exists():
            files = list(target_dir.glob('*'))
            for f in files:
                try:
                    if f.is_file():
                        f.unlink()
                    elif f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
                except Exception as e:
                    print(f"  [!] Could not delete {f.name}: {e}")
            print(f"  ✓ Purged {len(files)} files from {s}/")

    # 2. Clean saves and main database
    saves_dir = DATA_DIR / 'saves'
    if saves_dir.exists():
        save_files = list(saves_dir.glob('*.db'))
        for f in save_files:
            try:
                f.unlink()
            except Exception:
                pass
        print(f"  ✓ Purged {len(save_files)} backup database saves")

    # 3. Wipe all existing tables in database cleanly (handles locked handles)
    from database.db_setup import reset_database
    reset_database(DB_FILE)
    print(f"  ✓ Wiped all tables in database: {os.path.basename(DB_FILE)}")

    # 4. Re-initialize clean fresh database schema
    initialize_fresh_database(DB_FILE)
    print("  ✓ Fresh database schema initialized successfully!\n")


def run_3_seasons_benchmark():
    print("═" * 78)
    print(" 🚀 STEP 2: SIMULATING 3 FULL SEASONS WITH PERFORMANCE BENCHMARKING")
    print("═" * 78)

    os.environ["FOOTY_NUM_SEASONS"] = "3"
    import config
    config.NUM_SEASONS = 3

    import main as footy_main
    footy_main.NUM_SEASONS = 3

    total_start_time = time.perf_counter()

    try:
        footy_main.main()
    except Exception as e:
        print(f"\n[ERROR] Simulation halted: {e}")
        import traceback
        traceback.print_exc()
        return

    total_duration = time.perf_counter() - total_start_time

    # Inspect SQLite database directly for benchmark metrics
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM Match;")
    total_matches = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM TransferHistory;")
    total_transfers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT season_year) FROM Match;")
    total_seasons = cur.fetchone()[0] or 3

    dump_files = glob.glob(str(REPORTS_DIR / 'recordings' / '*.dump'))

    print("\n" + "═" * 78)
    print(" 📊 3-SEASON BENCHMARK PERFORMANCE REPORT")
    print("═" * 78)
    print(f" • Total Simulation Time   : {total_duration:.2f} seconds ({total_duration/60:.2f} mins)")
    print(f" • Average Time Per Season : {total_duration / max(1, total_seasons):.2f} seconds")
    print(f" • Total Matches Simulated : {total_matches} (38 matchdays × {total_seasons} seasons)")
    print(f" • Total Transfers Recorded: {total_transfers} completed deals in DB")
    print(f" • Average Time Per Match  : {(total_duration / max(1, total_matches)) * 1000:.2f} ms")
    print(f" • Average Matchday Time   : {total_duration / max(1, total_seasons * 38):.2f} seconds (10 matches/matchday)")
    print(f" • Native .dump Files      : {len(dump_files)}")
    print("═" * 78 + "\n")


if __name__ == "__main__":
    if "--yes" not in sys.argv and os.environ.get("FOOTY_CONFIRM_RESET") != "1":
        print("\n[GUARD] run_3_seasons.py will purge all database data and report artifacts.")
        print("To proceed, run with --yes flag or set FOOTY_CONFIRM_RESET=1 environment variable:")
        print("    python backend/run_3_seasons.py --yes\n")
        sys.exit(1)

    clean_all_data()
    run_3_seasons_benchmark()

