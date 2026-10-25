"""Command-line entry for one recruitment run.

From the repo root:

    python -m src.cli --job-description "Python Developer" --requirements "5 years experience"
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from recruitment.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
