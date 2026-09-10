import os
from pathlib import Path


USERNAME = os.getenv(
    "MLBTS_USERNAME",
    "poopoopee155",
).strip()

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

PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
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

REQUEST_DELAY_SECONDS = float(
    os.getenv(
        "MLBTS_REQUEST_DELAY_SECONDS",
        "0.75",
    )
)