import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

load_dotenv(
    PROJECT_ROOT / ".env"
)


USERNAME = os.getenv(
    "MLBTS_USERNAME",
    "",
).strip()

if not USERNAME:
    raise RuntimeError(
        "MLBTS_USERNAME is not configured. "
        "Copy .env.example to .env and set "
        "your MLB The Show username."
    )

PLATFORM = os.getenv(
    "MLBTS_PLATFORM",
    "psn",
).strip().lower()

MODE = os.getenv(
    "MLBTS_MODE",
    "arena",
).strip().lower()

BASE_URL = os.getenv(
    "MLBTS_BASE_URL",
    "https://mlb26.theshow.com",
).rstrip("/")

GAME_HISTORY_URL = (
    f"{BASE_URL}/apis/game_history.json"
)

GAME_LOG_URL = (
    f"{BASE_URL}/apis/game_log.json"
)

DATA_DIR = PROJECT_ROOT / "data"

RAW_GAME_LOG_DIR = (
    DATA_DIR / "raw_game_logs"
)

EXPORT_DIR = (
    DATA_DIR / "exports"
)

DB_PATH = (
    DATA_DIR / "mlb26_games.sqlite3"
)

CARD_CATALOG_CACHE_PATH = (
    DATA_DIR
    / "cache"
    / "mlb26_items_catalog.json"
)

REQUEST_DELAY_SECONDS = float(
    os.getenv(
        "MLBTS_REQUEST_DELAY_SECONDS",
        "0.75",
    )
)
