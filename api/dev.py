"""Local preview of the Vercel deployment: the API plus the static site on one port (python tasks.py web)."""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from index import ROOT, app  # noqa: F401  (index.py adds src/ to sys.path)

app.mount("/", StaticFiles(directory=Path(ROOT) / "site", html=True), name="site")
