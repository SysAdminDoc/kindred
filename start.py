"""
Kindred v1.3.0 - Turnkey Launcher
Auto-creates venv, installs deps, and starts both user + admin servers.
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"


def run(cmd, **kwargs):
    print(f"  > {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, **kwargs)


def main():
    print()
    print("=" * 50)
    print("  Kindred v1.3.0 - Compatibility Engine")
    print("=" * 50)
    print()

    # 1. Create venv if needed
    pip = VENV / ("Scripts" if os.name == "nt" else "bin") / "pip"
    python = VENV / ("Scripts" if os.name == "nt" else "bin") / "python"

    if not VENV.exists():
        print("[1/3] Creating virtual environment...")
        run([sys.executable, "-m", "venv", str(VENV)])
    else:
        print("[1/3] Virtual environment exists.")

    # 2. Install dependencies
    print("[2/3] Installing dependencies...")
    run([str(pip), "install", "-q", "-r", str(REQUIREMENTS)])

    # Load config for ports
    host = os.getenv("KINDRED_HOST", "127.0.0.1")
    user_port = os.getenv("KINDRED_USER_PORT", "8000")
    admin_port = os.getenv("KINDRED_ADMIN_PORT", "8001")

    # 3. Start both servers
    print("[3/3] Starting Kindred servers...")
    print()
    print(f"  User portal:  http://{host}:{user_port}")
    print(f"  Admin portal: http://{host}:{admin_port}")
    print("  Press Ctrl+C to stop both")
    print()

    # Open browser after a short delay
    import threading
    import webbrowser
    def open_browsers():
        import time
        time.sleep(2)
        webbrowser.open(f"http://{host}:{user_port}")
        webbrowser.open(f"http://{host}:{admin_port}")
    threading.Thread(target=open_browsers, daemon=True).start()

    # Start admin server in background
    admin_proc = subprocess.Popen(
        [str(python), "-m", "uvicorn", "app.admin_app:admin_app",
         "--host", host, "--port", admin_port, "--reload"],
        cwd=str(ROOT),
    )

    try:
        # Run user server in foreground
        run([str(python), "-m", "uvicorn", "app.main:app",
             "--host", host, "--port", user_port, "--reload"],
            cwd=str(ROOT))
    finally:
        admin_proc.terminate()
        admin_proc.wait()


if __name__ == "__main__":
    main()
