"""Start the API on the loopback interface by default."""

import os

import uvicorn
from dotenv import load_dotenv

from recruitment.paths import REPO_ROOT


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("recruitment.asgi:app", host=host, port=port, factory=False)


if __name__ == "__main__":
    main()
