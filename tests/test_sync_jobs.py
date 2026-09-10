import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

import src.api as api
from src.collector import sync_game_logs
from src.database import connect_db, init_db


class ImmediateThread:
    def __init__(
        self,
        *,
        target,
        args,
        daemon,
    ):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        self.target(*self.args)


class DormantThread:
    def __init__(
        self,
        *,
        target,
        args,
        daemon,
    ):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        return None


class SyncJobTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp_dir = (
            tempfile.TemporaryDirectory()
        )
        self.db_path = (
            Path(self.temp_dir.name)
            / "sync-jobs.sqlite3"
        )

        with api._sync_job_lock:
            api._sync_jobs.clear()
            api._active_sync_job_id = None
            api._latest_sync_job_id = None

    def tearDown(self):
        with api._sync_job_lock:
            api._sync_jobs.clear()
            api._active_sync_job_id = None
            api._latest_sync_job_id = None

        self.temp_dir.cleanup()

    def test_all_job_records_progress_and_results(
        self,
    ):
        summary = {
            "requested": 2,
            "ok": 2,
            "identity_mismatch": 0,
            "not_found": 0,
            "api_error": 0,
            "request_failed": 0,
            "preserved_ok": 0,
        }

        def fake_history(_conn):
            return [
                {"id": "game-1"},
                {"id": "game-2"},
            ]

        def fake_logs(
            _conn,
            progress_callback=None,
        ):
            if progress_callback:
                progress_callback(
                    {
                        "current": 0,
                        "total": 2,
                        "game_id": None,
                        "summary": {
                            **summary,
                            "ok": 0,
                        },
                    }
                )
                progress_callback(
                    {
                        "current": 1,
                        "total": 2,
                        "game_id": "game-1",
                        "summary": {
                            **summary,
                            "ok": 1,
                        },
                    }
                )
                progress_callback(
                    {
                        "current": 2,
                        "total": 2,
                        "game_id": "game-2",
                        "summary": summary,
                    }
                )

            return summary

        with (
            patch.object(
                api,
                "DB_PATH",
                self.db_path,
            ),
            patch.object(
                api,
                "Thread",
                ImmediateThread,
            ),
            patch.object(
                api,
                "sync_game_history",
                side_effect=fake_history,
            ),
            patch.object(
                api,
                "sync_game_logs",
                side_effect=fake_logs,
            ),
        ):
            job = api._start_sync_job(
                "all"
            )

        self.assertEqual(
            job["status"],
            "completed",
        )
        self.assertEqual(
            job["phase"],
            "complete",
        )
        self.assertEqual(
            job["human_games"],
            2,
        )
        self.assertEqual(
            job["progress_current"],
            2,
        )
        self.assertEqual(
            job["progress_total"],
            2,
        )
        self.assertEqual(
            job["log_summary"],
            summary,
        )
        self.assertIsNone(
            api._get_active_sync_job_snapshot()
        )

    def test_second_active_job_is_rejected(
        self,
    ):
        with patch.object(
            api,
            "Thread",
            DormantThread,
        ):
            first = api._start_sync_job(
                "logs"
            )

            with self.assertRaises(
                HTTPException
            ) as context:
                api._start_sync_job(
                    "history"
                )

        self.assertEqual(
            context.exception.status_code,
            409,
        )
        self.assertEqual(
            context.exception.detail[
                "job_id"
            ],
            first["id"],
        )

    def test_failed_job_records_error(
        self,
    ):
        def fail_history(_conn):
            raise RuntimeError(
                "history exploded"
            )

        with (
            patch.object(
                api,
                "DB_PATH",
                self.db_path,
            ),
            patch.object(
                api,
                "Thread",
                ImmediateThread,
            ),
            patch.object(
                api,
                "sync_game_history",
                side_effect=fail_history,
            ),
        ):
            job = api._start_sync_job(
                "history"
            )

        self.assertEqual(
            job["status"],
            "failed",
        )
        self.assertIn(
            "history exploded",
            job["error"],
        )
        self.assertIsNone(
            api._get_active_sync_job_snapshot()
        )


class CollectorProgressTests(
    unittest.TestCase
):
    def test_sync_game_logs_emits_progress(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = (
                Path(temp_dir)
                / "collector.sqlite3"
            )

            conn = connect_db(
                db_path
            )
            init_db(conn)

            conn.execute(
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
                    "game-1",
                    "2026-01-01 12:00:00",
                    "Home Team",
                    "Away Team",
                    "ConfiguredUser",
                    "OpponentUser",
                ),
            )
            conn.commit()

            events = []

            with (
                patch(
                    "src.collector.get_unfetched_game_ids",
                    return_value=["game-1"],
                ),
                patch(
                    "src.collector.create_session"
                ),
                patch(
                    "src.collector.fetch_game_log",
                    return_value={
                        "game": [],
                    },
                ),
                patch(
                    "src.collector.save_raw_game_log",
                    return_value=True,
                ),
                patch(
                    "src.collector.time.sleep"
                ),
            ):
                summary = sync_game_logs(
                    conn,
                    progress_callback=events.append,
                )

            conn.close()

        self.assertEqual(
            summary["requested"],
            1,
        )
        self.assertEqual(
            summary["ok"],
            1,
        )
        self.assertEqual(
            len(events),
            2,
        )
        self.assertEqual(
            events[0]["current"],
            0,
        )
        self.assertEqual(
            events[0]["total"],
            1,
        )
        self.assertEqual(
            events[1]["current"],
            1,
        )
        self.assertEqual(
            events[1]["game_id"],
            "game-1",
        )
        self.assertEqual(
            events[1]["summary"]["ok"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
