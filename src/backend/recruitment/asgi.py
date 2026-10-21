"""Uvicorn application. Loads the repo .env without overriding existing variables."""

from dotenv import load_dotenv

from recruitment.paths import REPO_ROOT
from recruitment.api import create_app

load_dotenv(REPO_ROOT / ".env")
app = create_app()
