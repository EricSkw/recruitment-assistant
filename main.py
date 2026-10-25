"""Local API entry point.

From the repo root, after `pip install -r requirements.txt`:

    python main.py

Binds HOST and PORT (default 127.0.0.1:8000). The chat UI is a second process:
`cd src/frontend && npm run dev`. The Docker image does not use this file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "src" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from recruitment.paths import REPO_ROOT


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "recruitment.asgi:app",
        host=host,
        port=port,
        factory=False,
        app_dir=str(BACKEND),
    )


if __name__ == "__main__":
    main()
