import json
import sqlite3
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

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
    innings_pitched_to_outs,
    is_cpu_game,
    parse_display_date,
    safe_float,
    safe_int,
    sum_csv_ints,
)
from .play_by_play import parse_game_log_text


console = Console()


def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 MLB26 Personal Game Analyzer",
            "Accept": "application/json,*/*",
        }
    )

    return session


def fetch_json(
    session: requests.Session,
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError(
            "Expected MLBTS API response to be a JSON object."
        )

    return payload


def fetch_game_history(
    session: requests.Session,
) -> List[Dict[str, Any]]:
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

    total_pages = int(
        first_page.get("total_pages", 1)
    )

    first_page_games = first_page.get(
        "game_history",
        [],
    )

    if not isinstance(first_page_games, list):
        first_page_games = []

    all_games.extend(first_page_games)

    console.print(
        f"[bold green]"
        f"Found {total_pages} total page(s)."
        f"[/bold green]"
    )

    console.print(
        f"Fetched page 1/{total_pages}: "
        f"{len(first_page_games)} games"
    )

    for page in range(
        2,
        total_pages + 1,
    ):
        time.sleep(
            REQUEST_DELAY_SECONDS
        )

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

        page_games = page_data.get(
            "game_history",
            [],
        )

        if not isinstance(page_games, list):
            page_games = []

        all_games.extend(page_games)

        console.print(
            f"Fetched page {page}/{total_pages}: "
            f"{len(page_games)} games"
        )

    return all_games


def save_game_history(
    conn: sqlite3.Connection,
    games: List[Dict[str, Any]],
) -> None:
    for game in games:
        conn.execute(
            """
            INSERT INTO games (
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
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(id) DO UPDATE SET
                display_date = excluded.display_date,
                game_mode = excluded.game_mode,
                home_full_name = excluded.home_full_name,
                away_full_name = excluded.away_full_name,
                home_name = excluded.home_name,
                away_name = excluded.away_name,
                home_runs = excluded.home_runs,
                away_runs = excluded.away_runs,
                home_hits = excluded.home_hits,
                away_hits = excluded.away_hits,
                home_errors = excluded.home_errors,
                away_errors = excluded.away_errors,
                user_result = excluded.user_result,
                opponent_name = excluded.opponent_name,
                opponent_team_name = excluded.opponent_team_name,
                raw_game_history_json = excluded.raw_game_history_json
            """,
            (
                game.get("id"),
                parse_display_date(
                    game.get(
                        "display_date",
                        "",
                    )
                ),
                game.get("game_mode"),
                game.get("home_full_name"),
                game.get("away_full_name"),
                clean_username(
                    game.get(
                        "home_name",
                        "",
                    )
                ),
                clean_username(
                    game.get(
                        "away_name",
                        "",
                    )
                ),
                safe_int(
                    game.get("home_runs")
                ),
                safe_int(
                    game.get("away_runs")
                ),
                safe_int(
                    game.get("home_hits")
                ),
                safe_int(
                    game.get("away_hits")
                ),
                safe_int(
                    game.get("home_errors")
                ),
                safe_int(
                    game.get("away_errors")
                ),
                get_user_result(
                    game,
                    USERNAME,
                ),
                get_opponent_name(
                    game,
                    USERNAME,
                ),
                get_opponent_team_name(
                    game,
                    USERNAME,
                ),
                json.dumps(
                    game,
                    ensure_ascii=False,
                ),
            ),
        )

    conn.commit()


def export_human_games(
    games: List[Dict[str, Any]],
) -> None:
    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    export_path = (
        EXPORT_DIR
        / "human_only_game_history.json"
    )

    games_sorted = sorted(
        games,
        key=lambda game: (
            parse_display_date(
                game.get(
                    "display_date",
                    "",
                )
            )
            or ""
        ),
        reverse=True,
    )

    output = {
        "username": USERNAME,
        "platform": PLATFORM,
        "mode": MODE,
        "total_games": len(
            games_sorted
        ),
        "filter_applied": (
            "Removed games where "
            'home_full_name or away_full_name '
            'equals "CPU"'
        ),
        "game_history": games_sorted,
    }

    with export_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    console.print(
        f"[green]"
        f"Exported human-only game history:"
        f"[/green] {export_path}"
    )


def get_unfetched_game_ids(
    conn: sqlite3.Connection,
) -> List[str]:
    """
    Return games that need a game-log request.

    Games with no stored response are eligible. Generic api_error responses
    are also retryable because they may represent transient MLBTS failures.

    Successful logs, identity mismatches, and game-not-found responses are
    treated as terminal and are not requested again automatically.
    """
    rows = conn.execute(
        """
        SELECT g.id
        FROM games AS g
        LEFT JOIN game_logs AS gl
            ON g.id = gl.game_id
        WHERE gl.game_id IS NULL
           OR gl.api_status = 'api_error'
        ORDER BY g.display_date DESC
        """
    ).fetchall()

    return [
        row["id"]
        for row in rows
    ]


def fetch_game_log(
    session: requests.Session,
    game_id: str,
) -> Dict[str, Any]:
    """
    Fetch one game log using the current configured MLBTS identity.

    The MLBTS game-log API requires id, username, and platform.
    No alternate identity guessing is performed.
    """
    return fetch_json(
        session,
        GAME_LOG_URL,
        params={
            "id": game_id,
            "username": USERNAME,
            "platform": PLATFORM,
        },
    )


def classify_game_log_response(
    game_log: Dict[str, Any],
) -> str:
    if "error" not in game_log:
        return "ok"

    error = str(
        game_log.get("error", "")
    ).strip().lower()

    if (
        "username and platform"
        in error
        and "do not match"
        in error
    ):
        return "identity_mismatch"

    if "game not found" in error:
        return "not_found"

    return "api_error"


def get_existing_game_log_status(
    conn: sqlite3.Connection,
    game_id: str,
) -> Optional[str]:
    row = conn.execute(
        """
        SELECT api_status
        FROM game_logs
        WHERE game_id = ?
        """,
        (game_id,),
    ).fetchone()

    if row is None:
        return None

    return row["api_status"]


def save_raw_game_log(
    game_id: str,
    game_log: Dict[str, Any],
) -> bool:
    """
    Save the raw API response.

    If a successful raw log already exists, do not replace it with a later
    error response.
    """
    RAW_GAME_LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        RAW_GAME_LOG_DIR
        / f"{game_id}.json"
    )

    new_status = (
        classify_game_log_response(
            game_log
        )
    )

    if (
        path.exists()
        and new_status != "ok"
    ):
        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as f:
                existing_payload = (
                    json.load(f)
                )

            if (
                isinstance(
                    existing_payload,
                    dict,
                )
                and classify_game_log_response(
                    existing_payload
                )
                == "ok"
            ):
                return False

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            pass

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            game_log,
            f,
            indent=2,
            ensure_ascii=False,
        )

    return True


