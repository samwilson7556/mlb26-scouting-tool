import json
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from rich.console import Console

from .config import (
    EXPORT_DIR,
    GAME_HISTORY_URL,
    GAME_LOG_URL,
    MODE,
    PLATFORM,
    RAW_GAME_LOG_DIR,
    REQUEST_DELAY_SECONDS,
    USERNAME,
)
from .parser import (
    clean_username,
    extract_game_sections,
    get_opponent_name,
    get_opponent_team_name,
    get_user_result,
    is_cpu_game,
    parse_display_date,
    safe_float,
    safe_int,
    sum_csv_ints,
)


console = Console()


def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 MLB26 Personal Game Analyzer",
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


def fetch_game_history(session: requests.Session) -> List[Dict[str, Any]]:
    all_games: List[Dict[str, Any]] = []

    first_page = fetch_json(
        session,
        GAME_HISTORY_URL,
        params={
            "page": 1,
            "username": USERNAME,
            "platform": PLATFORM,
            "mode": MODE,
        },
    )

    total_pages = int(first_page.get("total_pages", 1))
    first_page_games = first_page.get("game_history", [])

    all_games.extend(first_page_games)

    console.print(f"[bold green]Found {total_pages} total page(s).[/bold green]")
    console.print(f"Fetched page 1/{total_pages}: {len(first_page_games)} games")

    for page in range(2, total_pages + 1):
        time.sleep(REQUEST_DELAY_SECONDS)

        page_data = fetch_json(
            session,
            GAME_HISTORY_URL,
            params={
                "page": page,
                "username": USERNAME,
                "platform": PLATFORM,
                "mode": MODE,
            },
        )

        page_games = page_data.get("game_history", [])
        all_games.extend(page_games)

        console.print(f"Fetched page {page}/{total_pages}: {len(page_games)} games")

    return all_games


def save_game_history(conn: sqlite3.Connection, games: List[Dict[str, Any]]) -> None:
    for game in games:
        conn.execute(
            """
            INSERT OR REPLACE INTO games (
                id,
                display_date,
                game_mode,
                home_full_name,
                away_full_name,
                home_name,
                away_name,
                home_runs,
                away_runs,
                home_hits,
                away_hits,
                home_errors,
                away_errors,
                user_result,
                opponent_name,
                opponent_team_name,
                raw_game_history_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game.get("id"),
                parse_display_date(game.get("display_date", "")),
                game.get("game_mode"),
                game.get("home_full_name"),
                game.get("away_full_name"),
                clean_username(game.get("home_name", "")),
                clean_username(game.get("away_name", "")),
                safe_int(game.get("home_runs")),
                safe_int(game.get("away_runs")),
                safe_int(game.get("home_hits")),
                safe_int(game.get("away_hits")),
                safe_int(game.get("home_errors")),
                safe_int(game.get("away_errors")),
                get_user_result(game, USERNAME),
                get_opponent_name(game, USERNAME),
                get_opponent_team_name(game, USERNAME),
                json.dumps(game, ensure_ascii=False),
            ),
        )

    conn.commit()


def export_human_games(games: List[Dict[str, Any]]) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    export_path = EXPORT_DIR / "human_only_game_history.json"

    games_sorted = sorted(
        games,
        key=lambda game: parse_display_date(game.get("display_date", "")) or "",
        reverse=True,
    )

    output = {
        "username": USERNAME,
        "platform": PLATFORM,
        "mode": MODE,
        "total_games": len(games_sorted),
        "filter_applied": 'Removed games where home_full_name or away_full_name equals "CPU"',
        "game_history": games_sorted,
    }

    with export_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    console.print(f"[green]Exported human-only game history:[/green] {export_path}")


def get_unfetched_game_ids(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        """
        SELECT g.id
        FROM games g
        LEFT JOIN game_logs gl ON g.id = gl.game_id
        WHERE gl.game_id IS NULL
        ORDER BY g.display_date DESC
        """
    ).fetchall()

    return [row["id"] for row in rows]


def fetch_game_log(
    session: requests.Session,
    game_id: str,
) -> Dict[str, Any]:
    return fetch_json(
        session,
        GAME_LOG_URL,
        params={
            "id": game_id,
            "username": USERNAME,
            "platform": PLATFORM,
        },
    )

def save_raw_game_log(game_id: str, game_log: Dict[str, Any]) -> None:
    RAW_GAME_LOG_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_GAME_LOG_DIR / f"{game_id}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(game_log, f, indent=2, ensure_ascii=False)


def save_game_log(
    conn: sqlite3.Connection,
    game_id: str,
    game_log: Dict[str, Any],
) -> None:
    sections = extract_game_sections(game_log)
    text_log = sections.get("game_log", "")

    api_status = "error" if "error" in game_log else "ok"

    conn.execute(
        """
        INSERT OR REPLACE INTO game_logs (
            game_id,
            fetched_at,
            api_status,
            raw_game_log_json,
            raw_text_log
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            game_id,
            datetime.now().isoformat(sep=" "),
            api_status,
            json.dumps(game_log, ensure_ascii=False),
            text_log,
        ),
    )

    if api_status == "ok":
        save_box_score_sections(conn, game_id, sections)

    conn.commit()


