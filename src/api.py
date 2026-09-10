import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .collector import (
    backfill_missing_pitching_outs,
    sync_game_history,
    sync_game_logs,
)
from .config import (
    DB_PATH,
    MODE,
    PLATFORM,
    USERNAME,
)
from .database import connect_db, init_db
from .live_scout import (
    LiveScoutConfig,
    build_live_scout_report,
)
from .scout import (
    get_run_averages_for_configured_user,
    scout_local_opponent,
)


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
):
    """
    Apply local database migrations once when the API process starts.

    Legacy pitching_outs values are rebuilt only from already-stored
    successful raw game logs; no MLBTS requests are made here.
    """
    conn = connect_db(DB_PATH)

    try:
        init_db(conn)
        backfill_missing_pitching_outs(
            conn
        )
    finally:
        conn.close()

    yield


app = FastAPI(
    title="MLB The Show 26 Scouting API",
    description=(
        "Local API for MLB The Show 26 game history, "
        "game logs, and scouting."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SyncJobRequest(BaseModel):
    type: str = Field(
        pattern="^(history|logs|all)$"
    )


class LiveScoutRequest(BaseModel):
    username: str
    platform: str = PLATFORM
    pages: int = Field(
        default=1,
        ge=1,
        le=25,
    )
    max_games: int = Field(
        default=25,
        ge=1,
        le=250,
    )
    include_logs: bool = False
    log_workers: int = Field(
        default=5,
        ge=1,
        le=10,
    )



SyncType = str

_sync_job_lock = Lock()
_sync_jobs: Dict[str, Dict[str, Any]] = {}
_active_sync_job_id: Optional[str] = None
_latest_sync_job_id: Optional[str] = None


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _copy_job(
    job: Dict[str, Any],
) -> Dict[str, Any]:
    snapshot = dict(job)

    if isinstance(
        snapshot.get("log_summary"),
        dict,
    ):
        snapshot["log_summary"] = dict(
            snapshot["log_summary"]
        )

    return snapshot


def _get_sync_job_snapshot(
    job_id: str,
) -> Optional[Dict[str, Any]]:
    with _sync_job_lock:
        job = _sync_jobs.get(job_id)

        if job is None:
            return None

        return _copy_job(job)


def _get_active_sync_job_snapshot(
) -> Optional[Dict[str, Any]]:
    with _sync_job_lock:
        if not _active_sync_job_id:
            return None

        job = _sync_jobs.get(
            _active_sync_job_id
        )

        if job is None:
            return None

        return _copy_job(job)


def _get_latest_sync_job_snapshot(
) -> Optional[Dict[str, Any]]:
    with _sync_job_lock:
        if not _latest_sync_job_id:
            return None

        job = _sync_jobs.get(
            _latest_sync_job_id
        )

        if job is None:
            return None

        return _copy_job(job)


def _update_sync_job(
    job_id: str,
    **updates: Any,
) -> None:
    with _sync_job_lock:
        job = _sync_jobs.get(job_id)

        if job is None:
            return

        job.update(updates)


def _finish_active_sync_job(
    job_id: str,
) -> None:
    global _active_sync_job_id

    with _sync_job_lock:
        if (
            _active_sync_job_id
            == job_id
        ):
            _active_sync_job_id = None


def _run_sync_job(
    job_id: str,
    sync_type: SyncType,
) -> None:
    conn: Optional[
        sqlite3.Connection
    ] = None

    _update_sync_job(
        job_id,
        status="running",
        started_at=_utc_now(),
        message="Starting sync...",
    )

    try:
        conn = connect_db(DB_PATH)
        init_db(conn)

        human_games = None

        if sync_type in (
            "history",
            "all",
        ):
            _update_sync_job(
                job_id,
                phase="history",
                message=(
                    "Fetching game history "
                    "from MLB The Show..."
                ),
                current_game_id=None,
                progress_current=0,
                progress_total=0,
            )

            games = sync_game_history(
                conn
            )
            human_games = len(games)

            _update_sync_job(
                job_id,
                human_games=human_games,
            )

        if sync_type in (
            "logs",
            "all",
        ):
            _update_sync_job(
                job_id,
                phase="logs",
                message=(
                    "Fetching missing "
                    "game logs..."
                ),
                current_game_id=None,
                progress_current=0,
                progress_total=0,
            )

            def on_progress(
                progress: Dict[
                    str,
                    Any,
                ],
            ) -> None:
                current = int(
                    progress.get(
                        "current",
                        0,
                    )
                )
                total = int(
                    progress.get(
                        "total",
                        0,
                    )
                )

                _update_sync_job(
                    job_id,
                    phase="logs",
                    message=(
                        f"Fetching game logs "
                        f"({current}/{total})..."
                        if total
                        else (
                            "No missing game "
                            "logs to fetch."
                        )
                    ),
                    current_game_id=(
                        progress.get(
                            "game_id"
                        )
                    ),
                    progress_current=current,
                    progress_total=total,
                    log_summary=(
                        progress.get(
                            "summary"
                        )
                    ),
                )

            log_summary = sync_game_logs(
                conn,
                progress_callback=on_progress,
            )

            _update_sync_job(
                job_id,
                log_summary=log_summary,
            )

        if sync_type == "history":
            message = (
                "Game history synced."
            )
        elif sync_type == "logs":
            message = (
                "Game logs synced."
            )
        else:
            message = (
                "Game history and logs "
                "synced."
            )

        _update_sync_job(
            job_id,
            status="completed",
            phase="complete",
            message=message,
            current_game_id=None,
            finished_at=_utc_now(),
        )

    except Exception as exc:
        _update_sync_job(
            job_id,
            status="failed",
            message="Sync failed.",
            error=str(exc),
            current_game_id=None,
            finished_at=_utc_now(),
        )

    finally:
        if conn is not None:
            conn.close()

        _finish_active_sync_job(
            job_id
        )


def _start_sync_job(
    sync_type: SyncType,
) -> Dict[str, Any]:
    global _active_sync_job_id
    global _latest_sync_job_id

    if sync_type not in (
        "history",
        "logs",
        "all",
    ):
        raise HTTPException(
            status_code=422,
            detail="Invalid sync type.",
        )

    job_id = uuid4().hex

    with _sync_job_lock:
        if _active_sync_job_id:
            active_job = (
                _sync_jobs.get(
                    _active_sync_job_id
                )
            )

            if (
                active_job
                and active_job.get(
                    "status"
                )
                in {
                    "queued",
                    "running",
                }
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            "A sync job is "
                            "already running."
                        ),
                        "job_id": (
                            _active_sync_job_id
                        ),
                    },
                )

        job = {
            "id": job_id,
            "type": sync_type,
            "status": "queued",
            "phase": "queued",
            "message": "Sync queued.",
            "created_at": _utc_now(),
            "started_at": None,
            "finished_at": None,
            "human_games": None,
            "progress_current": 0,
            "progress_total": 0,
            "current_game_id": None,
            "log_summary": None,
            "error": None,
        }

        _sync_jobs[job_id] = job
        _active_sync_job_id = job_id
        _latest_sync_job_id = job_id

    worker = Thread(
        target=_run_sync_job,
        args=(
            job_id,
            sync_type,
        ),
        daemon=True,
    )
    worker.start()

    snapshot = (
        _get_sync_job_snapshot(
            job_id
        )
    )

    if snapshot is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Sync job could not "
                "be created."
            ),
        )

    return snapshot