def save_game_log(
    conn: sqlite3.Connection,
    game_id: str,
    game_log: Dict[str, Any],
) -> str:
    """
    Persist a game-log API response.

    Successful stored logs are never downgraded to an error if MLBTS later
    refuses the same historical record.
    """
    api_status = (
        classify_game_log_response(
            game_log
        )
    )

    existing_status = (
        get_existing_game_log_status(
            conn,
            game_id,
        )
    )

    if (
        existing_status == "ok"
        and api_status != "ok"
    ):
        return "preserved_ok"

    sections = extract_game_sections(
        game_log
    )

    text_log = sections.get(
        "game_log",
        "",
    )

    if not isinstance(
        text_log,
        str,
    ):
        text_log = str(
            text_log or ""
        )

    conn.execute(
        """
        INSERT INTO game_logs (
            game_id,
            fetched_at,
            api_status,
            raw_game_log_json,
            raw_text_log
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(game_id) DO UPDATE SET
            fetched_at = excluded.fetched_at,
            api_status = excluded.api_status,
            raw_game_log_json = excluded.raw_game_log_json,
            raw_text_log = excluded.raw_text_log
        """,
        (
            game_id,
            datetime.now()
            .astimezone()
            .isoformat(
                sep=" ",
                timespec="seconds",
            ),
            api_status,
            json.dumps(
                game_log,
                ensure_ascii=False,
            ),
            text_log,
        ),
    )

    if api_status == "ok":
        save_box_score_sections(
            conn,
            game_id,
            sections,
        )

        save_normalized_game_sections(
            conn,
            game_id,
            sections,
        )

    conn.commit()

    return api_status


