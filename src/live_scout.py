import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from rich.console import Console
from rich.table import Table

from .config import BASE_URL, EXPORT_DIR, MODE, REQUEST_DELAY_SECONDS
from .parser import (
    calculate_era,
    extract_game_sections,
    get_opponent_name,
    get_opponent_team_name,
    get_user_result,
    get_user_side,
    innings_pitched_to_outs,
    is_cpu_game,
    normalize_username,
    outs_to_innings_pitched,
    parse_display_date,
    safe_int,
)


console = Console()


@dataclass
class LiveScoutConfig:
    username: str
    platform: str = "psn"
    mode: str = MODE
    max_pages: int = 1
    max_games: int = 25
    include_logs: bool = False
    log_workers: int = 5


def create_live_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 MLB26 Live Opponent Scout",
            "Accept": "application/json,text/html,*/*",
        }
    )

    return session


def fetch_json(
    session: requests.Session,
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_game_history_for_user(
    session: requests.Session,
    username: str,
    platform: str,
    mode: str,
    max_pages: int = 1,
) -> Tuple[List[Dict[str, Any]], int]:
    game_history_url = f"{BASE_URL}/apis/game_history.json"

    first_page = fetch_json(
        session,
        game_history_url,
        params={
            "page": 1,
            "username": username,
            "platform": platform,
            "mode": mode,
        },
    )

    total_pages = int(first_page.get("total_pages", 1))
    pages_to_fetch = min(total_pages, max_pages)

    games: List[Dict[str, Any]] = []
    games.extend(first_page.get("game_history", []))

    console.print(
        f"[bold green]Found {total_pages} total page(s) for {username}. "
        f"Fetching {pages_to_fetch} page(s).[/bold green]"
    )

    for page in range(2, pages_to_fetch + 1):
        time.sleep(REQUEST_DELAY_SECONDS)

        page_data = fetch_json(
            session,
            game_history_url,
            params={
                "page": page,
                "username": username,
                "platform": platform,
                "mode": mode,
            },
        )

        page_games = page_data.get("game_history", [])
        games.extend(page_games)

        console.print(
            f"Fetched page {page}/{pages_to_fetch}: "
            f"{len(page_games)} games"
        )

    return games, pages_to_fetch


def is_attributable_user_game(
    game: Dict[str, Any],
    username: str,
) -> bool:
    """
    A useful live-scout game must:

    1. Not be against CPU.
    2. Have the searched username identifiable as home or away.
    3. Have an identifiable opponent.
    """
    if is_cpu_game(game):
        return False

    side = get_user_side(game, username)

    if side not in {"home", "away"}:
        return False

    opponent_name = get_opponent_name(game, username)

    if not opponent_name:
        return False

    return True


def get_runs_for_user(
    game: Dict[str, Any],
    username: str,
) -> Tuple[Optional[int], Optional[int]]:
    side = get_user_side(game, username)

    if side == "home":
        return (
            safe_int(game.get("home_runs")),
            safe_int(game.get("away_runs")),
        )

    if side == "away":
        return (
            safe_int(game.get("away_runs")),
            safe_int(game.get("home_runs")),
        )

    return None, None


def get_hits_for_user(
    game: Dict[str, Any],
    username: str,
) -> Tuple[Optional[int], Optional[int]]:
    side = get_user_side(game, username)

    if side == "home":
        return (
            safe_int(game.get("home_hits")),
            safe_int(game.get("away_hits")),
        )

    if side == "away":
        return (
            safe_int(game.get("away_hits")),
            safe_int(game.get("home_hits")),
        )

    return None, None


def get_errors_for_user(
    game: Dict[str, Any],
    username: str,
) -> Tuple[Optional[int], Optional[int]]:
    side = get_user_side(game, username)

    if side == "home":
        return (
            safe_int(game.get("home_errors")),
            safe_int(game.get("away_errors")),
        )

    if side == "away":
        return (
            safe_int(game.get("away_errors")),
            safe_int(game.get("home_errors")),
        )

    return None, None


def sort_games_newest_first(
    games: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return sorted(
        games,
        key=lambda game: parse_display_date(
            game.get("display_date", "")
        )
        or "",
        reverse=True,
    )


def fetch_game_log_for_user(
    session: requests.Session,
    game_id: str,
    username: str,
    platform: str,
) -> Dict[str, Any]:
    """
    Fetch a game log exactly once using the identity required by MLBTS.

    Game logs are requested directly from the MLBTS API.
    """
    game_log_url = f"{BASE_URL}/apis/game_log.json"

    return fetch_json(
        session,
        game_log_url,
        params={
            "id": game_id,
            "username": username,
            "platform": platform,
        },
    )


def locate_team_box_for_username(
    game_log: Dict[str, Any],
    username: str,
) -> Optional[Dict[str, Any]]:
    sections = extract_game_sections(game_log)

    line_score = sections.get("line_score", {})
    box_score = sections.get("box_score", [])

    if not isinstance(line_score, dict):
        return None

    if not isinstance(box_score, list):
        return None

    home_name = normalize_username(
        line_score.get("home_name", "")
    )
    away_name = normalize_username(
        line_score.get("away_name", "")
    )
    searched_username = normalize_username(username)

    if home_name == searched_username:
        target_team_id = str(
            line_score.get("home_mlb_team_id", "")
        )
    elif away_name == searched_username:
        target_team_id = str(
            line_score.get("away_mlb_team_id", "")
        )
    else:
        return None

    for team_box in box_score:
        if not isinstance(team_box, dict):
            continue

        if str(team_box.get("team_id", "")) == target_team_id:
            return team_box

    return None


def parse_live_log_stats_for_username(
    game_log: Dict[str, Any],
    username: str,
) -> Optional[Dict[str, Any]]:
    team_box = locate_team_box_for_username(
        game_log,
        username,
    )

    if not team_box:
        return None

    team_id = str(team_box.get("team_id", ""))
    team_details = team_box.get(team_id, {})

    if not isinstance(team_details, dict):
        return None

    batting_totals = team_details.get(
        "batting_totals",
        {},
    )
    pitching_totals = team_details.get(
        "pitching_totals",
        {},
    )

    if not isinstance(batting_totals, dict):
        batting_totals = {}

    if not isinstance(pitching_totals, dict):
        pitching_totals = {}

    batting_ab = safe_int(
        batting_totals.get("ab")
    ) or 0

    batting_h = safe_int(
        batting_totals.get("h")
    ) or 0

    pitching_outs = innings_pitched_to_outs(
        pitching_totals.get("ip")
    ) or 0

    pitching_er = safe_int(
        pitching_totals.get("er")
    ) or 0

    return {
        "batting_ab": batting_ab,
        "batting_h": batting_h,
        "pitching_outs": pitching_outs,
        "pitching_er": pitching_er,
    }


def fetch_and_parse_log_for_game(
    game: Dict[str, Any],
    username: str,
    platform: str,
) -> Dict[str, Any]:
    """
    Worker used by ThreadPoolExecutor.

    Each worker creates its own requests.Session because
    requests.Session is not guaranteed to be thread-safe.
    """
    game_id = str(game.get("id", ""))

    result: Dict[str, Any] = {
        "game_id": game_id,
        "success": False,
        "error": None,
        "stats": None,
    }

    if not game_id:
        result["error"] = "Missing game id"
        return result

    try:
        session = create_live_session()

        game_log = fetch_game_log_for_user(
            session=session,
            game_id=game_id,
            username=username,
            platform=platform,
        )

        if "error" in game_log:
            result["error"] = str(game_log)
            return result

        parsed_stats = parse_live_log_stats_for_username(
            game_log=game_log,
            username=username,
        )

        if not parsed_stats:
            result["error"] = (
                "Could not parse stats from game log"
            )
            return result

        result["success"] = True
        result["stats"] = parsed_stats

        return result

    except Exception as exc:
        result["error"] = str(exc)
        return result


def fetch_live_log_stats_concurrently(
    games: List[Dict[str, Any]],
    username: str,
    platform: str,
    max_workers: int,
) -> Dict[str, Any]:
    log_stats: Dict[str, Any] = {
        "logs_requested": True,
        "logs_fetched": 0,
        "logs_failed": 0,
        "batting_ab": 0,
        "batting_h": 0,
        "pitching_outs": 0,
        "pitching_ip": "0.0",
        "pitching_er": 0,
        "batting_average": None,
        "era": None,
        "worker_count": 0,
    }

    if not games:
        return log_stats

    worker_count = max(
        1,
        min(max_workers, len(games)),
    )

    log_stats["worker_count"] = worker_count

    console.print(
        f"[cyan]Fetching {len(games)} game log(s) "
        f"with {worker_count} concurrent worker(s)..."
        f"[/cyan]"
    )

    with ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:
        futures = [
            executor.submit(
                fetch_and_parse_log_for_game,
                game,
                username,
                platform,
            )
            for game in games
        ]

        for index, future in enumerate(
            as_completed(futures),
            start=1,
        ):
            result = future.result()
            game_id = result.get("game_id")

            if result.get("success"):
                parsed_stats = result["stats"]

                log_stats["logs_fetched"] += 1
                log_stats["batting_ab"] += (
                    parsed_stats["batting_ab"]
                )
                log_stats["batting_h"] += (
                    parsed_stats["batting_h"]
                )
                log_stats["pitching_outs"] += (
                    parsed_stats["pitching_outs"]
                )
                log_stats["pitching_er"] += (
                    parsed_stats["pitching_er"]
                )

                console.print(
                    f"[green]"
                    f"[{index}/{len(games)}] "
                    f"Parsed game log {game_id}"
                    f"[/green]"
                )
            else:
                log_stats["logs_failed"] += 1

                console.print(
                    f"[red]"
                    f"[{index}/{len(games)}] "
                    f"Failed game log {game_id}: "
                    f"{result.get('error')}"
                    f"[/red]"
                )

    if log_stats["batting_ab"] > 0:
        log_stats["batting_average"] = round(
            log_stats["batting_h"]
            / log_stats["batting_ab"],
            3,
        )

    log_stats["pitching_ip"] = (
        outs_to_innings_pitched(
            log_stats["pitching_outs"]
        )
        or "0.0"
    )

    log_stats["era"] = calculate_era(
        log_stats["pitching_er"],
        log_stats["pitching_outs"],
    )

    return log_stats


def build_live_scout_report(
    config: LiveScoutConfig,
) -> Dict[str, Any]:
    session = create_live_session()

    all_games, pages_fetched = (
        fetch_game_history_for_user(
            session=session,
            username=config.username,
            platform=config.platform,
            mode=config.mode,
            max_pages=config.max_pages,
        )
    )

    non_cpu_games = [
        game
        for game in all_games
        if not is_cpu_game(game)
    ]

    attributable_games = [
        game
        for game in non_cpu_games
        if is_attributable_user_game(
            game,
            config.username,
        )
    ]

    skipped_unattributable_games = (
        len(non_cpu_games)
        - len(attributable_games)
    )

    human_games = sort_games_newest_first(
        attributable_games
    )

    recent_games = human_games[
        : config.max_games
    ]

    wins = 0
    losses = 0
    unknown_results = 0

    runs_scored_values: List[int] = []
    runs_allowed_values: List[int] = []
    hits_for_values: List[int] = []
    hits_allowed_values: List[int] = []
    errors_for_values: List[int] = []

    game_rows: List[Dict[str, Any]] = []

    for game in recent_games:
        result = get_user_result(
            game,
            config.username,
        )

        if result == "W":
            wins += 1
        elif result == "L":
            losses += 1
        else:
            unknown_results += 1

        runs_for, runs_against = get_runs_for_user(
            game,
            config.username,
        )

        hits_for, hits_against = get_hits_for_user(
            game,
            config.username,
        )

        errors_for, _errors_against = (
            get_errors_for_user(
                game,
                config.username,
            )
        )

        if runs_for is not None:
            runs_scored_values.append(runs_for)

        if runs_against is not None:
            runs_allowed_values.append(
                runs_against
            )

        if hits_for is not None:
            hits_for_values.append(hits_for)

        if hits_against is not None:
            hits_allowed_values.append(
                hits_against
            )

        if errors_for is not None:
            errors_for_values.append(
                errors_for
            )

        game_rows.append(
            {
                "id": game.get("id"),
                "display_date": game.get(
                    "display_date"
                ),
                "result": result,
                "runs_for": runs_for,
                "runs_against": runs_against,
                "hits_for": hits_for,
                "hits_against": hits_against,
                "errors_for": errors_for,
                "opponent_name": (
                    get_opponent_name(
                        game,
                        config.username,
                    )
                ),
                "opponent_team": (
                    get_opponent_team_name(
                        game,
                        config.username,
                    )
                ),
                "raw_game": game,
            }
        )

    if config.include_logs:
        log_stats = (
            fetch_live_log_stats_concurrently(
                games=recent_games,
                username=config.username,
                platform=config.platform,
                max_workers=config.log_workers,
            )
        )
    else:
        log_stats = {
            "logs_requested": False,
            "logs_fetched": 0,
            "logs_failed": 0,
            "batting_ab": 0,
            "batting_h": 0,
            "pitching_outs": 0,
            "pitching_ip": "0.0",
            "pitching_er": 0,
            "batting_average": None,
            "era": None,
            "worker_count": 0,
        }

    return {
        "username": config.username,
        "platform": config.platform,
        "mode": config.mode,
        "pages_fetched": pages_fetched,
        "games_found_total": len(all_games),
        "non_cpu_games_found": len(
            non_cpu_games
        ),
        "human_games_found": len(
            human_games
        ),
        "cpu_games_removed": (
            len(all_games)
            - len(non_cpu_games)
        ),
        "skipped_unattributable_games": (
            skipped_unattributable_games
        ),
        "recent_games_analyzed": len(
            recent_games
        ),
        "record": {
            "wins": wins,
            "losses": losses,
            "unknown_results": (
                unknown_results
            ),
            "win_pct": (
                round(
                    wins / (wins + losses),
                    3,
                )
                if (wins + losses) > 0
                else None
            ),
        },
        "averages_from_game_history": {
            "runs_scored_per_game": average(
                runs_scored_values
            ),
            "runs_allowed_per_game": average(
                runs_allowed_values
            ),
            "hits_for_per_game": average(
                hits_for_values
            ),
            "hits_allowed_per_game": average(
                hits_allowed_values
            ),
            "errors_per_game": average(
                errors_for_values
            ),
        },
        "advanced_from_game_logs": log_stats,
        "games": game_rows,
    }


def average(
    values: List[int],
) -> Optional[float]:
    if not values:
        return None

    return round(
        sum(values) / len(values),
        2,
    )


def print_live_scout_report(
    report: Dict[str, Any],
) -> None:
    username = report["username"]
    record = report["record"]
    averages = report[
        "averages_from_game_history"
    ]
    advanced = report[
        "advanced_from_game_logs"
    ]

    console.print()
    console.print(
        f"[bold green]"
        f"Live Scout Report: {username}"
        f"[/bold green]"
    )
    console.print(
        f"[bold]Platform:[/bold] "
        f"{report['platform']}"
    )
    console.print(
        f"[bold]Mode:[/bold] "
        f"{report['mode']}"
    )
    console.print(
        f"[bold]Pages fetched:[/bold] "
        f"{report['pages_fetched']}"
    )
    console.print(
        f"[bold]Total games found:[/bold] "
        f"{report['games_found_total']}"
    )
    console.print(
        f"[bold]Non-CPU games found:[/bold] "
        f"{report['non_cpu_games_found']}"
    )
    console.print(
        f"[bold]CPU games removed:[/bold] "
        f"{report['cpu_games_removed']}"
    )
    console.print(
        f"[bold]Skipped unattributable "
        f"games:[/bold] "
        f"{report['skipped_unattributable_games']}"
    )
    console.print(
        f"[bold]Recent games analyzed:[/bold] "
        f"{report['recent_games_analyzed']}"
    )

    console.print()

    console.print(
        f"[bold]Recent Record:[/bold] "
        f"{record['wins']}-{record['losses']} "
        f"(Win%: {record['win_pct']})"
    )

    console.print(
        f"[bold]Runs/Game:[/bold] "
        f"{averages['runs_scored_per_game']} scored, "
        f"{averages['runs_allowed_per_game']} allowed"
    )

    console.print(
        f"[bold]Hits/Game:[/bold] "
        f"{averages['hits_for_per_game']} for, "
        f"{averages['hits_allowed_per_game']} allowed"
    )

    console.print(
        f"[bold]Errors/Game:[/bold] "
        f"{averages['errors_per_game']}"
    )

    if advanced["logs_requested"]:
        console.print()
        console.print(
            "[bold cyan]"
            "Advanced Stats From Game Logs"
            "[/bold cyan]"
        )
        console.print(
            f"Workers: "
            f"{advanced['worker_count']}"
        )
        console.print(
            f"Logs fetched: "
            f"{advanced['logs_fetched']}"
        )
        console.print(
            f"Logs failed: "
            f"{advanced['logs_failed']}"
        )
        console.print(
            f"Batting Average: "
            f"{advanced['batting_average']}"
        )
        console.print(
            f"Pitching IP: "
            f"{advanced['pitching_ip']}"
        )
        console.print(
            f"ERA: {advanced['era']}"
        )
    else:
        console.print()
        console.print(
            "[yellow]"
            "Batting average and ERA require "
            "--include-logs because they are "
            "not available directly from "
            "game_history."
            "[/yellow]"
        )

    console.print()

    table = Table(
        title=f"Recent Online Games for {username}"
    )

    table.add_column("Date")
    table.add_column(
        "Result",
        justify="center",
    )
    table.add_column("Opponent")
    table.add_column(
        "Score",
        justify="center",
    )
    table.add_column(
        "Hits",
        justify="center",
    )
    table.add_column("Game ID")

    for game in report["games"]:
        score = (
            f"{game['runs_for']}-"
            f"{game['runs_against']}"
        )

        hits = (
            f"{game['hits_for']}-"
            f"{game['hits_against']}"
        )

        table.add_row(
            str(game["display_date"] or ""),
            str(game["result"] or ""),
            str(game["opponent_name"] or ""),
            score,
            hits,
            str(game["id"] or ""),
        )

    console.print(table)


def save_live_scout_report(
    report: Dict[str, Any],
) -> str:
    safe_username = (
        report["username"]
        .replace("/", "_")
        .replace("\\", "_")
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    export_dir = EXPORT_DIR

    export_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        export_dir
        / (
            f"live_scout_"
            f"{safe_username}_"
            f"{timestamp}.json"
        )
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    return str(path)


def run_live_scout(
    username: str,
    platform: str = "psn",
    pages: int = 1,
    max_games: int = 25,
    include_logs: bool = False,
    export: bool = True,
    log_workers: int = 5,
) -> None:
    config = LiveScoutConfig(
        username=username,
        platform=platform,
        max_pages=pages,
        max_games=max_games,
        include_logs=include_logs,
        log_workers=log_workers,
    )

    report = build_live_scout_report(
        config
    )

    print_live_scout_report(
        report
    )

    if export:
        path = save_live_scout_report(
            report
        )

        console.print(
            f"[green]"
            f"Live scout report exported:"
            f"[/green] {path}"
        )