import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import get_dashboard, get_opponents
from src.database import connect_db, init_db


class ApiAggregateAttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conn = connect_db(
            Path(self.temp_dir.name) / "test.sqlite3"
        )
        init_db(self.conn)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def insert_game(
        self,
        game_id: str,
        home_name: str,
        away_name: str,
        home_runs: int,
        away_runs: int,
        opponent_name: str,
        opponent_team_name: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO games (
                id,
                display_date,
                home_full_name,
                away_full_name,
                home_name,
                away_name,
                home_runs,
                away_runs,
                user_result,
                opponent_name,
                opponent_team_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                "2026-01-01 12:00:00",
                "Home Team",
                "Away Team",
                home_name,
                away_name,
                home_runs,
                away_runs,
                "W",
                opponent_name,
                opponent_team_name,
            ),
        )
        self.conn.commit()

    def seed_marker_and_direct_games(self) -> None:
        self.insert_game(
            "game-1",
            "CPU",
            "RivalUser",
            6,
            2,
            "RivalUser",
            "Rivals",
        )
        self.insert_game(
            "game-2",
            "RivalUser",
            "ConfiguredUser",
            3,
            4,
            "RivalUser",
            "Rivals",
        )

    def test_dashboard_averages_use_shared_side_attribution(self):
        self.seed_marker_and_direct_games()
        with patch("src.scout.USERNAME", "ConfiguredUser"):
            dashboard = get_dashboard(self.conn)

        self.assertEqual(dashboard["averages"]["runs_scored"], 5.0)
        self.assertEqual(dashboard["averages"]["runs_allowed"], 2.5)

    def test_opponent_averages_use_shared_side_attribution(self):
        self.seed_marker_and_direct_games()
        with patch("src.scout.USERNAME", "ConfiguredUser"):
            response = get_opponents(self.conn)

        self.assertEqual(response["total"], 1)
        opponent = response["opponents"][0]
        self.assertEqual(opponent["avg_runs_scored"], 5.0)
        self.assertEqual(opponent["avg_runs_allowed"], 2.5)

    def test_opponents_uses_constant_query_count(self):
        self.seed_marker_and_direct_games()
        self.insert_game(
            "game-3",
            "ConfiguredUser",
            "SecondRival",
            5,
            1,
            "SecondRival",
            "Second Rivals",
        )

        statements = []
        self.conn.set_trace_callback(statements.append)

        try:
            with patch("src.scout.USERNAME", "ConfiguredUser"):
                response = get_opponents(self.conn)
        finally:
            self.conn.set_trace_callback(None)

        select_statements = [
            statement
            for statement in statements
            if statement.lstrip().upper().startswith("SELECT")
        ]

        self.assertEqual(response["total"], 2)
        self.assertEqual(len(select_statements), 2)


if __name__ == "__main__":
    unittest.main()