def get_conn() -> Generator[
    sqlite3.Connection,
    None,
    None,
]:
    """
    FastAPI database dependency.

    Every request receives its own SQLite connection, and the connection is
    always closed after the request finishes.
    """
    conn = connect_db(DB_PATH)
    init_db(conn)

    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(
    row: sqlite3.Row,
) -> Dict[str, Any]:
    return dict(row)


@app.get("/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
    }


@app.get("/config")
def get_config() -> Dict[str, str]:
    """
    Expose the non-secret application identity/configuration used by the
    local frontend.

    This prevents the username/platform from being duplicated in TypeScript.
    """
    return {
        "username": USERNAME,
        "platform": PLATFORM,
        "mode": MODE,
    }


@app.get("/dashboard")
def get_dashboard(
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    total_games = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM games
        """
    ).fetchone()["count"]

    total_logs = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM game_logs
        """
    ).fetchone()["count"]

    successful_logs = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM game_logs
        WHERE api_status = 'ok'
        """
    ).fetchone()["count"]

    record_row = conn.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN user_result = 'W'
                    THEN 1
                    ELSE 0
                END
            ) AS wins,
            SUM(
                CASE
                    WHEN user_result = 'L'
                    THEN 1
                    ELSE 0
                END
            ) AS losses
        FROM games
        """
    ).fetchone()

    average_game_rows = conn.execute(
        """
        SELECT
            home_name,
            away_name,
            home_runs,
            away_runs
        FROM games
        """
    ).fetchall()

    (
        avg_runs_scored,
        avg_runs_allowed,
    ) = get_run_averages_for_configured_user(
        [
            row_to_dict(row)
            for row in average_game_rows
        ]
    )

    recent_games = conn.execute(
        """
        SELECT
            id,
            display_date,
            opponent_name,
            opponent_team_name,
            user_result,
            home_full_name,
            away_full_name,
            home_runs,
            away_runs
        FROM games
        ORDER BY display_date DESC
        LIMIT 10
        """
    ).fetchall()

    wins = record_row["wins"] or 0
    losses = record_row["losses"] or 0

    total_decisions = (
        wins + losses
    )

    return {
        "total_games": total_games,
        "total_game_logs": total_logs,
        "successful_game_logs": successful_logs,
        "record": {
            "wins": wins,
            "losses": losses,
            "win_pct": (
                round(
                    wins / total_decisions,
                    3,
                )
                if total_decisions
                else None
            ),
        },
        "averages": {
            "runs_scored": (
                avg_runs_scored
            ),
            "runs_allowed": (
                avg_runs_allowed
            ),
        },
        "recent_games": [
            row_to_dict(row)
            for row in recent_games
        ],
    }