def save_box_score_sections(
    conn: sqlite3.Connection,
    game_id: str,
    sections: Dict[str, Any],
) -> None:
    """
    Replace parsed box-score rows for one game.

    Raw MLBTS innings-pitched notation is retained in the legacy REAL columns
    for display/backward compatibility. pitching_outs is the authoritative
    field for baseball calculations.
    """
    box_score = sections.get(
        "box_score",
        [],
    )

    if not isinstance(
        box_score,
        list,
    ):
        return

    conn.execute(
        """
        DELETE FROM team_box_scores
        WHERE game_id = ?
        """,
        (game_id,),
    )

    conn.execute(
        """
        DELETE FROM player_batting_stats
        WHERE game_id = ?
        """,
        (game_id,),
    )

    conn.execute(
        """
        DELETE FROM player_pitching_stats
        WHERE game_id = ?
        """,
        (game_id,),
    )

    for team in box_score:
        if not isinstance(
            team,
            dict,
        ):
            continue

        team_id = str(
            team.get(
                "team_id",
                "",
            )
        )

        team_name = team.get(
            "team_name",
            "",
        )

        team_details = team.get(
            team_id,
            {},
        )

        if not isinstance(
            team_details,
            dict,
        ):
            continue

        batting_totals = (
            team_details.get(
                "batting_totals",
                {},
            )
        )

        pitching_totals = (
            team_details.get(
                "pitching_totals",
                {},
            )
        )

        if not isinstance(
            batting_totals,
            dict,
        ):
            batting_totals = {}

        if not isinstance(
            pitching_totals,
            dict,
        ):
            pitching_totals = {}

        runs = sum_csv_ints(
            team.get(
                "r",
                "",
            )
        )

        hits = sum_csv_ints(
            team.get(
                "h",
                "",
            )
        )

        errors = sum_csv_ints(
            team.get(
                "e",
                "",
            )
        )

        pitching_ip_value = (
            pitching_totals.get("ip")
        )

        pitching_outs = (
            innings_pitched_to_outs(
                pitching_ip_value
            )
        )

        conn.execute(
            """
            INSERT INTO team_box_scores (
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
                pitching_outs,
                pitching_h,
                pitching_r,
                pitching_er,
                pitching_bb,
                pitching_so
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                game_id,
                team_id,
                team_name,
                runs,
                hits,
                errors,
                safe_int(
                    batting_totals.get(
                        "ab"
                    )
                ),
                safe_int(
                    batting_totals.get(
                        "r"
                    )
                ),
                safe_int(
                    batting_totals.get(
                        "h"
                    )
                ),
                safe_int(
                    batting_totals.get(
                        "rbi"
                    )
                ),
                safe_int(
                    batting_totals.get(
                        "bb"
                    )
                ),
                safe_int(
                    batting_totals.get(
                        "so"
                    )
                ),
                safe_float(
                    pitching_ip_value
                ),
                pitching_outs,
                safe_int(
                    pitching_totals.get(
                        "h"
                    )
                ),
                safe_int(
                    pitching_totals.get(
                        "r"
                    )
                ),
                safe_int(
                    pitching_totals.get(
                        "er"
                    )
                ),
                safe_int(
                    pitching_totals.get(
                        "bb"
                    )
                ),
                safe_int(
                    pitching_totals.get(
                        "so"
                    )
                ),
            ),
        )

        batting_stats = (
            team_details.get(
                "batting_stats",
                [],
            )
        )

        if not isinstance(
            batting_stats,
            list,
        ):
            batting_stats = []

        for batter in batting_stats:
            if not isinstance(
                batter,
                dict,
            ):
                continue

            conn.execute(
                """
                INSERT INTO player_batting_stats (
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
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    game_id,
                    team_id,
                    team_name,
                    batter.get(
                        "player_name"
                    ),
                    safe_int(
                        batter.get("ab")
                    ),
                    safe_int(
                        batter.get("r")
                    ),
                    safe_int(
                        batter.get("h")
                    ),
                    safe_int(
                        batter.get("rbi")
                    ),
                    safe_int(
                        batter.get("bb")
                    ),
                    safe_int(
                        batter.get("so")
                    ),
                    safe_int(
                        batter.get(
                            "doubles"
                        )
                    ),
                    safe_int(
                        batter.get(
                            "triples"
                        )
                    ),
                    safe_int(
                        batter.get("hr")
                    ),
                    safe_int(
                        batter.get("sb")
                    ),
                    safe_int(
                        batter.get("cs")
                    ),
                ),
            )

        pitching_stats = (
            team_details.get(
                "pitching_stats",
                [],
            )
        )

        if not isinstance(
            pitching_stats,
            list,
        ):
            pitching_stats = []

        for pitcher in pitching_stats:
            if not isinstance(
                pitcher,
                dict,
            ):
                continue

            pitcher_ip_value = (
                pitcher.get("ip")
            )

            pitcher_outs = (
                innings_pitched_to_outs(
                    pitcher_ip_value
                )
            )

            conn.execute(
                """
                INSERT INTO player_pitching_stats (
                    game_id,
                    team_id,
                    team_name,
                    player_name,
                    ip,
                    pitching_outs,
                    h,
                    r,
                    er,
                    bb,
                    so,
                    win,
                    loss,
                    save
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    game_id,
                    team_id,
                    team_name,
                    pitcher.get(
                        "player_name"
                    ),
                    safe_float(
                        pitcher_ip_value
                    ),
                    pitcher_outs,
                    safe_int(
                        pitcher.get("h")
                    ),
                    safe_int(
                        pitcher.get("r")
                    ),
                    safe_int(
                        pitcher.get("er")
                    ),
                    safe_int(
                        pitcher.get("bb")
                    ),
                    safe_int(
                        pitcher.get("so")
                    ),
                    safe_int(
                        pitcher.get("win")
                    ),
                    safe_int(
                        pitcher.get("loss")
                    ),
                    safe_int(
                        pitcher.get("save")
                    ),
                ),
            )



def _normalize_team_label(
    value: Any,
) -> str:
    return " ".join(
        str(value or "").split()
    ).casefold()


def infer_batting_side(
    line_score: Dict[str, Any],
    batting_team_name: Any,
) -> str:
    if not isinstance(
        line_score,
        dict,
    ):
        return "unknown"

    batting_team = (
        _normalize_team_label(
            batting_team_name
        )
    )

    if not batting_team:
        return "unknown"

    home_team = (
        _normalize_team_label(
            line_score.get(
                "home_full_name"
            )
        )
    )

    away_team = (
        _normalize_team_label(
            line_score.get(
                "away_full_name"
            )
        )
    )

    if (
        home_team
        and batting_team == home_team
    ):
        return "home"

    if (
        away_team
        and batting_team == away_team
    ):
        return "away"

    return "unknown"


def save_inning_sections(
    conn: sqlite3.Connection,
    game_id: str,
    sections: Dict[str, Any],
) -> None:
    """
    Replace inning-by-inning run rows for one game.

    The structured line_score is the baseline. MLBTS can publish stale or
    incomplete per-inning values, so text-log inning summaries may repair
    one side only when their summed runs exactly match that side's final
    score.
    """
    conn.execute(
        """
        DELETE FROM game_innings
        WHERE game_id = ?
        """,
        (game_id,),
    )

    line_score = sections.get(
        "line_score",
        {},
    )

    if not isinstance(
        line_score,
        dict,
    ):
        line_score = {}

    innings = safe_int(
        line_score.get("innings")
    )

    inning_runs = {}

    if (
        innings is not None
        and innings > 0
    ):
        for inning in range(
            1,
            innings + 1,
        ):
            inning_runs[inning] = {
                "home": safe_int(
                    line_score.get(
                        f"home_runs_{inning}"
                    )
                ),
                "away": safe_int(
                    line_score.get(
                        f"away_runs_{inning}"
                    )
                ),
            }

    text_log = sections.get(
        "game_log",
        "",
    )

    if (
        isinstance(text_log, str)
        and text_log.strip()
    ):
        parsed = parse_game_log_text(
            text_log
        )

        text_rows = {
            "home": [],
            "away": [],
        }

        for parsed_inning in parsed[
            "innings"
        ]:
            inning = safe_int(
                parsed_inning.get(
                    "inning"
                )
            )
            summary = parsed_inning.get(
                "summary"
            )

            if (
                inning is None
                or inning <= 0
                or not isinstance(
                    summary,
                    dict,
                )
            ):
                continue

            batting_side = (
                infer_batting_side(
                    line_score,
                    parsed_inning.get(
                        "batting_team"
                    ),
                )
            )

            if batting_side not in {
                "home",
                "away",
            }:
                continue

            runs = safe_int(
                summary.get("runs")
            )

            if runs is None:
                continue

            text_rows[
                batting_side
            ].append(
                (inning, runs)
            )

        for side in (
            "home",
            "away",
        ):
            rows = text_rows[side]

            if not rows:
                continue

            final_total = safe_int(
                line_score.get(
                    f"{side}_runs"
                )
            )

            if final_total is None:
                continue

            text_total = sum(
                runs
                for _, runs in rows
            )

            if text_total != final_total:
                continue

            for inning, runs in rows:
                inning_runs.setdefault(
                    inning,
                    {
                        "home": None,
                        "away": None,
                    },
                )

                inning_runs[
                    inning
                ][side] = runs

    for inning in sorted(
        inning_runs
    ):
        conn.execute(
            """
            INSERT INTO game_innings (
                game_id,
                inning,
                home_runs,
                away_runs
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                game_id,
                inning,
                inning_runs[
                    inning
                ]["home"],
                inning_runs[
                    inning
                ]["away"],
            ),
        )


