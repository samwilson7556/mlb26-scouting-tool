import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .collector import sync_game_history, sync_game_logs
from .config import DB_PATH
from .database import connect_db, init_db
from .live_scout import LiveScoutConfig, build_live_scout_report
from .scout import scout_local_opponent


app = FastAPI(
    title="MLB The Show 26 Scouting API",
    description="Local API for MLB The Show 26 game history, game logs, and scouting.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LiveScoutRequest(BaseModel):
    username: str
    platform: str = "psn"
    pages: int = Field(default=1, ge=1, le=25)
    max_games: int = Field(default=25, ge=1, le=250)
    include_logs: bool = False
    log_workers: int = Field(default=5, ge=1, le=10)


def get_conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    init_db(conn)
    return conn


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard")
def get_dashboard() -> Dict[str, Any]:
    conn = get_conn()

    total_games = conn.execute("SELECT COUNT(*) AS count FROM games").fetchone()["count"]
    total_logs = conn.execute("SELECT COUNT(*) AS count FROM game_logs").fetchone()["count"]

    record_row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN user_result = 'W' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN user_result = 'L' THEN 1 ELSE 0 END) AS losses
        FROM games
        """
    ).fetchone()

    avg_row = conn.execute(
        """
        SELECT
            AVG(
                CASE
                    WHEN home_name = 'poopoopee155' THEN home_runs
                    WHEN away_name = 'poopoopee155' THEN away_runs
                END
            ) AS avg_runs_scored,
            AVG(
                CASE
                    WHEN home_name = 'poopoopee155' THEN away_runs
                    WHEN away_name = 'poopoopee155' THEN home_runs
                END
            ) AS avg_runs_allowed
        FROM games
        """
    ).fetchone()

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
    total_decisions = wins + losses

    return {
        "total_games": total_games,
        "total_game_logs": total_logs,
        "record": {
            "wins": wins,
            "losses": losses,
            "win_pct": round(wins / total_decisions, 3) if total_decisions else None,
        },
        "averages": {
            "runs_scored": round(avg_row["avg_runs_scored"], 2)
            if avg_row["avg_runs_scored"] is not None
            else None,
            "runs_allowed": round(avg_row["avg_runs_allowed"], 2)
            if avg_row["avg_runs_allowed"] is not None
            else None,
        },
        "recent_games": [row_to_dict(row) for row in recent_games],
    }


@app.get("/games")
def get_games(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    opponent: Optional[str] = None,
    result: Optional[str] = Query(default=None, pattern="^(W|L)?$"),
) -> Dict[str, Any]:
    conn = get_conn()

    where_clauses = []
    params: List[Any] = []

    if opponent:
        where_clauses.append("LOWER(opponent_name) LIKE LOWER(?)")
        params.append(f"%{opponent}%")

    if result:
        where_clauses.append("user_result = ?")
        params.append(result)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    total = conn.execute(
        f"SELECT COUNT(*) AS count FROM games {where_sql}",
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
        [*params, limit, offset],
    ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "games": [row_to_dict(row) for row in rows],
    }


@app.get("/games/{game_id}")
def get_game_detail(game_id: str) -> Dict[str, Any]:
    conn = get_conn()

    game = conn.execute(
        """
        SELECT *
        FROM games
        WHERE id = ?
        """,
        (game_id,),
    ).fetchone()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

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
        ORDER BY team_name, player_name
        """,
        (game_id,),
    ).fetchall()

    pitching_stats = conn.execute(
        """
        SELECT *
        FROM player_pitching_stats
        WHERE game_id = ?
        ORDER BY team_name, player_name
        """,
        (game_id,),
    ).fetchall()

    return {
        "game": row_to_dict(game),
        "game_log": row_to_dict(game_log) if game_log else None,
        "team_box_scores": [row_to_dict(row) for row in team_box_scores],
        "batting_stats": [row_to_dict(row) for row in batting_stats],
        "pitching_stats": [row_to_dict(row) for row in pitching_stats],
    }


@app.get("/opponents")
def get_opponents() -> Dict[str, Any]:
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT
            opponent_name,
            opponent_team_name,
            COUNT(*) AS games_played,
            SUM(CASE WHEN user_result = 'W' THEN 1 ELSE 0 END) AS your_wins,
            SUM(CASE WHEN user_result = 'L' THEN 1 ELSE 0 END) AS your_losses,
            MAX(display_date) AS last_played,
            AVG(
                CASE
                    WHEN home_name = 'poopoopee155' THEN home_runs
                    WHEN away_name = 'poopoopee155' THEN away_runs
                END
            ) AS avg_runs_scored,
            AVG(
                CASE
                    WHEN home_name = 'poopoopee155' THEN away_runs
                    WHEN away_name = 'poopoopee155' THEN home_runs
                END
            ) AS avg_runs_allowed
        FROM games
        WHERE opponent_name IS NOT NULL
          AND opponent_name != ''
        GROUP BY opponent_name, opponent_team_name
        ORDER BY last_played DESC
        """
    ).fetchall()

    opponents = []

    for row in rows:
        item = row_to_dict(row)

        if item["avg_runs_scored"] is not None:
            item["avg_runs_scored"] = round(item["avg_runs_scored"], 2)

        if item["avg_runs_allowed"] is not None:
            item["avg_runs_allowed"] = round(item["avg_runs_allowed"], 2)

        opponents.append(item)

    return {
        "total": len(opponents),
        "opponents": opponents,
    }


@app.get("/opponents/{username}")
def get_local_opponent(username: str) -> Dict[str, Any]:
    conn = get_conn()
    return scout_local_opponent(conn, username)


@app.post("/sync/history")
def sync_history_endpoint() -> Dict[str, Any]:
    conn = get_conn()
    games = sync_game_history(conn)

    return {
        "status": "ok",
        "message": "Game history synced.",
        "human_games": len(games),
    }


@app.post("/sync/logs")
def sync_logs_endpoint() -> Dict[str, Any]:
    conn = get_conn()
    sync_game_logs(conn)

    return {
        "status": "ok",
        "message": "Game logs synced.",
    }


@app.post("/sync/all")
def sync_all_endpoint() -> Dict[str, Any]:
    conn = get_conn()
    games = sync_game_history(conn)
    sync_game_logs(conn)

    return {
        "status": "ok",
        "message": "Game history and logs synced.",
        "human_games": len(games),
    }


@app.post("/live-scout")
def live_scout_endpoint(request: LiveScoutRequest) -> Dict[str, Any]:
    config = LiveScoutConfig(
        username=request.username,
        platform=request.platform,
        max_pages=request.pages,
        max_games=request.max_games,
        include_logs=request.include_logs,
        log_workers=request.log_workers,
    )

    report = build_live_scout_report(config)
    return report