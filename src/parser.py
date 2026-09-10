import re
from datetime import datetime
from typing import Any, Dict, Optional


USERNAME_STYLE_PATTERN = re.compile(r"\s*\^[^\s]*\^.*$")


def clean_username(value: str) -> str:
    if not value:
        return ""

    cleaned = USERNAME_STYLE_PATTERN.sub("", str(value))
    return cleaned.strip()


def normalize_text(value: Any) -> str:
    return clean_username(str(value or "")).strip().upper()


def is_cpu_value(value: Any) -> bool:
    return normalize_text(value) == "CPU"


def is_cpu_game(game: Dict[str, Any]) -> bool:
    """
    True CPU games are identified by team-name fields.

    Important:
    The MLB The Show API may show CPU in home_name or away_name to represent
    the searched user's side. Do not use home_name/away_name for CPU filtering.
    """
    return (
        is_cpu_value(game.get("home_full_name"))
        or is_cpu_value(game.get("away_full_name"))
    )


def parse_display_date(value: str) -> Optional[str]:
    if not value:
        return None

    try:
        return datetime.strptime(value, "%m/%d/%Y %H:%M:%S").isoformat(sep=" ")
    except ValueError:
        return None


def safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, "", " "):
            return None
        return int(value)
    except ValueError:
        return None


def safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", " "):
            return None
        return float(value)
    except ValueError:
        return None


def sum_csv_ints(value: str) -> int:
    total = 0

    for part in str(value).split(","):
        part = part.strip()
        if part.isdigit():
            total += int(part)

    return total


def get_user_side(game: Dict[str, Any], username: str) -> str:
    searched_username = clean_username(username).lower()
    home_name = clean_username(game.get("home_name", "")).lower()
    away_name = clean_username(game.get("away_name", "")).lower()

    if home_name == searched_username:
        return "home"

    if away_name == searched_username:
        return "away"

    home_is_cpu = home_name == "cpu"
    away_is_cpu = away_name == "cpu"

    if home_is_cpu and not away_is_cpu:
        return "home"

    if away_is_cpu and not home_is_cpu:
        return "away"

    return "unknown"


def get_user_result(game: Dict[str, Any], username: str) -> Optional[str]:
    side = get_user_side(game, username)

    if side == "home":
        return game.get("home_display_result")

    if side == "away":
        return game.get("away_display_result")

    return None


def get_opponent_name(game: Dict[str, Any], username: str) -> str:
    side = get_user_side(game, username)

    if side == "home":
        return clean_username(game.get("away_name", ""))

    if side == "away":
        return clean_username(game.get("home_name", ""))

    return ""


def get_opponent_team_name(game: Dict[str, Any], username: str) -> str:
    side = get_user_side(game, username)

    if side == "home":
        return game.get("away_full_name", "")

    if side == "away":
        return game.get("home_full_name", "")

    return ""


def extract_game_sections(game_log_response: Dict[str, Any]) -> Dict[str, Any]:
    sections: Dict[str, Any] = {}

    game_items = game_log_response.get("game", [])

    for item in game_items:
        if not isinstance(item, list):
            continue

        if len(item) != 2:
            continue

        key, value = item
        sections[key] = value

    return sections