def save_play_by_play_sections(
    conn: sqlite3.Connection,
    game_id: str,
    sections: Dict[str, Any],
) -> None:
    """
    Replace normalized text-game-log events for one game.

    MLBTS text logs may contain one or both batting sides. batting_side
    is inferred conservatively from line_score team names, and unknown
    attribution is retained as "unknown".
    """
    conn.execute(
        """
        DELETE FROM game_events
        WHERE game_id = ?
        """,
        (game_id,),
    )

    text_log = sections.get(
        "game_log",
        "",
    )

    if not isinstance(
        text_log,
        str,
    ):
        return

    if not text_log.strip():
        return

    line_score = sections.get(
        "line_score",
        {},
    )

    if not isinstance(
        line_score,
        dict,
    ):
        line_score = {}

    parsed = parse_game_log_text(
        text_log
    )

    for event in parsed["events"]:
        batting_team_name = (
            event.get(
                "batting_team"
            )
        )

        batting_side = (
            infer_batting_side(
                line_score,
                batting_team_name,
            )
        )

        conn.execute(
            """
            INSERT INTO game_events (
                game_id,
                source_index,
                inning,
                batting_side,
                batting_team_name,
                event_type,
                player_name,
                pitcher_name,
                pitcher_is_starter,
                related_player_name,
                raw_text,
                is_plate_appearance,
                is_hit,
                is_out,
                hit_bases,
                outs_recorded,
                fielding_code,
                destination_base,
                cause,
                strikeout_type,
                home_run_distance_ft,
                terminal_pitch_type,
                terminal_pitch_location,
                secondary_out,
                parser_version
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?
            )
            """,
            (
                game_id,
                event.get(
                    "source_index"
                ),
                event.get("inning"),
                batting_side,
                batting_team_name,
                event.get(
                    "event_type"
                ),
                event.get(
                    "player_name"
                ),
                event.get(
                    "pitcher_name"
                ),
                (
                    int(
                        bool(
                            event.get(
                                "pitcher_is_starter"
                            )
                        )
                    )
                    if event.get(
                        "pitcher_name"
                    )
                    else None
                ),
                event.get(
                    "related_player_name"
                ),
                event.get(
                    "raw_text",
                    "",
                ),
                int(
                    bool(
                        event.get(
                            "is_plate_appearance"
                        )
                    )
                ),
                int(
                    bool(
                        event.get(
                            "is_hit"
                        )
                    )
                ),
                int(
                    bool(
                        event.get(
                            "is_out"
                        )
                    )
                ),
                event.get(
                    "hit_bases"
                ),
                event.get(
                    "outs_recorded"
                ),
                event.get(
                    "fielding_code"
                ),
                event.get(
                    "destination_base"
                ),
                event.get("cause"),
                event.get(
                    "strikeout_type"
                ),
                event.get(
                    "home_run_distance_ft"
                ),
                event.get(
                    "terminal_pitch_type"
                ),
                event.get(
                    "terminal_pitch_location"
                ),
                int(
                    bool(
                        event.get(
                            "secondary_out"
                        )
                    )
                ),
                5,
            ),
        )


