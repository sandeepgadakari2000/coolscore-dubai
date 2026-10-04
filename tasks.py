"""Cross-platform task runner (Windows has no `make`).

Usage: python tasks.py <task> [extra args passed through]
Tasks: setup, data, report-weather, report-physics, simulate, train, validate, assumptions, test, app, api,
       launch (start the app and open it in the browser; what "Start CoolScore.cmd" runs)
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
APP_PORT = 8501

TASKS: dict[str, list[str]] = {
    "setup": [PY, "-m", "pip", "install", "-r", "requirements.txt"],
    "test": [PY, "-m", "pytest", "-q"],
    "data": [PY, "-m", "coolscore.weather.dataset"],
    "report-weather": [PY, "-m", "coolscore.weather.report"],
    "report-physics": [PY, "-m", "coolscore.physics.report"],
    "simulate": [PY, "-m", "coolscore.simulate.run"],
    "train": [PY, "-m", "coolscore.model.train"],
    "validate": [PY, "-m", "coolscore.validation.report"],
    "assumptions": [PY, "-m", "coolscore.assumptions_doc"],
    "app": [PY, "-m", "streamlit", "run", "app/Home.py"],
    "api": [PY, "-m", "uvicorn", "api.main:app", "--port", "8000"],
}


def _listening(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def launch(extra: list[str], env: dict) -> int:
    """Start the Streamlit app and open it in the default browser as soon as it answers.

    If the app is already running (a second double-click), just open the browser again.
    """
    url = f"http://localhost:{APP_PORT}"
    if _listening(APP_PORT):
        print(f"CoolScore is already running; opening {url}")
        webbrowser.open(url)
        return 0
    proc = subprocess.Popen(TASKS["app"] + ["--server.port", str(APP_PORT), "--server.headless", "true"] + extra,
                            cwd=ROOT, env=env)
    try:
        for _ in range(240):                       # up to 2 minutes for a cold first start
            if proc.poll() is not None:
                return proc.returncode
            if _listening(APP_PORT):
                print(f"\nCoolScore is ready at {url} (opening your browser)\n")
                webbrowser.open(url)
                break
            time.sleep(0.5)
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        return 0


def main(argv: list[str]) -> int:
    """Run one task."""
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    if argv and argv[0] == "launch":
        return launch(argv[1:], env)
    if not argv or argv[0] not in TASKS:
        print(__doc__)
        return 2
    return subprocess.call(TASKS[argv[0]] + argv[1:], cwd=ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
