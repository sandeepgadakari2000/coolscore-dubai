"""Cross-platform task runner (Windows has no `make`).

Usage: python tasks.py <task>
Tasks: setup, data, simulate, train, validate, test, app, api
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

TASKS: dict[str, list[str] | str] = {
    "setup": [PY, "-m", "pip", "install", "-r", "requirements.txt"],
    "test": [PY, "-m", "pytest", "-q"],
    "data": "Phase 1: weather fetch + facade irradiance",
    "simulate": "Phase 4: scenario dataset",
    "train": "Phase 4: surrogate models",
    "validate": "Phase 8: real-bill validation report",
    "app": "Phase 5: Streamlit app",
    "api": "Phase 6: FastAPI service",
}


def main(argv: list[str]) -> int:
    """Run one task; unimplemented tasks say which phase builds them."""
    if len(argv) != 1 or argv[0] not in TASKS:
        print(__doc__)
        return 2
    task = TASKS[argv[0]]
    if isinstance(task, str):
        print(f"'{argv[0]}' is not built yet ({task}).")
        return 1
    return subprocess.call(task, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