def save_normalized_game_sections(
    conn: sqlite3.Connection,
    game_id: str,
    sections: Dict[str, Any],
) -> None:
    save_inning_sections(
        conn,
        game_id,
        sections,
    )

    save_play_by_play_sections(
        conn,
        game_id,
        sections,
    )


def get_game_ids_needing_pitching_outs_backfill(
    conn: sqlite3.Connection,
) -> List[str]:
    """
    Return successful stored logs whose parsed pitching rows predate
    the pitching_outs migration.
    """
    rows = conn.execute(
        """
        SELECT DISTINCT
            gl.game_id
        FROM game_logs AS gl
        WHERE gl.api_status = 'ok'
          AND (
              EXISTS (
                  SELECT 1
                  FROM team_box_scores AS tbs
                  WHERE tbs.game_id = gl.game_id
                    AND tbs.pitching_ip IS NOT NULL
                    AND tbs.pitching_outs IS NULL
              )
              OR EXISTS (
                  SELECT 1
                  FROM player_pitching_stats AS pps
                  WHERE pps.game_id = gl.game_id
                    AND pps.ip IS NOT NULL
                    AND pps.pitching_outs IS NULL
              )
          )
        ORDER BY gl.game_id
        """
    ).fetchall()

    return [
        row["game_id"]
        for row in rows
    ]


