"""Cross-platform task runner (Windows has no `make`).

Usage: python tasks.py <task> [extra args passed through]
Tasks: setup, data, report-weather, report-physics, simulate, train, validate, test, app, api
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

TASKS: dict[str, list[str] | str] = {
    "setup": [PY, "-m", "pip", "install", "-r", "requirements.txt"],
    "test": [PY, "-m", "pytest", "-q"],
    "data": [PY, "-m", "coolscore.weather.dataset"],
    "report-weather": [PY, "-m", "coolscore.weather.report"],
    "report-physics": [PY, "-m", "coolscore.physics.report"],
    "simulate": [PY, "-m", "coolscore.simulate.run"],
    "train": [PY, "-m", "coolscore.model.train"],
    "validate": [PY, "-m", "coolscore.validation.report"],
    "app": [PY, "-m", "streamlit", "run", "app/Home.py"],
    "api": [PY, "-m", "uvicorn", "api.main:app", "--port", "8000"],
}


def main(argv: list[str]) -> int:
    """Run one task; unimplemented tasks say which phase builds them."""
    if not argv or argv[0] not in TASKS:
        print(__doc__)
        return 2
    task = TASKS[argv[0]]
    if isinstance(task, str):
        print(f"'{argv[0]}' is not built yet ({task}).")
        return 1
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.call(task + argv[1:], cwd=ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
