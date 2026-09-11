import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import src.api as api
from src.database import connect_db, init_db


class DormantThread:
    def __init__(self, *, target, args, daemon):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        return None


class ApiRouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "api-routes.sqlite3"

        self.db_path_patch = patch.object(api, "DB_PATH", self.db_path)
        self.db_path_patch.start()

        with api._sync_job_lock:
            api._sync_jobs.clear()
            api._active_sync_job_id = None
            api._latest_sync_job_id = None

        self.client_context = TestClient(api.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

        with api._sync_job_lock:
            api._sync_jobs.clear()
            api._active_sync_job_id = None
            api._latest_sync_job_id = None

        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def insert_game(
        self,
        *,
        game_id: str,
        display_date: str,
        opponent_name: str,
        opponent_team_name: str,
        result: str,
        user_is_home: bool,
        user_runs: int,
        opponent_runs: int,
    ) -> None:
        conn = connect_db(self.db_path)
        init_db(conn)

        if user_is_home:
            home_name = api.USERNAME
            away_name = opponent_name
            home_runs = user_runs
            away_runs = opponent_runs
            home_full_name = "Configured Team"
            away_full_name = opponent_team_name
        else:
            home_name = opponent_name
            away_name = api.USERNAME
            home_runs = opponent_runs
            away_runs = user_runs
            home_full_name = opponent_team_name
            away_full_name = "Configured Team"

        conn.execute(
            """
            INSERT INTO games (
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
                opponent_team_name,
                raw_game_history_json
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                game_id,
                display_date,
                "arena",
                home_full_name,
                away_full_name,
                home_name,
                away_name,
                home_runs,
                away_runs,
                8,
                6,
                0,
                1,
                result,
                opponent_name,
                opponent_team_name,
                '{"fixture": true}',
            ),
        )
        conn.commit()
        conn.close()

    def test_health_and_config_endpoints(self):
        health = self.client.get("/health")
        config = self.client.get("/config")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(config.status_code, 200)
        self.assertEqual(
            config.json(),
            {
                "username": api.USERNAME,
                "platform": api.PLATFORM,
                "mode": api.MODE,
            },
        )

    def test_games_route_filters_and_paginates(self):
        self.insert_game(
            game_id="game-1",
            display_date="2026-01-01 12:00:00",
            opponent_name="Alpha",
            opponent_team_name="A Team",
            result="W",
            user_is_home=True,
            user_runs=5,
            opponent_runs=2,
        )
        self.insert_game(
            game_id="game-2",
            display_date="2026-01-02 12:00:00",
            opponent_name="Beta",
            opponent_team_name="B Team",
            result="L",
            user_is_home=False,
            user_runs=3,
            opponent_runs=4,
        )
        self.insert_game(
            game_id="game-3",
            display_date="2026-01-03 12:00:00",
            opponent_name="AlphaTwo",
            opponent_team_name="C Team",
            result="W",
            user_is_home=True,
            user_runs=7,
            opponent_runs=1,
        )

        response = self.client.get(
            "/games",
            params={
                "opponent": "alpha",
                "result": "W",
                "limit": 1,
                "offset": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["limit"], 1)
        self.assertEqual(payload["offset"], 1)
        self.assertEqual(
            [game["id"] for game in payload["games"]],
            ["game-1"],
        )

    def test_game_detail_route_returns_nested_data(self):
        self.insert_game(
            game_id="game-detail",
            display_date="2026-02-01 12:00:00",
            opponent_name="DetailOpponent",
            opponent_team_name="Detail Team",
            result="W",
            user_is_home=True,
            user_runs=6,
            opponent_runs=3,
        )

        conn = connect_db(self.db_path)
        init_db(conn)

        conn.execute(
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
                "game-detail",
                "2026-02-01T13:00:00Z",
                "ok",
                '{"game": []}',
                "Test log",
            ),
        )

        conn.execute(
            """
            INSERT INTO team_box_scores (
                game_id,
                team_id,
                team_name,
                runs,
                hits,
                errors,
                pitching_outs
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "game-detail",
                "team-1",
                "Configured Team",
                6,
                8,
                0,
                27,
            ),
        )

        conn.execute(
            """
            INSERT INTO player_batting_stats (
                game_id,
                team_id,
                team_name,
                player_name,
                ab,
                h,
                hr
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "game-detail",
                "team-1",
                "Configured Team",
                "Fixture Batter",
                4,
                2,
                1,
            ),
        )

        conn.execute(
            """
            INSERT INTO player_pitching_stats (
                game_id,
                team_id,
                team_name,
                player_name,
                ip,
                pitching_outs,
                er,
                so
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "game-detail",
                "team-1",
                "Configured Team",
                "Fixture Pitcher",
                9.0,
                27,
                3,
                8,
            ),
        )

        conn.commit()
        conn.close()

        response = self.client.get("/games/game-detail")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["game"]["id"], "game-detail")
        self.assertEqual(payload["game_log"]["api_status"], "ok")
        self.assertEqual(
            payload["team_box_scores"][0]["pitching_outs"],
            27,
        )
        self.assertEqual(
            payload["batting_stats"][0]["player_name"],
            "Fixture Batter",
        )
        self.assertEqual(
            payload["pitching_stats"][0]["player_name"],
            "Fixture Pitcher",
        )

    def test_game_detail_route_returns_404(self):
        response = self.client.get("/games/missing-game")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Game not found")

    def test_dashboard_route_returns_counts_and_record(self):
        self.insert_game(
            game_id="dash-1",
            display_date="2026-03-01 12:00:00",
            opponent_name="OpponentOne",
            opponent_team_name="Team One",
            result="W",
            user_is_home=True,
            user_runs=5,
            opponent_runs=2,
        )
        self.insert_game(
            game_id="dash-2",
            display_date="2026-03-02 12:00:00",
            opponent_name="OpponentTwo",
            opponent_team_name="Team Two",
            result="L",
            user_is_home=False,
            user_runs=3,
            opponent_runs=4,
        )

        conn = connect_db(self.db_path)
        init_db(conn)
        conn.execute(
            """
            INSERT INTO game_logs (
                game_id,
                fetched_at,
                api_status
            )
            VALUES (?, ?, ?)
            """,
            (
                "dash-1",
                "2026-03-01T13:00:00Z",
                "ok",
            ),
        )
        conn.commit()
        conn.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["total_games"], 2)
        self.assertEqual(payload["total_game_logs"], 1)
        self.assertEqual(payload["successful_game_logs"], 1)
        self.assertEqual(
            payload["record"],
            {
                "wins": 1,
                "losses": 1,
                "win_pct": 0.5,
            },
        )
        self.assertEqual(payload["averages"]["runs_scored"], 4.0)
        self.assertEqual(payload["averages"]["runs_allowed"], 3.0)

    def test_opponents_route_groups_and_averages(self):
        self.insert_game(
            game_id="opp-1",
            display_date="2026-04-01 12:00:00",
            opponent_name="RepeatOpponent",
            opponent_team_name="Repeat Team",
            result="W",
            user_is_home=True,
            user_runs=6,
            opponent_runs=2,
        )
        self.insert_game(
            game_id="opp-2",
            display_date="2026-04-02 12:00:00",
            opponent_name="RepeatOpponent",
            opponent_team_name="Repeat Team",
            result="L",
            user_is_home=False,
            user_runs=2,
            opponent_runs=4,
        )

        response = self.client.get("/opponents")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)

        opponent = payload["opponents"][0]
        self.assertEqual(opponent["games_played"], 2)
        self.assertEqual(opponent["your_wins"], 1)
        self.assertEqual(opponent["your_losses"], 1)
        self.assertEqual(opponent["avg_runs_scored"], 4.0)
        self.assertEqual(opponent["avg_runs_allowed"], 3.0)

    def test_sync_job_read_routes(self):
        active = self.client.get("/sync/jobs/active")
        latest = self.client.get("/sync/jobs/latest")
        missing = self.client.get("/sync/jobs/not-a-real-job")

        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.json(), {"job": None})
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.json(), {"job": None})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"],
            "Sync job not found.",
        )

    def test_sync_job_start_and_conflict_route(self):
        with patch.object(api, "Thread", DormantThread):
            first = self.client.post(
                "/sync/jobs",
                json={"type": "logs"},
            )
            second = self.client.post(
                "/sync/jobs",
                json={"type": "history"},
            )

        self.assertEqual(first.status_code, 202)
        first_payload = first.json()
        self.assertEqual(first_payload["type"], "logs")
        self.assertEqual(first_payload["status"], "queued")

        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            second.json()["detail"]["job_id"],
            first_payload["id"],
        )

        fetched = self.client.get(
            f"/sync/jobs/{first_payload['id']}"
        )
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(
            fetched.json()["id"],
            first_payload["id"],
        )

    def test_invalid_sync_type_returns_422(self):
        response = self.client.post(
            "/sync/jobs",
            json={"type": "invalid"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
