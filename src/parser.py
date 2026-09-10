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


def normalize_username(value: Any) -> str:
    return clean_username(str(value or "")).strip().lower()


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
        return datetime.strptime(
            value,
            "%m/%d/%Y %H:%M:%S",
        ).isoformat(sep=" ")
    except ValueError:
        return None


def safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, "", " "):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", " "):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def sum_csv_ints(value: str) -> int:
    total = 0

    for part in str(value).split(","):
        part = part.strip()

        if not part:
            continue

        try:
            total += int(part)
        except ValueError:
            continue

    return total


def get_user_side(game: Dict[str, Any], username: str) -> str:
    searched_username = normalize_username(username)
    home_name = normalize_username(game.get("home_name", ""))
    away_name = normalize_username(game.get("away_name", ""))

    if home_name == searched_username:
        return "home"

    if away_name == searched_username:
        return "away"

    # The API occasionally uses "CPU" in home_name / away_name as a marker
    # for the searched user's side even when the actual opponent is human.
    home_is_cpu_marker = home_name == "cpu"
    away_is_cpu_marker = away_name == "cpu"

    if home_is_cpu_marker and not away_is_cpu_marker:
        return "home"

    if away_is_cpu_marker and not home_is_cpu_marker:
        return "away"

    return "unknown"


def get_user_result(
    game: Dict[str, Any],
    username: str,
) -> Optional[str]:
    side = get_user_side(game, username)

    if side == "home":
        return game.get("home_display_result")

    if side == "away":
        return game.get("away_display_result")

    return None


def get_opponent_name(
    game: Dict[str, Any],
    username: str,
) -> str:
    side = get_user_side(game, username)

    if side == "home":
        return clean_username(game.get("away_name", ""))

    if side == "away":
        return clean_username(game.get("home_name", ""))

    return ""


def get_opponent_team_name(
    game: Dict[str, Any],
    username: str,
) -> str:
    side = get_user_side(game, username)

    if side == "home":
        return game.get("away_full_name", "")

    if side == "away":
        return game.get("home_full_name", "")

    return ""


def extract_game_sections(
    game_log_response: Dict[str, Any],
) -> Dict[str, Any]:
    sections: Dict[str, Any] = {}

    game_items = game_log_response.get("game", [])

    if not isinstance(game_items, list):
        return sections

    for item in game_items:
        if not isinstance(item, list):
            continue

        if len(item) != 2:
            continue

        key, value = item
        sections[key] = value

    return sections


def innings_pitched_to_outs(value: Any) -> Optional[int]:
    """
    Convert baseball innings-pitched notation into outs.

    Baseball IP is not a decimal value:
        5.0 -> 15 outs
        5.1 -> 16 outs
        5.2 -> 17 outs

    Returns None for missing or invalid input.
    """
    if value in (None, "", " "):
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        if "." in text:
            whole_text, partial_text = text.split(".", 1)
        else:
            whole_text, partial_text = text, "0"

        whole_innings = int(whole_text)
    except ValueError:
        return None

    partial_text = partial_text.strip()

    if partial_text == "":
        partial_outs = 0
    elif partial_text == "0":
        partial_outs = 0
    elif partial_text == "1":
        partial_outs = 1
    elif partial_text == "2":
        partial_outs = 2
    else:
        return None

    if whole_innings < 0:
        return None

    return (whole_innings * 3) + partial_outs


def outs_to_innings_pitched(outs: Any) -> Optional[str]:
    """
    Convert a count of pitching outs back to baseball IP notation.

        15 -> "5.0"
        16 -> "5.1"
        17 -> "5.2"
    """
    parsed_outs = safe_int(outs)

    if parsed_outs is None or parsed_outs < 0:
        return None

    whole_innings, partial_outs = divmod(parsed_outs, 3)

    return f"{whole_innings}.{partial_outs}"


def calculate_era(
    earned_runs: Any,
    pitching_outs: Any,
) -> Optional[float]:
    """
    Calculate ERA from earned runs and pitching outs.

    ERA = ER * 27 / outs
    """
    parsed_er = safe_int(earned_runs)
    parsed_outs = safe_int(pitching_outs)

    if parsed_er is None:
        return None

    if parsed_outs is None or parsed_outs <= 0:
        return None

    return round((parsed_er * 27) / parsed_outs, 2)