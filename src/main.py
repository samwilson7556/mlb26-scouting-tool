import argparse

from rich.console import Console

from .collector import (
    backfill_missing_pitching_outs,
    reparse_stored_game_logs,
    sync_game_history,
    sync_game_logs,
)
from .config import (
    DATA_DIR,
    DB_PATH,
    EXPORT_DIR,
    PLATFORM,
    RAW_GAME_LOG_DIR,
)
from .database import connect_db, init_db
from .live_scout import run_live_scout
from .scout import (
    export_opponent_summary,
    print_local_scout,
    print_opponent_summary,
)


console = Console()


def ensure_directories() -> None:
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_GAME_LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "MLB The Show 26 game-history "
            "collector and scouting tool"
        )
    )

    parser.add_argument(
        "command",
        choices=[
            "init",
            "sync-history",
            "sync-logs",
            "sync-all",
            "reparse-logs",
            "opponents",
            "scout",
            "live-scout",
            "export-opponents",
        ],
        help="Command to run",
    )

    parser.add_argument(
        "--username",
        help=(
            "Opponent username for the "
            "scout or live-scout command"
        ),
    )

    parser.add_argument(
        "--platform",
        default=PLATFORM,
        help=(
            "Platform for live scouting. "
            "Common values: psn, xbl, "
            "mlbts, nsw. "
            f"Default: {PLATFORM}"
        ),
    )

    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help=(
            "Number of game-history pages "
            "to fetch for live scouting. "
            "Default: 1"
        ),
    )

    parser.add_argument(
        "--max-games",
        type=int,
        default=25,
        help=(
            "Maximum recent human-vs-human "
            "games to analyze for live "
            "scouting. Default: 25"
        ),
    )

    parser.add_argument(
        "--include-logs",
        action="store_true",
        help=(
            "For live scouting, fetch recent "
            "game logs to calculate batting "
            "average and ERA."
        ),
    )

    parser.add_argument(
        "--log-workers",
        type=int,
        default=5,
        help=(
            "Concurrent game-log workers for "
            "live scouting with --include-logs. "
            "Default: 5"
        ),
    )

    parser.add_argument(
        "--no-export",
        action="store_true",
        help=(
            "For live scouting, do not export "
            "the scout report JSON file."
        ),
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    ensure_directories()

    conn = connect_db(DB_PATH)

    try:
        init_db(conn)

        if args.command != "reparse-logs":
            backfill_summary = (
                backfill_missing_pitching_outs(
                    conn
                )
            )

            if (
                backfill_summary[
                    "reparsed"
                ]
                > 0
            ):
                console.print(
                    f"[green]"
                    f"Backfilled pitching outs "
                    f"from "
                    f"{backfill_summary['reparsed']} "
                    f"stored game log(s)."
                    f"[/green]"
                )

        if args.command == "init":
            console.print(
                f"[green]"
                f"Database initialized:"
                f"[/green] "
                f"{DB_PATH}"
            )

        elif args.command == "reparse-logs":
            summary = (
                reparse_stored_game_logs(
                    conn
                )
            )

            console.print(
                "[bold]"
                "Stored game-log reparse summary"
                "[/bold]"
            )
            console.print(
                f"Found: "
                f"{summary['found']}"
            )
            console.print(
                f"Reparsed: "
                f"{summary['reparsed']}"
            )
            console.print(
                f"Failed: "
                f"{summary['failed']}"
            )

        elif args.command == "sync-history":
            sync_game_history(conn)

        elif args.command == "sync-logs":
            sync_game_logs(conn)

        elif args.command == "sync-all":
            sync_game_history(conn)
            sync_game_logs(conn)
            export_opponent_summary(
                conn
            )

        elif args.command == "opponents":
            print_opponent_summary(
                conn
            )

        elif args.command == "scout":
            username = (
                args.username.strip()
                if args.username
                else ""
            )

            if not username:
                console.print(
                    "[red]"
                    "Please provide --username "
                    "for the scout command."
                    "[/red]"
                )

                return

            print_local_scout(
                conn,
                username,
            )

        elif args.command == "live-scout":
            username = (
                args.username.strip()
                if args.username
                else ""
            )

            if not username:
                console.print(
                    "[red]"
                    "Please provide --username "
                    "for the live-scout command."
                    "[/red]"
                )

                return

            run_live_scout(
                username=username,
                platform=(
                    args.platform
                    .strip()
                    .lower()
                ),
                pages=args.pages,
                max_games=args.max_games,
                include_logs=(
                    args.include_logs
                ),
                export=(
                    not args.no_export
                ),
                log_workers=(
                    args.log_workers
                ),
            )

        elif args.command == "export-opponents":
            export_opponent_summary(
                conn
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()