def reparse_stored_game_logs(
    conn: sqlite3.Connection,
    game_ids: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Rebuild parsed statistics using already-stored successful raw game logs.

    If game_ids is provided, only those successful stored logs are reparsed.
    This function performs no network requests.
    """
    params: List[Any] = []
    where_sql = (
        "WHERE api_status = 'ok'"
    )

    if game_ids is not None:
        if not game_ids:
            return {
                "found": 0,
                "reparsed": 0,
                "failed": 0,
            }

        placeholders = ", ".join(
            "?"
            for _ in game_ids
        )

        where_sql += (
            f" AND game_id IN "
            f"({placeholders})"
        )

        params.extend(
            game_ids
        )

    rows = conn.execute(
        f"""
        SELECT
            game_id,
            raw_game_log_json
        FROM game_logs
        {where_sql}
        ORDER BY game_id
        """,
        params,
    ).fetchall()

    summary = {
        "found": len(rows),
        "reparsed": 0,
        "failed": 0,
    }

    for row in rows:
        game_id = row["game_id"]

        try:
            payload = json.loads(
                row["raw_game_log_json"]
            )

            if not isinstance(
                payload,
                dict,
            ):
                raise ValueError(
                    "Stored game log is not a JSON object."
                )

            sections = extract_game_sections(
                payload
            )

            save_box_score_sections(
                conn,
                game_id,
                sections,
            )

            save_normalized_game_sections(
                conn,
                game_id,
                sections,
            )

            summary["reparsed"] += 1

        except Exception as exc:
            summary["failed"] += 1

            console.print(
                f"[red]"
                f"Failed to reparse stored game "
                f"{game_id}: {exc}"
                f"[/red]"
            )

    conn.commit()

    return summary


def backfill_missing_pitching_outs(
    conn: sqlite3.Connection,
) -> Dict[str, int]:
    """
    Reparse only legacy successful game logs whose parsed pitching data has
    innings pitched but no pitching_outs value.

    No MLBTS requests are made; the stored raw JSON is the source of truth.
    """
    game_ids = (
        get_game_ids_needing_pitching_outs_backfill(
            conn
        )
    )

    return reparse_stored_game_logs(
        conn,
        game_ids=game_ids,
    )


def sync_game_history(
    conn: sqlite3.Connection,
) -> List[Dict[str, Any]]:
    session = create_session()

    all_games = fetch_game_history(
        session
    )

    human_games = [
        game
        for game in all_games
        if not is_cpu_game(game)
    ]

    human_games.sort(
        key=lambda game: (
            parse_display_date(
                game.get(
                    "display_date",
                    "",
                )
            )
            or ""
        ),
        reverse=True,
    )

    console.print(
        f"[bold]Total games found:[/bold] "
        f"{len(all_games)}"
    )

    console.print(
        f"[bold]Human-only games:[/bold] "
        f"{len(human_games)}"
    )

    console.print(
        f"[bold]CPU games removed:[/bold] "
        f"{len(all_games) - len(human_games)}"
    )

    save_game_history(
        conn,
        human_games,
    )

    export_human_games(
        human_games
    )

    return human_games


def sync_game_logs(
    conn: sqlite3.Connection,
    progress_callback: Optional[
        Callable[
            [Dict[str, Any]],
            None,
        ]
    ] = None,
) -> Dict[str, int]:
    session = create_session()

    game_ids = get_unfetched_game_ids(
        conn
    )

    summary = {
        "requested": len(game_ids),
        "ok": 0,
        "identity_mismatch": 0,
        "not_found": 0,
        "api_error": 0,
        "request_failed": 0,
        "preserved_ok": 0,
    }

    console.print(
        f"[bold]Game logs to fetch:[/bold] "
        f"{len(game_ids)}"
    )

    if progress_callback:
        progress_callback(
            {
                "current": 0,
                "total": len(game_ids),
                "game_id": None,
                "summary": dict(summary),
            }
        )

    for index, game_id in enumerate(
        game_ids,
        start=1,
    ):
        console.print(
            f"[cyan]"
            f"[{index}/{len(game_ids)}] "
            f"Fetching game log {game_id}"
            f"[/cyan]"
        )

        try:
            time.sleep(
                REQUEST_DELAY_SECONDS
            )

            game_log = fetch_game_log(
                session,
                game_id,
            )

            status = (
                classify_game_log_response(
                    game_log
                )
            )

            save_raw_game_log(
                game_id,
                game_log,
            )

            saved_status = save_game_log(
                conn,
                game_id,
                game_log,
            )

            if saved_status == "preserved_ok":
                summary["preserved_ok"] += 1

                console.print(
                    "[yellow]"
                    "Existing successful log preserved."
                    "[/yellow]"
                )

                if progress_callback:
                    progress_callback(
                        {
                            "current": index,
                            "total": len(game_ids),
                            "game_id": game_id,
                            "summary": dict(summary),
                        }
                    )

                continue

            summary[status] += 1

            if status == "ok":
                console.print(
                    "[green]Saved.[/green]"
                )

            elif status == "identity_mismatch":
                console.print(
                    f"[yellow]"
                    f"Stored identity mismatch for "
                    f"{game_id}; it will not be "
                    f"retried automatically."
                    f"[/yellow]"
                )

            elif status == "not_found":
                console.print(
                    f"[yellow]"
                    f"Stored game-not-found response "
                    f"for {game_id}; it will not be "
                    f"retried automatically."
                    f"[/yellow]"
                )

            else:
                console.print(
                    f"[yellow]"
                    f"Stored MLBTS API error for "
                    f"{game_id}: "
                    f"{game_log.get('error')}"
                    f"[/yellow]"
                )

        except Exception as exc:
            summary[
                "request_failed"
            ] += 1

            console.print(
                f"[red]"
                f"Request failed for "
                f"{game_id}: {exc}"
                f"[/red]"
            )

        if progress_callback:
            progress_callback(
                {
                    "current": index,
                    "total": len(game_ids),
                    "game_id": game_id,
                    "summary": dict(summary),
                }
            )

    console.print()
    console.print(
        "[bold]Game-log sync summary[/bold]"
    )

    console.print(
        f"Requested: "
        f"{summary['requested']}"
    )
    console.print(
        f"Successful: "
        f"{summary['ok']}"
    )
    console.print(
        f"Identity mismatch: "
        f"{summary['identity_mismatch']}"
    )
    console.print(
        f"Not found: "
        f"{summary['not_found']}"
    )
    console.print(
        f"Other API errors: "
        f"{summary['api_error']}"
    )
    console.print(
        f"Request failures: "
        f"{summary['request_failed']}"
    )

    return summary
