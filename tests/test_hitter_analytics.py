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

    def test_matchup_strikeout_profiles_track_coverage_and_locations(
        self,
    ):
        bucket = create_hitter_bucket(
            "Matchup Batter"
        )

        events = [
            {
                "event_type": "single",
                "is_plate_appearance": True,
                "is_hit": True,
                "hit_bases": 1,
                "matchup": "RvR",
            },
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "is_hit": False,
                "matchup": "RvR",
                "terminal_pitch_type": "slider",
                "terminal_pitch_location": "low_away",
                "strikeout_type": "chasing",
            },
            {
                "event_type": "walk",
                "is_plate_appearance": True,
                "is_hit": False,
                "matchup": "RvL",
            },
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "is_hit": False,
                "matchup": "LvL",
                "terminal_pitch_type": "sinker",
                "terminal_pitch_location": "high_in",
                "strikeout_type": "looking",
            },
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "is_hit": False,
                "terminal_pitch_type": "fastball",
                "terminal_pitch_location": "low",
                "strikeout_type": "chasing",
            },
        ]

        for event in events:
            apply_hitter_event(
                bucket,
                event,
                game_id="game-1",
            )

        row = finalize_hitter_bucket(
            bucket
        )

        profiles = row[
            "matchup_strikeout_profiles"
        ]

        self.assertEqual(
            profiles[
                "classified_plate_appearances"
            ],
            4,
        )

        self.assertEqual(
            profiles[
                "unclassified_plate_appearances"
            ],
            1,
        )

        self.assertEqual(
            profiles[
                "coverage_pct"
            ],
            80.0,
        )

        self.assertEqual(
            profiles[
                "classified_strikeouts"
            ],
            2,
        )

        self.assertEqual(
            profiles[
                "unclassified_strikeouts"
            ],
            1,
        )

        self.assertEqual(
            profiles[
                "strikeout_coverage_pct"
            ],
            66.7,
        )

        rvr = profiles[
            "matchups"
        ]["RvR"]

        self.assertEqual(
            rvr["plate_appearances"],
            2,
        )

        self.assertEqual(
            rvr["strikeouts"],
            1,
        )

        self.assertEqual(
            rvr["strikeout_pct"],
            50.0,
        )

        self.assertEqual(
            rvr["with_location"],
            1,
        )

        self.assertEqual(
            rvr[
                "location_coverage_pct"
            ],
            100.0,
        )

        self.assertEqual(
            rvr["location_counts"],
            {
                "high_in": 0,
                "high": 0,
                "high_away": 0,
                "inside": 0,
                "middle": 0,
                "outside": 0,
                "low_in": 0,
                "low": 0,
                "low_away": 1,
            },
        )

        self.assertEqual(
            rvr["finishing_pitches"],
            [
                {
                    "value": "slider",
                    "count": 1,
                    "pct": 100.0,
                }
            ],
        )

        rvl = profiles[
            "matchups"
        ]["RvL"]

        self.assertEqual(
            rvl["plate_appearances"],
            1,
        )

        self.assertEqual(
            rvl["strikeouts"],
            0,
        )

        self.assertEqual(
            rvl["strikeout_pct"],
            0.0,
        )

        self.assertIsNone(
            rvl[
                "location_coverage_pct"
            ]
        )

        lvl = profiles[
            "matchups"
        ]["LvL"]

        self.assertEqual(
            lvl["strikeouts"],
            1,
        )

        self.assertEqual(
            lvl["location_counts"][
                "high_in"
            ],
            1,
        )

        lvr = profiles[
            "matchups"
        ]["LvR"]

        self.assertEqual(
            lvr["plate_appearances"],
            0,
        )

        self.assertIsNone(
            lvr["strikeout_pct"]
        )

    def test_matchup_location_tracks_finishing_pitch_breakdown(
        self,
    ):
        bucket = create_hitter_bucket(
            "Hover Batter"
        )

        events = [
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "matchup": "RvR",
                "terminal_pitch_location": "low_away",
                "terminal_pitch_type": "slider",
            },
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "matchup": "RvR",
                "terminal_pitch_location": "low_away",
                "terminal_pitch_type": "slider",
            },
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "matchup": "RvR",
                "terminal_pitch_location": "low_away",
                "terminal_pitch_type": "fastball",
            },
            {
                "event_type": "strikeout",
                "is_plate_appearance": True,
                "matchup": "RvR",
                "terminal_pitch_location": "low_away",
                "terminal_pitch_type": None,
            },
        ]

        for event in events:
            apply_hitter_event(
                bucket,
                event,
                game_id="hover-game",
            )

        row = finalize_hitter_bucket(
            bucket
        )

        rvr = row[
            "matchup_strikeout_profiles"
        ][
            "matchups"
        ][
            "RvR"
        ]

        self.assertEqual(
            rvr[
                "location_counts"
            ][
                "low_away"
            ],
            4,
        )

        self.assertEqual(
            rvr[
                "location_pitch_counts"
            ][
                "low_away"
            ],
            {
                "slider": 2,
                "fastball": 1,
            },
        )

    def test_empty_matchup_profiles_have_stable_four_matchup_shape(
        self,
    ):
        bucket = create_hitter_bucket(
            "Empty Batter"
        )

        row = finalize_hitter_bucket(
            bucket
        )

        profiles = row[
            "matchup_strikeout_profiles"
        ]

        self.assertEqual(
            list(
                profiles[
                    "matchups"
                ].keys()
            ),
            [
                "RvR",
                "RvL",
                "LvR",
                "LvL",
            ],
        )

        self.assertIsNone(
            profiles["coverage_pct"]
        )

        for matchup in (
            profiles[
                "matchups"
            ].values()
        ):
            self.assertEqual(
                matchup[
                    "plate_appearances"
                ],
                0,
            )

            self.assertEqual(
                sum(
                    matchup[
                        "location_counts"
                    ].values()
                ),
                0,
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
