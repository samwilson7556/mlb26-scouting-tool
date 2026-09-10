from pathlib import Path


USERNAME = "poopoopee155"
PLATFORM = "psn"
MODE = "arena"

BASE_URL = "https://mlb26.theshow.com"

GAME_HISTORY_URL = f"{BASE_URL}/apis/game_history.json"
GAME_LOG_URL = f"{BASE_URL}/apis/game_log.json"

GAME_WEB_URL_TEMPLATE = (
    f"{BASE_URL}/games/{{game_id}}?platform={PLATFORM}&username={USERNAME}"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_GAME_LOG_DIR = DATA_DIR / "raw_game_logs"
EXPORT_DIR = DATA_DIR / "exports"

DB_PATH = DATA_DIR / "mlb26_games.sqlite3"

REQUEST_DELAY_SECONDS = 0.75
RETRY_DELAY_SECONDS = 2.0