def save_box_score_sections(
    conn: sqlite3.Connection,
    game_id: str,
    sections: Dict[str, Any],
) -> None:
    box_score = sections.get("box_score", [])

    if not isinstance(box_score, list):
        return

    for team in box_score:
        if not isinstance(team, dict):
            continue

        team_id = str(team.get("team_id", ""))
        team_name = team.get("team_name", "")
        team_details = team.get(team_id, {})

        if not isinstance(team_details, dict):
            continue

        batting_totals = team_details.get("batting_totals", {})
        pitching_totals = team_details.get("pitching_totals", {})

        runs = sum_csv_ints(team.get("r", ""))
        hits = sum_csv_ints(team.get("h", ""))
        errors = sum_csv_ints(team.get("e", ""))

        conn.execute(
            """
            INSERT OR REPLACE INTO team_box_scores (
                game_id,
                team_id,
                team_name,
                runs,
                hits,
                errors,
                batting_ab,
                batting_r,
                batting_h,
                batting_rbi,
                batting_bb,
                batting_so,
                pitching_ip,
                pitching_h,
                pitching_r,
                pitching_er,
                pitching_bb,
                pitching_so
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                team_id,
                team_name,
                runs,
                hits,
                errors,
                safe_int(batting_totals.get("ab")),
                safe_int(batting_totals.get("r")),
                safe_int(batting_totals.get("h")),
                safe_int(batting_totals.get("rbi")),
                safe_int(batting_totals.get("bb")),
                safe_int(batting_totals.get("so")),
                safe_float(pitching_totals.get("ip")),
                safe_int(pitching_totals.get("h")),
                safe_int(pitching_totals.get("r")),
                safe_int(pitching_totals.get("er")),
                safe_int(pitching_totals.get("bb")),
                safe_int(pitching_totals.get("so")),
            ),
        )

        for batter in team_details.get("batting_stats", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO player_batting_stats (
                    game_id,
                    team_id,
                    team_name,
                    player_name,
                    ab,
                    r,
                    h,
                    rbi,
                    bb,
                    so,
                    doubles,
                    triples,
                    hr,
                    sb,
                    cs
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    team_id,
                    team_name,
                    batter.get("player_name"),
                    safe_int(batter.get("ab")),
                    safe_int(batter.get("r")),
                    safe_int(batter.get("h")),
                    safe_int(batter.get("rbi")),
                    safe_int(batter.get("bb")),
                    safe_int(batter.get("so")),
                    safe_int(batter.get("doubles")),
                    safe_int(batter.get("triples")),
                    safe_int(batter.get("hr")),
                    safe_int(batter.get("sb")),
                    safe_int(batter.get("cs")),
                ),
            )

        for pitcher in team_details.get("pitching_stats", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO player_pitching_stats (
                    game_id,
                    team_id,
                    team_name,
                    player_name,
                    ip,
                    h,
                    r,
                    er,
                    bb,
                    so,
                    win,
                    loss,
                    save
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    team_id,
                    team_name,
                    pitcher.get("player_name"),
                    safe_float(pitcher.get("ip")),
                    safe_int(pitcher.get("h")),
                    safe_int(pitcher.get("r")),
                    safe_int(pitcher.get("er")),
                    safe_int(pitcher.get("bb")),
                    safe_int(pitcher.get("so")),
                    safe_int(pitcher.get("win")),
                    safe_int(pitcher.get("loss")),
                    safe_int(pitcher.get("save")),
                ),
            )


def sync_game_history(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    session = create_session()

    all_games = fetch_game_history(session)
    human_games = [game for game in all_games if not is_cpu_game(game)]

    human_games.sort(
        key=lambda game: parse_display_date(game.get("display_date", "")) or "",
        reverse=True,
    )

    console.print(f"[bold]Total games found:[/bold] {len(all_games)}")
    console.print(f"[bold]Human-only games:[/bold] {len(human_games)}")
    console.print(f"[bold]CPU games removed:[/bold] {len(all_games) - len(human_games)}")

    save_game_history(conn, human_games)
    export_human_games(human_games)

    return human_games


def sync_game_logs(conn: sqlite3.Connection) -> None:
    session = create_session()
    game_ids = get_unfetched_game_ids(conn)

    console.print(f"[bold]Game logs to fetch:[/bold] {len(game_ids)}")

    for index, game_id in enumerate(game_ids, start=1):
        console.print(f"[cyan][{index}/{len(game_ids)}] Fetching game log {game_id}[/cyan]")

        try:
            time.sleep(REQUEST_DELAY_SECONDS)

            game_log = fetch_game_log(session, game_id)

            save_raw_game_log(game_id, game_log)
            save_game_log(conn, game_id, game_log)

            if "error" in game_log:
                console.print(f"[red]Still returned error for {game_id}: {game_log}[/red]")
            else:
                console.print("[green]Saved.[/green]")

        except Exception as exc:
            console.print(f"[red]Failed to fetch/save game {game_id}: {exc}[/red]")