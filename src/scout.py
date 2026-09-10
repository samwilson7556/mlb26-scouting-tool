import json
import sqlite3
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

from .config import EXPORT_DIR, USERNAME
from .parser import get_user_side, safe_int


console = Console()


def get_all_opponents(
    conn: sqlite3.Connection,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            opponent_name,
            opponent_team_name,
            COUNT(*) AS games_played,
            SUM(
                CASE
                    WHEN user_result = 'W'
                    THEN 1
                    ELSE 0
                END
            ) AS your_wins,
            SUM(
                CASE
                    WHEN user_result = 'L'
                    THEN 1
                    ELSE 0
                END
            ) AS your_losses,
            MAX(display_date) AS last_played
        FROM games
        WHERE opponent_name IS NOT NULL
          AND opponent_name != ''
        GROUP BY
            opponent_name,
            opponent_team_name
        ORDER BY
            last_played DESC
        """
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_runs_for_configured_user(
    game: Dict[str, Any],
) -> tuple[int | None, int | None]:
    """
    Return (user_runs, opponent_runs) for a stored game.

    User-side attribution is delegated to the shared parser logic so this
    module never needs its own hardcoded MLBTS username.
    """
    side = get_user_side(
        game,
        USERNAME,
    )

    if side == "home":
        return (
            safe_int(
                game.get("home_runs")
            ),
            safe_int(
                game.get("away_runs")
            ),
        )

    if side == "away":
        return (
            safe_int(
                game.get("away_runs")
            ),
            safe_int(
                game.get("home_runs")
            ),
        )

    return None, None


def scout_local_opponent(
    conn: sqlite3.Connection,
    opponent_username: str,
) -> Dict[str, Any]:
    games = conn.execute(
        """
        SELECT *
        FROM games
        WHERE LOWER(opponent_name) = LOWER(?)
        ORDER BY display_date DESC
        """,
        (opponent_username,),
    ).fetchall()

    if not games:
        return {
            "opponent": opponent_username,
            "found": False,
            "message": (
                "No local games found "
                "against this opponent."
            ),
        }

    games_list = [
        dict(row)
        for row in games
    ]

    total_games = len(
        games_list
    )

    your_wins = sum(
        1
        for game in games_list
        if game["user_result"] == "W"
    )

    your_losses = sum(
        1
        for game in games_list
        if game["user_result"] == "L"
    )

    your_runs: List[int] = []
    opponent_runs: List[int] = []

    for game in games_list:
        user_runs, other_runs = (
            get_runs_for_configured_user(
                game
            )
        )

        if (
            user_runs is not None
            and other_runs is not None
        ):
            your_runs.append(
                user_runs
            )

            opponent_runs.append(
                other_runs
            )

    avg_runs_scored = (
        sum(your_runs)
        / len(your_runs)
        if your_runs
        else 0
    )

    avg_runs_allowed = (
        sum(opponent_runs)
        / len(opponent_runs)
        if opponent_runs
        else 0
    )

    return {
        "opponent": opponent_username,
        "found": True,
        "games_played": total_games,
        "your_record": (
            f"{your_wins}-"
            f"{your_losses}"
        ),
        "avg_runs_scored": round(
            avg_runs_scored,
            2,
        ),
        "avg_runs_allowed": round(
            avg_runs_allowed,
            2,
        ),
        "last_played": (
            games_list[0][
                "display_date"
            ]
        ),
        "games": games_list,
    }


def print_opponent_summary(
    conn: sqlite3.Connection,
) -> None:
    opponents = get_all_opponents(
        conn
    )

    table = Table(
        title="Opponent Summary"
    )

    table.add_column(
        "Opponent"
    )

    table.add_column(
        "Team"
    )

    table.add_column(
        "Games",
        justify="right",
    )

    table.add_column(
        "Your Record",
        justify="right",
    )

    table.add_column(
        "Last Played"
    )

    for opponent in opponents:
        record = (
            f"{opponent['your_wins']}-"
            f"{opponent['your_losses']}"
        )

        table.add_row(
            opponent[
                "opponent_name"
            ],
            opponent[
                "opponent_team_name"
            ]
            or "",
            str(
                opponent[
                    "games_played"
                ]
            ),
            record,
            opponent[
                "last_played"
            ]
            or "",
        )

    console.print(
        table
    )


def print_local_scout(
    conn: sqlite3.Connection,
    opponent_username: str,
) -> None:
    report = scout_local_opponent(
        conn,
        opponent_username,
    )

    if not report["found"]:
        console.print(
            f"[yellow]"
            f"{report['message']}"
            f"[/yellow]"
        )
        return

    console.print(
        f"[bold green]"
        f"Opponent:"
        f"[/bold green] "
        f"{report['opponent']}"
    )

    console.print(
        f"[bold]"
        f"Games vs you:"
        f"[/bold] "
        f"{report['games_played']}"
    )

    console.print(
        f"[bold]"
        f"Your record:"
        f"[/bold] "
        f"{report['your_record']}"
    )

    console.print(
        f"[bold]"
        f"Avg runs scored:"
        f"[/bold] "
        f"{report['avg_runs_scored']}"
    )

    console.print(
        f"[bold]"
        f"Avg runs allowed:"
        f"[/bold] "
        f"{report['avg_runs_allowed']}"
    )

    console.print(
        f"[bold]"
        f"Last played:"
        f"[/bold] "
        f"{report['last_played']}"
    )

    table = Table(
        title=(
            f"Games vs "
            f"{opponent_username}"
        )
    )

    table.add_column(
        "Date"
    )

    table.add_column(
        "Result"
    )

    table.add_column(
        "Home"
    )

    table.add_column(
        "Away"
    )

    table.add_column(
        "Score"
    )

    for game in report["games"]:
        score = (
            f"{game['home_runs']}-"
            f"{game['away_runs']}"
        )

        table.add_row(
            game[
                "display_date"
            ]
            or "",
            game[
                "user_result"
            ]
            or "",
            game[
                "home_full_name"
            ]
            or "",
            game[
                "away_full_name"
            ]
            or "",
            score,
        )

    console.print(
        table
    )


def export_opponent_summary(
    conn: sqlite3.Connection,
) -> None:
    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    opponents = get_all_opponents(
        conn
    )

    path = (
        EXPORT_DIR
        / "opponent_summary.json"
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            opponents,
            f,
            indent=2,
            ensure_ascii=False,
        )

    console.print(
        f"[green]"
        f"Exported opponent summary:"
        f"[/green] "
        f"{path}"
    )