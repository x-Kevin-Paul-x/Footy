"""
Resilient Development Server for Footy Backend.
Handles auto-reloading on file changes and automatically recovers from crashes on Windows.
"""
import os
import sys
import time
import subprocess
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent
BACKEND_DIR = BACKEND_SRC.parent
PROJECT_ROOT = BACKEND_DIR.parent

def run():
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    pythonpaths = [str(PROJECT_ROOT), str(BACKEND_SRC)]
    if existing_pp:
        pythonpaths.append(existing_pp)
    sys.path.insert(0, str(BACKEND_SRC))
    try:
        from config import API_PORT
    except Exception:
        API_PORT = 5001

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api_fastapi:app",
        "--app-dir",
        str(BACKEND_SRC),
        "--reload",
        "--reload-dir",
        str(BACKEND_SRC),
        "--port",
        str(API_PORT),
        "--host",
        "127.0.0.1",
    ]

    print(f"[Footy Dev Server] Starting backend on http://127.0.0.1:{API_PORT} (watching {BACKEND_SRC})...", flush=True)

    while True:
        try:
            proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), env=env)
            ret_code = proc.wait()

            # Clean exit / KeyboardInterrupt codes on Windows
            if ret_code in (0, -2, -15, 3221225786, 0xC000013A):
                break

            print(f"[Footy Dev Server] Process exited with code {ret_code}. Auto-restarting...", flush=True)
            time.sleep(0.5)

        except KeyboardInterrupt:
            if "proc" in locals() and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
            break
        except Exception as e:
            print(f"[Footy Dev Server] Exception: {e}. Auto-restarting in 1s...", flush=True)
            time.sleep(1)

if __name__ == "__main__":
    run()
