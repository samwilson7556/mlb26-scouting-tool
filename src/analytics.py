import sqlite3
from typing import Any, Dict, List, Optional

from .parser import get_user_side, safe_int


def _normalize_team_name(
    value: Any,
) -> str:
    return " ".join(
        str(value or "").split()
    ).casefold()


def _average(
    total: int,
    count: int,
) -> Optional[float]:
    if count <= 0:
        return None

    return round(
        total / count,
        2,
    )


def _load_recent_games_with_box_scores(
    conn: sqlite3.Connection,
    limit: int,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            id,
            display_date,
            home_full_name,
            away_full_name,
            home_name,
            away_name,
            opponent_name,
            opponent_team_name
        FROM games
        WHERE EXISTS (
            SELECT 1
            FROM team_box_scores AS tbs
            WHERE tbs.game_id = games.id
        )
        ORDER BY
            display_date DESC,
            id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def _load_recent_games_with_innings(
    conn: sqlite3.Connection,
    limit: int,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            id,
            display_date,
            home_full_name,
            away_full_name,
            home_name,
            away_name,
            opponent_name,
            opponent_team_name
        FROM games
        WHERE EXISTS (
            SELECT 1
            FROM game_innings AS gi
            WHERE gi.game_id = games.id
        )
        ORDER BY
            display_date DESC,
            id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def _load_team_box_scores(
    conn: sqlite3.Connection,
    game_ids: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    if not game_ids:
        return {}

    placeholders = ", ".join(
        "?"
        for _ in game_ids
    )

    rows = conn.execute(
        f"""
        SELECT
            game_id,
            team_name,
            batting_bb,
            batting_so
        FROM team_box_scores
        WHERE game_id IN ({placeholders})
        """,
        game_ids,
    ).fetchall()

    grouped: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    for row in rows:
        item = dict(row)
        grouped.setdefault(
            item["game_id"],
            [],
        ).append(item)

    return grouped


def _load_innings(
    conn: sqlite3.Connection,
    game_ids: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    if not game_ids:
        return {}

    placeholders = ", ".join(
        "?"
        for _ in game_ids
    )

    rows = conn.execute(
        f"""
        SELECT
            game_id,
            inning,
            home_runs,
            away_runs
        FROM game_innings
        WHERE game_id IN ({placeholders})
        ORDER BY
            game_id,
            inning
        """,
        game_ids,
    ).fetchall()

    grouped: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    for row in rows:
        item = dict(row)
        grouped.setdefault(
            item["game_id"],
            [],
        ).append(item)

    return grouped


def _find_team_box_score(
    rows: List[Dict[str, Any]],
    team_name: Any,
) -> Optional[Dict[str, Any]]:
    expected = _normalize_team_name(
        team_name
    )

    if not expected:
        return None

    for row in rows:
        if (
            _normalize_team_name(
                row.get("team_name")
            )
            == expected
        ):
            return row

    return None


def get_plate_discipline_trends(
    conn: sqlite3.Connection,
    username: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Return recent team-level walk and strikeout trends.

    The most recent `limit` games with parsed team box scores are considered.
    Returned game rows are chronological so they can be plotted directly.
    Games whose user side or team rows cannot be attributed safely are skipped.
    """
    games = (
        _load_recent_games_with_box_scores(
            conn,
            limit,
        )
    )

    box_scores = _load_team_box_scores(
        conn,
        [
            game["id"]
            for game in games
        ],
    )

    trend_rows: List[
        Dict[str, Any]
    ] = []

    for game in reversed(games):
        side = get_user_side(
            game,
            username,
        )

        if side not in {
            "home",
            "away",
        }:
            continue

        if side == "home":
            user_team_name = (
                game.get(
                    "home_full_name"
                )
            )
            opponent_team_name = (
                game.get(
                    "away_full_name"
                )
            )
        else:
            user_team_name = (
                game.get(
                    "away_full_name"
                )
            )
            opponent_team_name = (
                game.get(
                    "home_full_name"
                )
            )

        rows = box_scores.get(
            game["id"],
            [],
        )

        user_box = (
            _find_team_box_score(
                rows,
                user_team_name,
            )
        )
        opponent_box = (
            _find_team_box_score(
                rows,
                opponent_team_name,
            )
        )

        if (
            user_box is None
            or opponent_box is None
        ):
            continue

        user_bb = safe_int(
            user_box.get(
                "batting_bb"
            )
        )
        user_so = safe_int(
            user_box.get(
                "batting_so"
            )
        )
        opponent_bb = safe_int(
            opponent_box.get(
                "batting_bb"
            )
        )
        opponent_so = safe_int(
            opponent_box.get(
                "batting_so"
            )
        )

        if None in {
            user_bb,
            user_so,
            opponent_bb,
            opponent_so,
        }:
            continue

        trend_rows.append(
            {
                "game_id": game["id"],
                "display_date": (
                    game.get(
                        "display_date"
                    )
                ),
                "opponent_name": (
                    game.get(
                        "opponent_name"
                    )
                ),
                "opponent_team_name": (
                    game.get(
                        "opponent_team_name"
                    )
                ),
                "user_side": side,
                "user_walks": user_bb,
                "user_strikeouts": (
                    user_so
                ),
                "opponent_walks": (
                    opponent_bb
                ),
                "opponent_strikeouts": (
                    opponent_so
                ),
            }
        )

    game_count = len(
        trend_rows
    )

    user_walks = sum(
        row["user_walks"]
        for row in trend_rows
    )
    user_strikeouts = sum(
        row["user_strikeouts"]
        for row in trend_rows
    )
    opponent_walks = sum(
        row["opponent_walks"]
        for row in trend_rows
    )
    opponent_strikeouts = sum(
        row["opponent_strikeouts"]
        for row in trend_rows
    )

    return {
        "games_included": game_count,
        "summary": {
            "user_walks": user_walks,
            "user_strikeouts": (
                user_strikeouts
            ),
            "opponent_walks": (
                opponent_walks
            ),
            "opponent_strikeouts": (
                opponent_strikeouts
            ),
            "user_walks_per_game": (
                _average(
                    user_walks,
                    game_count,
                )
            ),
            "user_strikeouts_per_game": (
                _average(
                    user_strikeouts,
                    game_count,
                )
            ),
            "opponent_walks_per_game": (
                _average(
                    opponent_walks,
                    game_count,
                )
            ),
            "opponent_strikeouts_per_game": (
                _average(
                    opponent_strikeouts,
                    game_count,
                )
            ),
        },
        "games": trend_rows,
    }


def get_inning_scoring_tendencies(
    conn: sqlite3.Connection,
    username: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Aggregate user/opponent scoring by inning over the most recent games with
    structured line-score rows.

    Runs are averaged only across observed half-innings for each side.
    This keeps unplayed bottom halves and source rows with unavailable
    extra-inning scoring values from being silently treated as zero runs.
    """
    games = (
        _load_recent_games_with_innings(
            conn,
            limit,
        )
    )

    innings_by_game = _load_innings(
        conn,
        [
            game["id"]
            for game in games
        ],
    )

    aggregates: Dict[
        int,
        Dict[str, int],
    ] = {}

    games_included = 0

    for game in games:
        side = get_user_side(
            game,
            username,
        )

        if side not in {
            "home",
            "away",
        }:
            continue

        game_innings = (
            innings_by_game.get(
                game["id"],
                [],
            )
        )

        if not game_innings:
            continue

        games_included += 1

        for inning_row in game_innings:
            inning = safe_int(
                inning_row.get(
                    "inning"
                )
            )

            if inning is None:
                continue

            home_runs = safe_int(
                inning_row.get(
                    "home_runs"
                )
            )
            away_runs = safe_int(
                inning_row.get(
                    "away_runs"
                )
            )

            if side == "home":
                user_runs = home_runs
                opponent_runs = away_runs
            else:
                user_runs = away_runs
                opponent_runs = home_runs

            bucket = (
                aggregates.setdefault(
                    inning,
                    {
                        "games": 0,
                        "user_runs": 0,
                        "opponent_runs": 0,
                        "user_innings_observed": 0,
                        "opponent_innings_observed": 0,
                    },
                )
            )

            bucket["games"] += 1

            if user_runs is not None:
                bucket["user_runs"] += (
                    user_runs
                )
                bucket[
                    "user_innings_observed"
                ] += 1

            if opponent_runs is not None:
                bucket[
                    "opponent_runs"
                ] += opponent_runs
                bucket[
                    "opponent_innings_observed"
                ] += 1

    inning_rows = []

    for inning in sorted(
        aggregates
    ):
        bucket = aggregates[
            inning
        ]
        games_reaching = (
            bucket["games"]
        )

        user_observed = (
            bucket[
                "user_innings_observed"
            ]
        )
        opponent_observed = (
            bucket[
                "opponent_innings_observed"
            ]
        )

        user_per_observed_inning = (
            _average(
                bucket["user_runs"],
                user_observed,
            )
        )
        opponent_per_observed_inning = (
            _average(
                bucket[
                    "opponent_runs"
                ],
                opponent_observed,
            )
        )

        if (
            user_per_observed_inning
            is None
            or opponent_per_observed_inning
            is None
        ):
            run_diff = None
        else:
            run_diff = round(
                user_per_observed_inning
                - opponent_per_observed_inning,
                2,
            )

        inning_rows.append(
            {
                "inning": inning,
                "games_reaching_inning": (
                    games_reaching
                ),
                "user_innings_observed": (
                    user_observed
                ),
                "opponent_innings_observed": (
                    opponent_observed
                ),
                "user_runs": (
                    bucket["user_runs"]
                ),
                "opponent_runs": (
                    bucket[
                        "opponent_runs"
                    ]
                ),
                "user_runs_per_observed_inning": (
                    user_per_observed_inning
                ),
                "opponent_runs_per_observed_inning": (
                    opponent_per_observed_inning
                ),
                "run_diff_per_observed_inning": (
                    run_diff
                ),
            }
        )

    return {
        "games_included": (
            games_included
        ),
        "innings": inning_rows,
    }


def get_scouting_trends(
    conn: sqlite3.Connection,
    username: str,
    limit: int = 20,
) -> Dict[str, Any]:
    return {
        "limit": limit,
        "plate_discipline": (
            get_plate_discipline_trends(
                conn,
                username,
                limit,
            )
        ),
        "inning_scoring": (
            get_inning_scoring_tendencies(
                conn,
                username,
                limit,
            )
        ),
    }
