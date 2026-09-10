import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.collector import (
    backfill_missing_pitching_outs,
    classify_game_log_response,
    get_game_ids_needing_pitching_outs_backfill,
    get_unfetched_game_ids,
    save_box_score_sections,
    save_game_log,
    save_raw_game_log,
)
from src.database import (
    column_exists,
    connect_db,
    init_db,
)


class TemporaryDatabaseTestCase(
    unittest.TestCase
):
    def setUp(self):
        self.temp_dir = (
            tempfile.TemporaryDirectory()
        )

        self.db_path = (
            Path(self.temp_dir.name)
            / "test.sqlite3"
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
        game_id: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO games (
                id,
                display_date,
                home_full_name,
                away_full_name,
                home_name,
                away_name
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                "2026-01-01 12:00:00",
                "Home Team",
                "Away Team",
                "ConfiguredUser",
                "OpponentUser",
            ),
        )

        self.conn.commit()


class DatabaseSchemaTests(
    TemporaryDatabaseTestCase
):
    def test_new_database_has_team_pitching_outs(
        self,
    ):
        self.assertTrue(
            column_exists(
                self.conn,
                "team_box_scores",
                "pitching_outs",
            )
        )

    def test_new_database_has_player_pitching_outs(
        self,
    ):
        self.assertTrue(
            column_exists(
                self.conn,
                "player_pitching_stats",
                "pitching_outs",
            )
        )


