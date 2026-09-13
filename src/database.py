import sqlite3
from pathlib import Path


def connect_db(
    db_path: Path,
) -> sqlite3.Connection:
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    if column_exists(
        conn,
        table_name,
        column_name,
    ):
        return

    conn.execute(
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name}
        {column_definition}
        """
    )


def init_db(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            display_date TEXT,
            game_mode TEXT,
            home_full_name TEXT,
            away_full_name TEXT,
            home_name TEXT,
            away_name TEXT,
            home_runs INTEGER,
            away_runs INTEGER,
            home_hits INTEGER,
            away_hits INTEGER,
            home_errors INTEGER,
            away_errors INTEGER,
            user_result TEXT,
            opponent_name TEXT,
            opponent_team_name TEXT,
            raw_game_history_json TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_logs (
            game_id TEXT PRIMARY KEY,
            fetched_at TEXT,
            api_status TEXT,
            raw_game_log_json TEXT,
            raw_text_log TEXT,
            FOREIGN KEY(game_id)
                REFERENCES games(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS team_box_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            team_id TEXT,
            team_name TEXT,
            runs INTEGER,
            hits INTEGER,
            errors INTEGER,
            batting_ab INTEGER,
            batting_r INTEGER,
            batting_h INTEGER,
            batting_rbi INTEGER,
            batting_bb INTEGER,
            batting_so INTEGER,
            pitching_ip REAL,
            pitching_outs INTEGER,
            pitching_h INTEGER,
            pitching_r INTEGER,
            pitching_er INTEGER,
            pitching_bb INTEGER,
            pitching_so INTEGER,
            UNIQUE(game_id, team_id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_batting_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            team_id TEXT,
            team_name TEXT,
            player_name TEXT,
            ab INTEGER,
            r INTEGER,
            h INTEGER,
            rbi INTEGER,
            bb INTEGER,
            so INTEGER,
            doubles INTEGER,
            triples INTEGER,
            hr INTEGER,
            sb INTEGER,
            cs INTEGER,
            UNIQUE(
                game_id,
                team_id,
                player_name
            )
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_pitching_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            team_id TEXT,
            team_name TEXT,
            player_name TEXT,
            ip REAL,
            pitching_outs INTEGER,
            h INTEGER,
            r INTEGER,
            er INTEGER,
            bb INTEGER,
            so INTEGER,
            win INTEGER,
            loss INTEGER,
            save INTEGER,
            UNIQUE(
                game_id,
                team_id,
                player_name
            )
        )
        """
    )


    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_innings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            inning INTEGER NOT NULL,
            home_runs INTEGER,
            away_runs INTEGER,
            UNIQUE(game_id, inning),
            FOREIGN KEY(game_id)
                REFERENCES games(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            source_index INTEGER NOT NULL,
            inning INTEGER NOT NULL,
            batting_side TEXT NOT NULL,
            batting_team_name TEXT,
            event_type TEXT NOT NULL,
            player_name TEXT,
            pitcher_name TEXT,
            pitcher_is_starter INTEGER,
            related_player_name TEXT,
            raw_text TEXT NOT NULL,
            is_plate_appearance INTEGER NOT NULL DEFAULT 0,
            is_hit INTEGER NOT NULL DEFAULT 0,
            is_out INTEGER NOT NULL DEFAULT 0,
            hit_bases INTEGER,
            outs_recorded INTEGER,
            fielding_code TEXT,
            destination_base TEXT,
            cause TEXT,
            strikeout_type TEXT,
            home_run_distance_ft INTEGER,
            terminal_pitch_type TEXT,
            terminal_pitch_location TEXT,
            secondary_out INTEGER NOT NULL DEFAULT 0,
            parser_version INTEGER NOT NULL DEFAULT 1,
            UNIQUE(game_id, source_index),
            FOREIGN KEY(game_id)
                REFERENCES games(id)
        )
        """
    )

    # Migration support for databases created before pitching_outs existed.
    ensure_column(
        conn,
        "team_box_scores",
        "pitching_outs",
        "INTEGER",
    )

    ensure_column(
        conn,
        "player_pitching_stats",
        "pitching_outs",
        "INTEGER",
    )

    # Migration support for databases created before
    # terminal_pitch_location existed.
    ensure_column(
        conn,
        "game_events",
        "terminal_pitch_location",
        "TEXT",
    )

    ensure_column(
        conn,
        "game_events",
        "pitcher_name",
        "TEXT",
    )

    ensure_column(
        conn,
        "game_events",
        "pitcher_is_starter",
        "INTEGER",
    )

    conn.commit()