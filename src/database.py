import sqlite3
from pathlib import Path


def connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
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
            FOREIGN KEY(game_id) REFERENCES games(id)
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
            UNIQUE(game_id, team_id, player_name)
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
            h INTEGER,
            r INTEGER,
            er INTEGER,
            bb INTEGER,
            so INTEGER,
            win INTEGER,
            loss INTEGER,
            save INTEGER,
            UNIQUE(game_id, team_id, player_name)
        )
        """
    )

    conn.commit()