import unittest

from src.hitter_analytics import (
    apply_hitter_event,
    create_hitter_bucket,
    finalize_hitter_bucket,
    finalize_hitter_buckets,
    hitter_event_is_relevant,
)


class HitterEventRelevanceTests(
    unittest.TestCase
):
    def test_plate_appearances_and_tracked_runner_events_are_relevant(
        self,
    ):
        self.assertTrue(
            hitter_event_is_relevant(
                {
                    "event_type": "single",
                    "is_plate_appearance": True,
                }
            )
        )

        self.assertTrue(
            hitter_event_is_relevant(
                {
                    "event_type": "runner_scored",
                    "is_plate_appearance": False,
                }
            )
        )

        self.assertFalse(
            hitter_event_is_relevant(
                {
                    "event_type": "pitcher_marker",
                    "is_plate_appearance": False,
                }
            )
        )


class HitterAggregationTests(
    unittest.TestCase
):
    def test_shared_bucket_calculates_stats_and_strikeout_tendencies(
        self,
    ):
        bucket = create_hitter_bucket(
            "Test Batter",
            team_name="Test Team",
        )

        events = [
            (
                "game-1",
                {
                    "event_type": "single",
                    "is_plate_appearance": True,
                    "is_hit": True,
                    "hit_bases": 1,
                },
            ),
            (
                "game-1",
                {
                    "event_type": "walk",
                    "is_plate_appearance": True,
                    "is_hit": False,
                    "cause": None,
                },
            ),
            (
                "game-1",
                {
                    "event_type": "strikeout",
                    "is_plate_appearance": True,
                    "is_hit": False,
                    "terminal_pitch_type": "slider",
                    "terminal_pitch_location": "low_away",
                    "strikeout_type": "chasing",
                },
            ),
            (
                "game-1",
                {
                    "event_type": "runner_scored",
                    "is_plate_appearance": False,
                },
            ),
            (
                "game-2",
                {
                    "event_type": "home_run",
                    "is_plate_appearance": True,
                    "is_hit": True,
                    "hit_bases": 4,
                },
            ),
            (
                "game-2",
                {
                    "event_type": "strikeout",
                    "is_plate_appearance": True,
                    "is_hit": False,
                    "terminal_pitch_type": "slider",
                    "terminal_pitch_location": "high_in",
                    "strikeout_type": "looking",
                },
            ),
        ]

        for game_id, event in events:
            apply_hitter_event(
                bucket,
                event,
                game_id=game_id,
            )

        row = finalize_hitter_bucket(
            bucket
        )

        self.assertEqual(
            row["player_name"],
            "Test Batter",
        )
        self.assertEqual(
            row["team_name"],
            "Test Team",
        )
        self.assertEqual(
            row["games"],
            2,
        )
        self.assertEqual(
            row["plate_appearances"],
            5,
        )
        self.assertEqual(
            row["at_bats"],
            4,
        )
        self.assertEqual(
            row["hits"],
            2,
        )
        self.assertEqual(
            row["singles"],
            1,
        )
        self.assertEqual(
            row["home_runs"],
            1,
        )
        self.assertEqual(
            row["walks"],
            1,
        )
        self.assertEqual(
            row["strikeouts"],
            2,
        )
        self.assertEqual(
            row["runs"],
            1,
        )
        self.assertEqual(
            row["batting_average"],
            0.5,
        )
        self.assertEqual(
            row["walk_pct"],
            20.0,
        )
        self.assertEqual(
            row["strikeout_pct"],
            40.0,
        )
        self.assertEqual(
            row["home_run_pct"],
            20.0,
        )

        tendencies = row[
            "strikeout_tendencies"
        ]

        self.assertEqual(
            tendencies[
                "with_finishing_pitch"
            ],
            2,
        )
        self.assertEqual(
            tendencies[
                "finishing_pitches"
            ],
            [
                {
                    "value": "slider",
                    "count": 2,
                    "pct": 100.0,
                }
            ],
        )
        self.assertEqual(
            tendencies[
                "locations"
            ],
            [
                {
                    "value": "high_in",
                    "count": 1,
                    "pct": 50.0,
                },
                {
                    "value": "low_away",
                    "count": 1,
                    "pct": 50.0,
                },
            ],
        )
        self.assertEqual(
            tendencies[
                "styles"
            ],
            [
                {
                    "value": "chasing",
                    "count": 1,
                    "pct": 50.0,
                },
                {
                    "value": "looking",
                    "count": 1,
                    "pct": 50.0,
                },
            ],
        )

    def test_shared_bucket_sort_matches_scout_order(
        self,
    ):
        buckets = {}

        for (
            name,
            plate_appearances,
            home_runs,
        ) in (
            ("Alpha", 2, 0),
            ("Beta", 2, 1),
            ("Gamma", 3, 0),
        ):
            bucket = create_hitter_bucket(
                name
            )

            bucket[
                "plate_appearances"
            ] = plate_appearances
            bucket[
                "home_runs"
            ] = home_runs

            buckets[
                name.casefold()
            ] = bucket

        rows = finalize_hitter_buckets(
            buckets
        )

        self.assertEqual(
            [
                row["player_name"]
                for row in rows
            ],
            [
                "Gamma",
                "Beta",
                "Alpha",
            ],
        )


if __name__ == "__main__":
    unittest.main()