class LegacyDatabaseMigrationTests(
    unittest.TestCase
):
    def test_init_db_migrates_legacy_pitching_tables(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = (
                Path(temp_dir)
                / "legacy.sqlite3"
            )

            conn = sqlite3.connect(
                db_path
            )

            conn.row_factory = (
                sqlite3.Row
            )

            conn.execute(
                """
                CREATE TABLE team_box_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT,
                    team_id TEXT,
                    team_name TEXT,
                    pitching_ip REAL,
                    UNIQUE(game_id, team_id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE player_pitching_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT,
                    team_id TEXT,
                    team_name TEXT,
                    player_name TEXT,
                    ip REAL,
                    UNIQUE(
                        game_id,
                        team_id,
                        player_name
                    )
                )
                """
            )

            conn.commit()

            self.assertFalse(
                column_exists(
                    conn,
                    "team_box_scores",
                    "pitching_outs",
                )
            )

            self.assertFalse(
                column_exists(
                    conn,
                    "player_pitching_stats",
                    "pitching_outs",
                )
            )

            init_db(conn)

            self.assertTrue(
                column_exists(
                    conn,
                    "team_box_scores",
                    "pitching_outs",
                )
            )

            self.assertTrue(
                column_exists(
                    conn,
                    "player_pitching_stats",
                    "pitching_outs",
                )
            )

            conn.close()


class GameLogClassificationTests(
    unittest.TestCase
):
    def test_success(self):
        self.assertEqual(
            classify_game_log_response(
                {
                    "game": [],
                }
            ),
            "ok",
        )

    def test_identity_mismatch(self):
        self.assertEqual(
            classify_game_log_response(
                {
                    "error": (
                        "Username and platform "
                        "do not match the game record."
                    )
                }
            ),
            "identity_mismatch",
        )

    def test_not_found(self):
        self.assertEqual(
            classify_game_log_response(
                {
                    "error": (
                        "Game not found"
                    )
                }
            ),
            "not_found",
        )

    def test_other_api_error(self):
        self.assertEqual(
            classify_game_log_response(
                {
                    "error": (
                        "Unexpected API problem"
                    )
                }
            ),
            "api_error",
        )


class UnfetchedGameTests(
    TemporaryDatabaseTestCase
):
    def test_game_without_log_is_unfetched(
        self,
    ):
        self.insert_game(
            "game-1"
        )

        ids = get_unfetched_game_ids(
            self.conn
        )

        self.assertEqual(
            ids,
            ["game-1"],
        )

    def test_successful_log_is_not_unfetched(
        self,
    ):
        self.insert_game(
            "game-1"
        )

        self.conn.execute(
            """
            INSERT INTO game_logs (
                game_id,
                fetched_at,
                api_status,
                raw_game_log_json,
                raw_text_log
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "game-1",
                "2026-01-01 12:01:00",
                "ok",
                '{"game": []}',
                "",
            ),
        )

        self.conn.commit()

        ids = get_unfetched_game_ids(
            self.conn
        )

        self.assertEqual(
            ids,
            [],
        )

    def test_error_log_is_not_retried_automatically(
        self,
    ):
        self.insert_game(
            "game-1"
        )

        self.conn.execute(
            """
            INSERT INTO game_logs (
                game_id,
                fetched_at,
                api_status,
                raw_game_log_json,
                raw_text_log
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "game-1",
                "2026-01-01 12:01:00",
                "identity_mismatch",
                json.dumps(
                    {
                        "error": (
                            "Username and platform "
                            "do not match the game record."
                        )
                    }
                ),
                "",
            ),
        )

        self.conn.commit()

        ids = get_unfetched_game_ids(
            self.conn
        )

        self.assertEqual(
            ids,
            [],
        )


class SuccessfulLogPreservationTests(
    TemporaryDatabaseTestCase
):
    def test_successful_database_log_is_not_downgraded(
        self,
    ):
        self.insert_game(
            "game-1"
        )

        successful_payload = {
            "game": [
                [
                    "game_log",
                    "Successful historical game log",
                ],
            ]
        }

        first_status = save_game_log(
            self.conn,
            "game-1",
            successful_payload,
        )

        self.assertEqual(
            first_status,
            "ok",
        )

        error_payload = {
            "error": (
                "Username and platform "
                "do not match the game record."
            )
        }

        second_status = save_game_log(
            self.conn,
            "game-1",
            error_payload,
        )

        self.assertEqual(
            second_status,
            "preserved_ok",
        )

        row = self.conn.execute(
            """
            SELECT
                api_status,
                raw_game_log_json,
                raw_text_log
            FROM game_logs
            WHERE game_id = ?
            """,
            ("game-1",),
        ).fetchone()

        self.assertEqual(
            row["api_status"],
            "ok",
        )

        stored_payload = json.loads(
            row["raw_game_log_json"]
        )

        self.assertEqual(
            stored_payload,
            successful_payload,
        )

        self.assertEqual(
            row["raw_text_log"],
            "Successful historical game log",
        )

    def test_successful_raw_file_is_not_downgraded(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir)

            successful_payload = {
                "game": [
                    [
                        "game_log",
                        "Stored successfully",
                    ]
                ]
            }

            error_payload = {
                "error": (
                    "Username and platform "
                    "do not match the game record."
                )
            }

            with patch(
                "src.collector.RAW_GAME_LOG_DIR",
                raw_dir,
            ):
                first_saved = (
                    save_raw_game_log(
                        "game-1",
                        successful_payload,
                    )
                )

                second_saved = (
                    save_raw_game_log(
                        "game-1",
                        error_payload,
                    )
                )

            self.assertTrue(
                first_saved
            )

            self.assertFalse(
                second_saved
            )

            stored = json.loads(
                (
                    raw_dir
                    / "game-1.json"
                ).read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                stored,
                successful_payload,
            )


class BoxScoreParsingTests(
    TemporaryDatabaseTestCase
):
    def test_team_and_pitcher_ip_are_stored_as_outs(
        self,
    ):
        sections = {
            "box_score": [
                {
                    "team_id": "123",
                    "team_name": "Test Team",
                    "r": "3",
                    "h": "7",
                    "e": "0",
                    "123": {
                        "batting_totals": {
                            "ab": "30",
                            "r": "3",
                            "h": "7",
                            "rbi": "3",
                            "bb": "2",
                            "so": "8",
                        },
                        "pitching_totals": {
                            "ip": "5.2",
                            "h": "4",
                            "r": "2",
                            "er": "2",
                            "bb": "1",
                            "so": "6",
                        },
                        "batting_stats": [],
                        "pitching_stats": [
                            {
                                "player_name": (
                                    "Test Pitcher"
                                ),
                                "ip": "5.2",
                                "h": "4",
                                "r": "2",
                                "er": "2",
                                "bb": "1",
                                "so": "6",
                                "win": "1",
                                "loss": "0",
                                "save": "0",
                            }
                        ],
                    },
                }
            ]
        }

        save_box_score_sections(
            self.conn,
            "game-1",
            sections,
        )

        team_row = self.conn.execute(
            """
            SELECT
                pitching_ip,
                pitching_outs
            FROM team_box_scores
            WHERE game_id = ?
            """,
            ("game-1",),
        ).fetchone()

        self.assertIsNotNone(
            team_row
        )

        self.assertEqual(
            team_row["pitching_ip"],
            5.2,
        )

        self.assertEqual(
            team_row["pitching_outs"],
            17,
        )

        pitcher_row = self.conn.execute(
            """
            SELECT
                ip,
                pitching_outs
            FROM player_pitching_stats
            WHERE game_id = ?
            """,
            ("game-1",),
        ).fetchone()

        self.assertIsNotNone(
            pitcher_row
        )

        self.assertEqual(
            pitcher_row["ip"],
            5.2,
        )

        self.assertEqual(
            pitcher_row["pitching_outs"],
            17,
        )

    def test_reparse_replaces_old_parsed_rows(
        self,
    ):
        first_sections = {
            "box_score": [
                {
                    "team_id": "123",
                    "team_name": "Test Team",
                    "r": "1",
                    "h": "3",
                    "e": "0",
                    "123": {
                        "batting_totals": {},
                        "pitching_totals": {
                            "ip": "1.0",
                        },
                        "batting_stats": [],
                        "pitching_stats": [],
                    },
                }
            ]
        }

        second_sections = {
            "box_score": [
                {
                    "team_id": "123",
                    "team_name": "Test Team",
                    "r": "2",
                    "h": "5",
                    "e": "0",
                    "123": {
                        "batting_totals": {},
                        "pitching_totals": {
                            "ip": "2.2",
                        },
                        "batting_stats": [],
                        "pitching_stats": [],
                    },
                }
            ]
        }

        save_box_score_sections(
            self.conn,
            "game-1",
            first_sections,
        )

        save_box_score_sections(
            self.conn,
            "game-1",
            second_sections,
        )

        rows = self.conn.execute(
            """
            SELECT
                runs,
                hits,
                pitching_outs
            FROM team_box_scores
            WHERE game_id = ?
            """,
            ("game-1",),
        ).fetchall()

        self.assertEqual(
            len(rows),
            1,
        )

        self.assertEqual(
            rows[0]["runs"],
            2,
        )

        self.assertEqual(
            rows[0]["hits"],
            5,
        )

        self.assertEqual(
            rows[0]["pitching_outs"],
            8,
        )


class PitchingOutsBackfillTests(
    TemporaryDatabaseTestCase
):
    def build_successful_game_log(
        self,
    ):
        return {
            "game": [
                [
                    "box_score",
                    [
                        {
                            "team_id": "123",
                            "team_name": "Test Team",
                            "r": "3",
                            "h": "7",
                            "e": "0",
                            "123": {
                                "batting_totals": {},
                                "pitching_totals": {
                                    "ip": "5.2",
                                },
                                "batting_stats": [],
                                "pitching_stats": [
                                    {
                                        "player_name": "Test Pitcher",
                                        "ip": "5.2",
                                    }
                                ],
                            },
                        }
                    ],
                ]
            ]
        }

    def test_backfill_reparses_legacy_rows_without_network(
        self,
    ):
        self.insert_game("game-1")

        save_game_log(
            self.conn,
            "game-1",
            self.build_successful_game_log(),
        )

        self.conn.execute(
            """
            UPDATE team_box_scores
            SET pitching_outs = NULL
            WHERE game_id = ?
            """,
            ("game-1",),
        )
        self.conn.execute(
            """
            UPDATE player_pitching_stats
            SET pitching_outs = NULL
            WHERE game_id = ?
            """,
            ("game-1",),
        )
        self.conn.commit()

        self.assertEqual(
            get_game_ids_needing_pitching_outs_backfill(
                self.conn
            ),
            ["game-1"],
        )

        with patch("src.collector.fetch_game_log") as network_fetch:
            summary = backfill_missing_pitching_outs(
                self.conn
            )

        network_fetch.assert_not_called()
        self.assertEqual(
            summary,
            {"found": 1, "reparsed": 1, "failed": 0},
        )

        team_row = self.conn.execute(
            "SELECT pitching_outs FROM team_box_scores WHERE game_id = ?",
            ("game-1",),
        ).fetchone()
        pitcher_row = self.conn.execute(
            "SELECT pitching_outs FROM player_pitching_stats WHERE game_id = ?",
            ("game-1",),
        ).fetchone()

        self.assertEqual(team_row["pitching_outs"], 17)
        self.assertEqual(pitcher_row["pitching_outs"], 17)

    def test_completed_rows_do_not_need_backfill(
        self,
    ):
        self.insert_game("game-1")
        save_game_log(
            self.conn,
            "game-1",
            self.build_successful_game_log(),
        )

        self.assertEqual(
            get_game_ids_needing_pitching_outs_backfill(
                self.conn
            ),
            [],
        )

        summary = backfill_missing_pitching_outs(
            self.conn
        )
        self.assertEqual(
            summary,
            {"found": 0, "reparsed": 0, "failed": 0},
        )


if __name__ == "__main__":
    unittest.main()
