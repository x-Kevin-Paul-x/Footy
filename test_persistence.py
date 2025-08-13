import os
import subprocess
import sqlite3
import time

DB_FILE = "football_sim.db"

def run_main_script():
    """Runs the main.py script and captures its output."""
    process = subprocess.Popen(['python', 'main.py', '--seasons', '1'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    output_lines = []
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(line.strip())
        output_lines.append(line.strip())

    process.wait()
    return "\n".join(output_lines)

def check_db_has_data():
    """Checks if the database has data in the League table."""
    if not os.path.exists(DB_FILE):
        return False
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM League")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def main():
    print("--- Persistence Test Starting ---")

    # 1. Clean up old database file
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed existing database file: {DB_FILE}")

    # 2. First run: Create and populate the database
    print("\n--- Running simulation for the first time (should create data) ---")
    output1 = run_main_script()

    if "Traceback" in output1:
        print("TEST FAILED: First run produced a traceback.")
        return
    if "Creating new tables..." not in output1:
        print("TEST FAILED: First run did not create new tables.")
        return

    if not check_db_has_data():
        print("TEST FAILED: Database has no data after first run.")
        return

    print("First run completed. Database created and populated.")
    time.sleep(1) # Give a moment for file handles to close

    # 3. Second run: Load from the existing database
    print("\n--- Running simulation for the second time (should load data) ---")
    output2 = run_main_script()

    if "Traceback" in output2:
        print("TEST FAILED: Second run produced a traceback.")
        return
    if "Loading data..." not in output2:
        print("TEST FAILED: Second run did not load data from the database.")
        return

    if "Creating new tables..." in output2:
        print("TEST FAILED: Second run recreated tables instead of loading.")
        return

    print("\n--- Persistence Test Passed! ---")
    print("The simulation correctly created the database on the first run and loaded from it on the second run.")

if __name__ == "__main__":
    main()
