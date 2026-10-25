"""Deploy-only ASGI target.

Serves the built chat page from ``src/frontend/dist`` on the same process as the
existing FastAPI app. Local development keeps using ``src/backend/main.py`` and
the Vite dev server. This module does not change crew, gate, or API behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "src" / "backend"
DIST_DIR = REPO_ROOT / "src" / "frontend" / "dist"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.staticfiles import StaticFiles

from recruitment.asgi import app

if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