@app.get("/games")
def get_games(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    opponent: Optional[str] = None,
    result: Optional[str] = Query(
        default=None,
        pattern="^(W|L)?$",
    ),
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    where_clauses: List[str] = []
    params: List[Any] = []

    if opponent:
        where_clauses.append(
            "LOWER(opponent_name) "
            "LIKE LOWER(?)"
        )
        params.append(
            f"%{opponent}%"
        )

    if result:
        where_clauses.append(
            "user_result = ?"
        )
        params.append(result)

    where_sql = ""

    if where_clauses:
        where_sql = (
            "WHERE "
            + " AND ".join(
                where_clauses
            )
        )

    total = conn.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM games
        {where_sql}
        """,
        params,
    ).fetchone()["count"]

    rows = conn.execute(
        f"""
        SELECT
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
            opponent_team_name
        FROM games
        {where_sql}
        ORDER BY display_date DESC
        LIMIT ?
        OFFSET ?
        """,
        [
            *params,
            limit,
            offset,
        ],
    ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "games": [
            row_to_dict(row)
            for row in rows
        ],
    }


@app.get("/games/{game_id}")
def get_game_detail(
    game_id: str,
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    game = conn.execute(
        """
        SELECT *
        FROM games
        WHERE id = ?
        """,
        (game_id,),
    ).fetchone()

    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found",
        )

    game_log = conn.execute(
        """
        SELECT *
        FROM game_logs
        WHERE game_id = ?
        """,
        (game_id,),
    ).fetchone()

    team_box_scores = conn.execute(
        """
        SELECT *
        FROM team_box_scores
        WHERE game_id = ?
        ORDER BY team_name
        """,
        (game_id,),
    ).fetchall()

    batting_stats = conn.execute(
        """
        SELECT *
        FROM player_batting_stats
        WHERE game_id = ?
        ORDER BY
            team_name,
            player_name
        """,
        (game_id,),
    ).fetchall()

    pitching_stats = conn.execute(
        """
        SELECT *
        FROM player_pitching_stats
        WHERE game_id = ?
        ORDER BY
            team_name,
            player_name
        """,
        (game_id,),
    ).fetchall()

    return {
        "game": row_to_dict(game),
        "game_log": (
            row_to_dict(game_log)
            if game_log
            else None
        ),
        "team_box_scores": [
            row_to_dict(row)
            for row in team_box_scores
        ],
        "batting_stats": [
            row_to_dict(row)
            for row in batting_stats
        ],
        "pitching_stats": [
            row_to_dict(row)
            for row in pitching_stats
        ],
    }


@app.get("/opponents")
def get_opponents(
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
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
            MAX(
                display_date
            ) AS last_played
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

    opponents = []

    for row in rows:
        item = row_to_dict(row)

        opponent_games = conn.execute(
            """
            SELECT
                home_name,
                away_name,
                home_runs,
                away_runs
            FROM games
            WHERE opponent_name = ?
              AND opponent_team_name IS ?
            """,
            (
                item["opponent_name"],
                item["opponent_team_name"],
            ),
        ).fetchall()

        (
            avg_runs_scored,
            avg_runs_allowed,
        ) = get_run_averages_for_configured_user(
            [
                row_to_dict(game)
                for game in opponent_games
            ]
        )

        item[
            "avg_runs_scored"
        ] = avg_runs_scored

        item[
            "avg_runs_allowed"
        ] = avg_runs_allowed

        opponents.append(item)

    return {
        "total": len(opponents),
        "opponents": opponents,
    }


@app.get("/opponents/{username}")
def get_local_opponent(
    username: str,
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    return scout_local_opponent(
        conn,
        username,
    )



@app.post(
    "/sync/jobs",
    status_code=202,
)
def start_sync_job_endpoint(
    request: SyncJobRequest,
) -> Dict[str, Any]:
    return _start_sync_job(
        request.type
    )


@app.get("/sync/jobs/active")
def get_active_sync_job_endpoint(
) -> Dict[str, Any]:
    return {
        "job": (
            _get_active_sync_job_snapshot()
        ),
    }


@app.get("/sync/jobs/latest")
def get_latest_sync_job_endpoint(
) -> Dict[str, Any]:
    return {
        "job": (
            _get_latest_sync_job_snapshot()
        ),
    }


@app.get("/sync/jobs/{job_id}")
def get_sync_job_endpoint(
    job_id: str,
) -> Dict[str, Any]:
    job = _get_sync_job_snapshot(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Sync job not found.",
        )

    return job


@app.post("/sync/history")
def sync_history_endpoint(
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    games = sync_game_history(conn)

    return {
        "status": "ok",
        "message": (
            "Game history synced."
        ),
        "human_games": len(games),
    }


@app.post("/sync/logs")
def sync_logs_endpoint(
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    summary = sync_game_logs(conn)

    return {
        "status": "ok",
        "message": (
            "Game logs synced."
        ),
        "summary": summary,
    }


@app.post("/sync/all")
def sync_all_endpoint(
    conn: sqlite3.Connection = Depends(
        get_conn
    ),
) -> Dict[str, Any]:
    games = sync_game_history(conn)

    log_summary = sync_game_logs(
        conn
    )

    return {
        "status": "ok",
        "message": (
            "Game history and logs synced."
        ),
        "human_games": len(games),
        "log_summary": log_summary,
    }


@app.post("/live-scout")
def live_scout_endpoint(
    request: LiveScoutRequest,
) -> Dict[str, Any]:
    config = LiveScoutConfig(
        username=request.username,
        platform=(
            request.platform
            .strip()
            .lower()
        ),
        max_pages=request.pages,
        max_games=request.max_games,
        include_logs=(
            request.include_logs
        ),
        log_workers=(
            request.log_workers
        ),
    )

    return build_live_scout_report(
        config
    )