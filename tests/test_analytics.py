import tempfile
import unittest
from pathlib import Path

from src.analytics import (
    get_inning_scoring_tendencies,
    get_plate_discipline_trends,
    get_scouting_trends,
)
from src.config import USERNAME
from src.database import connect_db, init_db


class AnalyticsTestCase(
    unittest.TestCase
):
    def setUp(self):
        self.temp_dir = (
            tempfile.TemporaryDirectory()
        )
        self.db_path = (
            Path(self.temp_dir.name)
            / "analytics.sqlite3"
        )
        self.conn = connect_db(
            self.db_path
        )
        init_db(self.conn)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def insert_game(
        self,
        *,
        game_id: str,
        display_date: str,
        user_is_home: bool,
        opponent_name: str,
        opponent_team_name: str,
    ) -> None:
        if user_is_home:
            home_full_name = (
                "Configured Team"
            )
            away_full_name = (
                opponent_team_name
            )
            home_name = USERNAME
            away_name = (
                opponent_name
            )
        else:
            home_full_name = (
                opponent_team_name
            )
            away_full_name = (
                "Configured Team"
            )
            home_name = (
                opponent_name
            )
            away_name = USERNAME

        self.conn.execute(
            """
            INSERT INTO games (
                id,
                display_date,
                home_full_name,
                away_full_name,
                home_name,
                away_name,
                opponent_name,
                opponent_team_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                display_date,
                home_full_name,
                away_full_name,
                home_name,
                away_name,
                opponent_name,
                opponent_team_name,
            ),
        )

    def insert_box_score(
        self,
        *,
        game_id: str,
        team_name: str,
        walks: int,
        strikeouts: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO team_box_scores (
                game_id,
                team_id,
                team_name,
                batting_bb,
                batting_so
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                game_id,
                (
                    game_id
                    + "-"
                    + team_name
                ),
                team_name,
                walks,
                strikeouts,
            ),
        )

    def insert_inning(
        self,
        *,
        game_id: str,
        inning: int,
        home_runs: int,
        away_runs: int,
    ) -> None:
        self.conn.execute(
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
                home_runs,
                away_runs,
            ),
        )


class PlateDisciplineTrendTests(
    AnalyticsTestCase
):
    def test_home_and_away_games_are_attributed_and_ordered(
        self,
    ):
        self.insert_game(
            game_id="game-1",
            display_date=(
                "2026-01-01 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Alpha",
            opponent_team_name=(
                "Alpha Team"
            ),
        )
        self.insert_box_score(
            game_id="game-1",
            team_name="Configured Team",
            walks=2,
            strikeouts=5,
        )
        self.insert_box_score(
            game_id="game-1",
            team_name="Alpha Team",
            walks=1,
            strikeouts=7,
        )

        self.insert_game(
            game_id="game-2",
            display_date=(
                "2026-01-02 12:00:00"
            ),
            user_is_home=False,
            opponent_name="Beta",
            opponent_team_name=(
                "Beta Team"
            ),
        )
        self.insert_box_score(
            game_id="game-2",
            team_name="Configured Team",
            walks=4,
            strikeouts=3,
        )
        self.insert_box_score(
            game_id="game-2",
            team_name="Beta Team",
            walks=2,
            strikeouts=6,
        )

        self.conn.commit()

        report = (
            get_plate_discipline_trends(
                self.conn,
                USERNAME,
                limit=2,
            )
        )

        self.assertEqual(
            report["games_included"],
            2,
        )
        self.assertEqual(
            [
                row["game_id"]
                for row in report["games"]
            ],
            [
                "game-1",
                "game-2",
            ],
        )
        self.assertEqual(
            [
                row["user_side"]
                for row in report["games"]
            ],
            [
                "home",
                "away",
            ],
        )
        self.assertEqual(
            report["summary"],
            {
                "user_walks": 6,
                "user_strikeouts": 8,
                "opponent_walks": 3,
                "opponent_strikeouts": 13,
                "user_walks_per_game": 3.0,
                "user_strikeouts_per_game": 4.0,
                "opponent_walks_per_game": 1.5,
                "opponent_strikeouts_per_game": 6.5,
            },
        )


class InningScoringTrendTests(
    AnalyticsTestCase
):
    def test_scoring_is_attributed_by_side_and_inning_denominator(
        self,
    ):
        self.insert_game(
            game_id="game-1",
            display_date=(
                "2026-01-01 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Alpha",
            opponent_team_name=(
                "Alpha Team"
            ),
        )
        self.insert_inning(
            game_id="game-1",
            inning=1,
            home_runs=2,
            away_runs=0,
        )
        self.insert_inning(
            game_id="game-1",
            inning=2,
            home_runs=0,
            away_runs=1,
        )

        self.insert_game(
            game_id="game-2",
            display_date=(
                "2026-01-02 12:00:00"
            ),
            user_is_home=False,
            opponent_name="Beta",
            opponent_team_name=(
                "Beta Team"
            ),
        )
        self.insert_inning(
            game_id="game-2",
            inning=1,
            home_runs=1,
            away_runs=3,
        )
        self.insert_inning(
            game_id="game-2",
            inning=2,
            home_runs=0,
            away_runs=0,
        )
        self.insert_inning(
            game_id="game-2",
            inning=3,
            home_runs=2,
            away_runs=0,
        )

        self.conn.commit()

        report = (
            get_inning_scoring_tendencies(
                self.conn,
                USERNAME,
                limit=2,
            )
        )

        self.assertEqual(
            report["games_included"],
            2,
        )
        self.assertEqual(
            report["innings"],
            [
                {
                    "inning": 1,
                    "games_reaching_inning": 2,
                    "user_innings_observed": 2,
                    "opponent_innings_observed": 2,
                    "user_runs": 5,
                    "opponent_runs": 1,
                    "user_runs_per_observed_inning": 2.5,
                    "opponent_runs_per_observed_inning": 0.5,
                    "run_diff_per_observed_inning": 2.0,
                },
                {
                    "inning": 2,
                    "games_reaching_inning": 2,
                    "user_innings_observed": 2,
                    "opponent_innings_observed": 2,
                    "user_runs": 0,
                    "opponent_runs": 1,
                    "user_runs_per_observed_inning": 0.0,
                    "opponent_runs_per_observed_inning": 0.5,
                    "run_diff_per_observed_inning": -0.5,
                },
                {
                    "inning": 3,
                    "games_reaching_inning": 1,
                    "user_innings_observed": 1,
                    "opponent_innings_observed": 1,
                    "user_runs": 0,
                    "opponent_runs": 2,
                    "user_runs_per_observed_inning": 0.0,
                    "opponent_runs_per_observed_inning": 2.0,
                    "run_diff_per_observed_inning": -2.0,
                },
            ],
        )


class MissingInningRunValueTests(
    AnalyticsTestCase
):
    def test_missing_run_values_are_not_treated_as_zero(
        self,
    ):
        self.insert_game(
            game_id="game-null",
            display_date=(
                "2026-01-03 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Gamma",
            opponent_team_name=(
                "Gamma Team"
            ),
        )
        self.insert_inning(
            game_id="game-null",
            inning=9,
            home_runs=None,
            away_runs=0,
        )
        self.insert_inning(
            game_id="game-null",
            inning=10,
            home_runs=None,
            away_runs=None,
        )
        self.conn.commit()

        report = (
            get_inning_scoring_tendencies(
                self.conn,
                USERNAME,
                limit=1,
            )
        )

        self.assertEqual(
            report["innings"],
            [
                {
                    "inning": 9,
                    "games_reaching_inning": 1,
                    "user_innings_observed": 0,
                    "opponent_innings_observed": 1,
                    "user_runs": 0,
                    "opponent_runs": 0,
                    "user_runs_per_observed_inning": None,
                    "opponent_runs_per_observed_inning": 0.0,
                    "run_diff_per_observed_inning": None,
                },
                {
                    "inning": 10,
                    "games_reaching_inning": 1,
                    "user_innings_observed": 0,
                    "opponent_innings_observed": 0,
                    "user_runs": 0,
                    "opponent_runs": 0,
                    "user_runs_per_observed_inning": None,
                    "opponent_runs_per_observed_inning": None,
                    "run_diff_per_observed_inning": None,
                },
            ],
        )


class EmptyAnalyticsTests(
    AnalyticsTestCase
):
    def test_empty_database_returns_stable_shapes(
        self,
    ):
        report = get_scouting_trends(
            self.conn,
            USERNAME,
            limit=20,
        )

        self.assertEqual(
            report,
            {
                "limit": 20,
                "plate_discipline": {
                    "games_included": 0,
                    "summary": {
                        "user_walks": 0,
                        "user_strikeouts": 0,
                        "opponent_walks": 0,
                        "opponent_strikeouts": 0,
                        "user_walks_per_game": None,
                        "user_strikeouts_per_game": None,
                        "opponent_walks_per_game": None,
                        "opponent_strikeouts_per_game": None,
                    },
                    "games": [],
                },
                "inning_scoring": {
                    "games_included": 0,
                    "innings": [],
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
