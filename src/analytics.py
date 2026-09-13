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


def _percentage(
    count: int,
    total: int,
) -> Optional[float]:
    if total <= 0:
        return None

    return round(
        (count / total) * 100,
        1,
    )


def _increment_category_count(
    counts: Dict[str, int],
    value: Any,
) -> None:
    normalized = " ".join(
        str(value or "").split()
    ).casefold()

    if not normalized:
        return

    counts[normalized] = (
        counts.get(
            normalized,
            0,
        )
        + 1
    )


def _category_breakdown(
    counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    total = sum(
        counts.values()
    )

    return [
        {
            "value": value,
            "count": count,
            "pct": _percentage(
                count,
                total,
            ),
        }
        for value, count in sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    ]


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


def _load_recent_games_with_events(
    conn: sqlite3.Connection,
    limit: int,
    opponent_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    normalized_opponent = (
        opponent_name.strip()
        if opponent_name
        and opponent_name.strip()
        else None
    )

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
            FROM game_events AS ge
            WHERE ge.game_id = games.id
        )
          AND (
              ? IS NULL
              OR LOWER(opponent_name) = LOWER(?)
          )
        ORDER BY
            display_date DESC,
            id DESC
        LIMIT ?
        """,
        (
            normalized_opponent,
            normalized_opponent,
            limit,
        ),
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def _load_game_events(
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
            source_index,
            batting_side,
            batting_team_name,
            event_type,
            player_name,
            is_plate_appearance,
            is_hit,
            hit_bases,
            cause,
            strikeout_type,
            terminal_pitch_type,
            terminal_pitch_location
        FROM game_events
        WHERE game_id IN ({placeholders})
        ORDER BY
            game_id,
            source_index
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


def get_player_event_analytics(
    conn: sqlite3.Connection,
    username: str,
    limit: int = 20,
    opponent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate normalized offensive events by player.

    The most recent `limit` games containing normalized game events are
    considered. When opponent_name is supplied, the opponent filter is
    applied before the limit so the window represents that opponent's
    most recent event-bearing games. Events are attributed to the
    configured user or opponent from the persisted batting_side plus
    get_user_side().

    User hitters are grouped by normalized player name so a custom-team
    rename does not split their history. Opponent hitters are grouped by
    opponent account plus normalized player name so unrelated opponents
    with the same displayed hitter name are never merged.

    Plate appearances come from the normalized is_plate_appearance flag.
    At-bats exclude walks, hit-by-pitches, sacrifice flies, and sacrifice
    bunts. Non-PA baserunning events are retained for runs, steals,
    caught-stealing, and pickoff totals.
    """
    games = _load_recent_games_with_events(
        conn,
        limit,
        opponent_name=opponent_name,
    )

    events_by_game = _load_game_events(
        conn,
        [
            game["id"]
            for game in games
        ],
    )

    player_buckets: Dict[
        str,
        Dict[Any, Dict[str, Any]],
    ] = {
        "user": {},
        "opponent": {},
    }

    games_included = 0

    tracked_non_pa_events = {
        "runner_scored",
        "stolen_base",
        "caught_stealing",
        "picked_off",
    }

    for game in games:
        user_side = get_user_side(
            game,
            username,
        )

        if user_side not in {
            "home",
            "away",
        }:
            continue

        games_included += 1

        for event in events_by_game.get(
            game["id"],
            [],
        ):
            batting_side = event.get(
                "batting_side"
            )

            if batting_side not in {
                "home",
                "away",
            }:
                continue

            is_plate_appearance = bool(
                safe_int(
                    event.get(
                        "is_plate_appearance"
                    )
                )
            )

            event_type = str(
                event.get("event_type")
                or ""
            )

            if (
                not is_plate_appearance
                and event_type
                not in tracked_non_pa_events
            ):
                continue

            player_name = " ".join(
                str(
                    event.get(
                        "player_name"
                    )
                    or ""
                ).split()
            )

            if not player_name:
                continue

            scope = (
                "user"
                if batting_side == user_side
                else "opponent"
            )

            team_name = (
                game.get(
                    f"{batting_side}_full_name"
                )
                or event.get(
                    "batting_team_name"
                )
                or "Unknown Team"
            )

            normalized_player_name = (
                player_name.casefold()
            )

            if scope == "user":
                key = (
                    normalized_player_name
                )
                opponent_name = None
            else:
                opponent_name = " ".join(
                    str(
                        game.get(
                            "opponent_name"
                        )
                        or ""
                    ).split()
                )

                opponent_identity = (
                    opponent_name.casefold()
                    if opponent_name
                    else (
                        str(
                            team_name
                        ).casefold()
                    )
                )

                key = (
                    opponent_identity,
                    normalized_player_name,
                )

            bucket = player_buckets[
                scope
            ].get(key)

            if bucket is None:
                bucket = {
                    "player_name": (
                        player_name
                    ),
                    "team_name": (
                        str(team_name)
                    ),
                    "_games": set(),
                    "plate_appearances": 0,
                    "hits": 0,
                    "singles": 0,
                    "doubles": 0,
                    "triples": 0,
                    "home_runs": 0,
                    "walks": 0,
                    "intentional_walks": 0,
                    "hit_by_pitch": 0,
                    "strikeouts": 0,
                    "sacrifice_flies": 0,
                    "sacrifice_bunts": 0,
                    "double_plays": 0,
                    "triple_plays": 0,
                    "runs": 0,
                    "stolen_bases": 0,
                    "caught_stealing": 0,
                    "picked_off": 0,
                    "_strikeout_pitches": {},
                    "_strikeout_locations": {},
                    "_strikeout_styles": {},
                }

                if scope == "opponent":
                    bucket[
                        "opponent_name"
                    ] = (
                        opponent_name
                        or None
                    )

                player_buckets[
                    scope
                ][key] = bucket

            bucket["_games"].add(
                game["id"]
            )

            if is_plate_appearance:
                bucket[
                    "plate_appearances"
                ] += 1

            if bool(
                safe_int(
                    event.get(
                        "is_hit"
                    )
                )
            ):
                bucket["hits"] += 1

                hit_bases = safe_int(
                    event.get(
                        "hit_bases"
                    )
                )

                if hit_bases == 1:
                    bucket["singles"] += 1
                elif hit_bases == 2:
                    bucket["doubles"] += 1
                elif hit_bases == 3:
                    bucket["triples"] += 1
                elif hit_bases == 4:
                    bucket[
                        "home_runs"
                    ] += 1

            if event_type == "walk":
                bucket["walks"] += 1

                if (
                    event.get("cause")
                    == "intentional_walk"
                ):
                    bucket[
                        "intentional_walks"
                    ] += 1

            elif event_type == "hit_by_pitch":
                bucket[
                    "hit_by_pitch"
                ] += 1

            elif event_type == "strikeout":
                bucket[
                    "strikeouts"
                ] += 1

                _increment_category_count(
                    bucket[
                        "_strikeout_pitches"
                    ],
                    event.get(
                        "terminal_pitch_type"
                    ),
                )
                _increment_category_count(
                    bucket[
                        "_strikeout_locations"
                    ],
                    event.get(
                        "terminal_pitch_location"
                    ),
                )
                _increment_category_count(
                    bucket[
                        "_strikeout_styles"
                    ],
                    event.get(
                        "strikeout_type"
                    ),
                )

            elif event_type == "sacrifice_fly":
                bucket[
                    "sacrifice_flies"
                ] += 1

            elif event_type == "sacrifice_bunt":
                bucket[
                    "sacrifice_bunts"
                ] += 1

            elif event_type == "double_play":
                bucket[
                    "double_plays"
                ] += 1

            elif event_type == "triple_play":
                bucket[
                    "triple_plays"
                ] += 1

            elif event_type == "runner_scored":
                bucket["runs"] += 1

            elif event_type == "stolen_base":
                bucket[
                    "stolen_bases"
                ] += 1

            elif event_type == "caught_stealing":
                bucket[
                    "caught_stealing"
                ] += 1

            elif event_type == "picked_off":
                bucket[
                    "picked_off"
                ] += 1

    def finalize(
        buckets: Dict[
            Any,
            Dict[str, Any],
        ],
    ) -> List[Dict[str, Any]]:
        rows: List[
            Dict[str, Any]
        ] = []

        for bucket in buckets.values():
            plate_appearances = bucket[
                "plate_appearances"
            ]

            at_bats = max(
                0,
                (
                    plate_appearances
                    - bucket["walks"]
                    - bucket[
                        "hit_by_pitch"
                    ]
                    - bucket[
                        "sacrifice_flies"
                    ]
                    - bucket[
                        "sacrifice_bunts"
                    ]
                ),
            )

            hits = bucket["hits"]

            row = {
                key: value
                for key, value
                in bucket.items()
                if not key.startswith("_")
            }

            pitch_counts = bucket[
                "_strikeout_pitches"
            ]
            location_counts = bucket[
                "_strikeout_locations"
            ]
            style_counts = bucket[
                "_strikeout_styles"
            ]

            row[
                "strikeout_tendencies"
            ] = {
                "with_finishing_pitch": (
                    sum(
                        pitch_counts.values()
                    )
                ),
                "with_location": (
                    sum(
                        location_counts.values()
                    )
                ),
                "with_style": (
                    sum(
                        style_counts.values()
                    )
                ),
                "finishing_pitches": (
                    _category_breakdown(
                        pitch_counts
                    )
                ),
                "locations": (
                    _category_breakdown(
                        location_counts
                    )
                ),
                "styles": (
                    _category_breakdown(
                        style_counts
                    )
                ),
            }

            row["games"] = len(
                bucket["_games"]
            )
            row["at_bats"] = at_bats
            row["batting_average"] = (
                round(
                    hits / at_bats,
                    3,
                )
                if at_bats > 0
                else None
            )
            row["walk_pct"] = (
                _percentage(
                    bucket["walks"],
                    plate_appearances,
                )
            )
            row["strikeout_pct"] = (
                _percentage(
                    bucket[
                        "strikeouts"
                    ],
                    plate_appearances,
                )
            )
            row["home_run_pct"] = (
                _percentage(
                    bucket[
                        "home_runs"
                    ],
                    plate_appearances,
                )
            )

            rows.append(row)

        return sorted(
            rows,
            key=lambda row: (
                -row[
                    "plate_appearances"
                ],
                -row["home_runs"],
                row[
                    "player_name"
                ].casefold(),
                row[
                    "team_name"
                ].casefold(),
            ),
        )

    return {
        "games_included": (
            games_included
        ),
        "user_players": finalize(
            player_buckets["user"]
        ),
        "opponent_players": finalize(
            player_buckets[
                "opponent"
            ]
        ),
    }


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
