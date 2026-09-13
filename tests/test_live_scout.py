import unittest
from unittest.mock import patch

from src.live_scout import (
    LiveScoutConfig,
    aggregate_live_hitter_profiles,
    attribute_live_event_sides,
    build_live_scout_report,
    fetch_and_parse_log_for_game,
    fetch_live_log_stats_concurrently,
    parse_live_log_stats_for_username,
    parse_live_normalized_events,
    resolve_live_history_platform,
    resolve_live_log_platform,
)


def make_game_log(
    *,
    home_name: str,
    away_name: str,
):
    return {
        "game": [
            [
                "line_score",
                {
                    "home_name": home_name,
                    "away_name": away_name,
                    "home_mlb_team_id": "8507077",
                    "away_mlb_team_id": "32529",
                },
            ],
            [
                "box_score",
                [
                    {
                        "team_id": "8507077",
                        "team_name": "Vols",
                        "8507077": {
                            "batting_totals": {
                                "ab": "30",
                                "h": "3",
                            },
                            "pitching_totals": {
                                "ip": "9.0",
                                "er": "2",
                            },
                        },
                    },
                    {
                        "team_id": "32529",
                        "team_name": "Rapids",
                        "32529": {
                            "batting_totals": {
                                "ab": "28",
                                "h": "7",
                            },
                            "pitching_totals": {
                                "ip": "9.0",
                                "er": "1",
                            },
                        },
                    },
                ],
            ],
        ],
    }


def make_game_log_with_text(
    *,
    home_name: str,
    away_name: str,
):
    payload = make_game_log(
        home_name=home_name,
        away_name=away_name,
    )

    payload["game"].append(
        [
            "game_log",
            (
                "^c51^Inning 1:^c50^^n^"
                "Scout Team batting. "
                "Batter struck out chasing "
                "a slider low and away. "
                "Runs: 0 Hits: 0 Walks: 0 "
                "Errors: 0 Pitches: 4 "
                "Runners Left On: 0"
            ),
        ]
    )

    return payload


class LiveScoutHistoryPlatformResolutionTests(
    unittest.TestCase
):
    @patch(
        "src.live_scout.time.sleep"
    )
    @patch(
        "src.live_scout.fetch_json"
    )
    def test_history_resolver_falls_back_to_attributable_platform(
        self,
        mock_fetch_json,
        mock_sleep,
    ):
        preferred_payload = {
            "total_pages": 1,
            "game_history": [
                {
                    "id": "wrong-user",
                    "home_name": "SomeoneElse",
                    "away_name": "AnotherUser",
                    "home_full_name": "Home Team",
                    "away_full_name": "Away Team",
                }
            ],
        }

        resolved_payload = {
            "total_pages": 2,
            "game_history": [
                {
                    "id": "game-1",
                    "home_name": "ScoutUser",
                    "away_name": "Opponent",
                    "home_full_name": "Scout Team",
                    "away_full_name": "Opponent Team",
                }
            ],
        }

        def fake_fetch(
            session,
            url,
            params=None,
        ):
            self.assertIsNotNone(
                session
            )
            self.assertIn(
                "game_history.json",
                url,
            )

            if params[
                "platform"
            ] == "xbl":
                return (
                    resolved_payload
                )

            return (
                preferred_payload
            )

        mock_fetch_json.side_effect = (
            fake_fetch
        )

        (
            resolved_platform,
            first_page,
        ) = resolve_live_history_platform(
            session=object(),
            username="ScoutUser",
            preferred_platform="psn",
            mode="arena",
        )

        self.assertEqual(
            resolved_platform,
            "xbl",
        )
        self.assertIs(
            first_page,
            resolved_payload,
        )

        self.assertEqual(
            [
                call.kwargs[
                    "params"
                ][
                    "platform"
                ]
                for call
                in mock_fetch_json.call_args_list
            ],
            [
                "psn",
                "xbl",
            ],
        )

        self.assertEqual(
            mock_sleep.call_count,
            1,
        )

    @patch(
        "src.live_scout.fetch_json"
    )
    def test_history_resolver_keeps_preferred_when_attributable(
        self,
        mock_fetch_json,
    ):
        preferred_payload = {
            "total_pages": 1,
            "game_history": [
                {
                    "id": "game-1",
                    "home_name": "ScoutUser",
                    "away_name": "Opponent",
                    "home_full_name": "Scout Team",
                    "away_full_name": "Opponent Team",
                }
            ],
        }

        mock_fetch_json.return_value = (
            preferred_payload
        )

        (
            resolved_platform,
            first_page,
        ) = resolve_live_history_platform(
            session=object(),
            username="ScoutUser",
            preferred_platform="psn",
            mode="arena",
        )

        self.assertEqual(
            resolved_platform,
            "psn",
        )
        self.assertIs(
            first_page,
            preferred_payload,
        )
        self.assertEqual(
            mock_fetch_json.call_count,
            1,
        )

    @patch(
        "src.live_scout.fetch_live_log_stats_concurrently"
    )
    @patch(
        "src.live_scout.fetch_game_history_for_user"
    )
    @patch(
        "src.live_scout.resolve_live_history_platform"
    )
    @patch(
        "src.live_scout.create_live_session"
    )
    def test_report_uses_resolved_history_platform(
        self,
        mock_create_session,
        mock_resolve_history,
        mock_fetch_history,
        mock_fetch_logs,
    ):
        session = object()
        probe_payload = {
            "total_pages": 1,
            "game_history": [],
        }

        mock_create_session.return_value = (
            session
        )
        mock_resolve_history.return_value = (
            "xbl",
            probe_payload,
        )
        mock_fetch_history.return_value = (
            [],
            1,
        )
        mock_fetch_logs.return_value = {
            "logs_requested": True,
            "game_log_platform": "psn",
        }

        report = build_live_scout_report(
            LiveScoutConfig(
                username="ScoutUser",
                platform="psn",
                mode="arena",
                max_pages=2,
                max_games=5,
                include_logs=True,
                log_workers=3,
            )
        )

        self.assertEqual(
            report["platform"],
            "psn",
        )
        self.assertEqual(
            report[
                "history_platform"
            ],
            "xbl",
        )

        history_kwargs = (
            mock_fetch_history
            .call_args
            .kwargs
        )

        self.assertIs(
            history_kwargs[
                "session"
            ],
            session,
        )
        self.assertEqual(
            history_kwargs[
                "platform"
            ],
            "xbl",
        )
        self.assertIs(
            history_kwargs[
                "first_page"
            ],
            probe_payload,
        )

        log_kwargs = (
            mock_fetch_logs
            .call_args
            .kwargs
        )

        self.assertEqual(
            log_kwargs[
                "platform"
            ],
            "xbl",
        )


class LiveScoutPlatformResolutionTests(
    unittest.TestCase
):
    @patch(
        "src.live_scout.create_live_session"
    )
    @patch(
        "src.live_scout.fetch_game_log_for_user"
    )
    def test_resolver_falls_back_to_working_platform(
        self,
        mock_fetch_log,
        mock_create_session,
    ):
        mock_create_session.return_value = (
            object()
        )

        def fake_fetch(
            *,
            session,
            game_id,
            username,
            platform,
        ):
            self.assertIsNotNone(
                session
            )
            self.assertEqual(
                game_id,
                "game-1",
            )
            self.assertEqual(
                username,
                "ScoutUser",
            )

            if platform == "psn":
                return {
                    "game": [],
                }

            return {
                "error": (
                    "Username and platform "
                    "do not match the game record."
                )
            }

        mock_fetch_log.side_effect = (
            fake_fetch
        )

        resolved = (
            resolve_live_log_platform(
                games=[
                    {
                        "id": "game-1",
                    }
                ],
                username="ScoutUser",
                preferred_platform="xbl",
            )
        )

        self.assertEqual(
            resolved,
            "psn",
        )

        self.assertEqual(
            [
                call.kwargs[
                    "platform"
                ]
                for call in (
                    mock_fetch_log
                    .call_args_list
                )
            ],
            [
                "xbl",
                "psn",
            ],
        )

    @patch(
        "src.live_scout.create_live_session"
    )
    @patch(
        "src.live_scout.fetch_game_log_for_user"
    )
    def test_resolver_keeps_preferred_platform_when_valid(
        self,
        mock_fetch_log,
        mock_create_session,
    ):
        mock_create_session.return_value = (
            object()
        )

        mock_fetch_log.return_value = {
            "game": [],
        }

        resolved = (
            resolve_live_log_platform(
                games=[
                    {
                        "id": "game-1",
                    }
                ],
                username="ScoutUser",
                preferred_platform="xbl",
            )
        )

        self.assertEqual(
            resolved,
            "xbl",
        )
        self.assertEqual(
            mock_fetch_log.call_count,
            1,
        )


class LiveScoutConcurrentAggregationTests(
    unittest.TestCase
):
    @patch(
        "src.live_scout.resolve_live_log_platform",
        return_value="psn",
    )
    @patch(
        "src.live_scout.fetch_and_parse_log_for_game"
    )
    def test_concurrent_fetch_includes_hitter_profiles(
        self,
        mock_fetch_game,
        mock_resolve_platform,
    ):
        mock_fetch_game.side_effect = [
            {
                "game_id": "game-1",
                "success": True,
                "error": None,
                "user_side": "home",
                "stats": {
                    "batting_ab": 3,
                    "batting_h": 1,
                    "pitching_outs": 27,
                    "pitching_er": 2,
                },
                "events": [
                    {
                        "batting_side": "home",
                        "event_type": "single",
                        "player_name": "Live Batter",
                        "is_plate_appearance": True,
                        "is_hit": True,
                        "hit_bases": 1,
                    },
                    {
                        "batting_side": "home",
                        "event_type": "strikeout",
                        "player_name": "Live Batter",
                        "is_plate_appearance": True,
                        "is_hit": False,
                        "terminal_pitch_type": "slider",
                        "terminal_pitch_location": "low_away",
                        "strikeout_type": "chasing",
                    },
                ],
            },
            {
                "game_id": "game-2",
                "success": True,
                "error": None,
                "user_side": "away",
                "stats": {
                    "batting_ab": 4,
                    "batting_h": 2,
                    "pitching_outs": 27,
                    "pitching_er": 1,
                },
                "events": [
                    {
                        "batting_side": "away",
                        "event_type": "home_run",
                        "player_name": "Live Batter",
                        "is_plate_appearance": True,
                        "is_hit": True,
                        "hit_bases": 4,
                    },
                ],
            },
        ]

        report = (
            fetch_live_log_stats_concurrently(
                games=[
                    {"id": "game-1"},
                    {"id": "game-2"},
                ],
                username="ScoutUser",
                platform="psn",
                max_workers=2,
            )
        )

        self.assertEqual(
            report["logs_fetched"],
            2,
        )
        self.assertEqual(
            report["logs_failed"],
            0,
        )
        self.assertEqual(
            report[
                "game_log_platform"
            ],
            "psn",
        )

        mock_resolve_platform.assert_called_once()

        self.assertTrue(
            all(
                call.args[2]
                == "psn"
                for call in (
                    mock_fetch_game
                    .call_args_list
                )
            )
        )

        self.assertEqual(
            report["batting_ab"],
            7,
        )
        self.assertEqual(
            report["batting_h"],
            3,
        )

        profiles = report[
            "hitter_profiles"
        ]

        self.assertEqual(
            profiles["games_included"],
            2,
        )
        self.assertEqual(
            len(
                profiles["players"]
            ),
            1,
        )

        player = profiles[
            "players"
        ][0]

        self.assertEqual(
            player["player_name"],
            "Live Batter",
        )
        self.assertEqual(
            player["games"],
            2,
        )
        self.assertEqual(
            player["plate_appearances"],
            3,
        )
        self.assertEqual(
            player["hits"],
            2,
        )
        self.assertEqual(
            player["home_runs"],
            1,
        )
        self.assertEqual(
            player["strikeouts"],
            1,
        )
        self.assertEqual(
            player[
                "strikeout_tendencies"
            ][
                "finishing_pitches"
            ][0][
                "value"
            ],
            "slider",
        )


class LiveScoutHitterProfileTests(
    unittest.TestCase
):
    def test_profiles_use_only_searched_users_batting_side(
        self,
    ):
        results = [
            {
                "game_id": "game-1",
                "success": True,
                "user_side": "home",
                "events": [
                    {
                        "batting_side": "home",
                        "event_type": "single",
                        "player_name": "Star Batter",
                        "is_plate_appearance": True,
                        "is_hit": True,
                        "hit_bases": 1,
                    },
                    {
                        "batting_side": "home",
                        "event_type": "strikeout",
                        "player_name": "Star Batter",
                        "is_plate_appearance": True,
                        "is_hit": False,
                        "terminal_pitch_type": "slider",
                        "terminal_pitch_location": "low_away",
                        "strikeout_type": "chasing",
                    },
                    {
                        "batting_side": "away",
                        "event_type": "home_run",
                        "player_name": "Other Batter",
                        "is_plate_appearance": True,
                        "is_hit": True,
                        "hit_bases": 4,
                    },
                ],
            },
            {
                "game_id": "game-2",
                "success": True,
                "user_side": "away",
                "events": [
                    {
                        "batting_side": "away",
                        "event_type": "walk",
                        "player_name": "Star Batter",
                        "is_plate_appearance": True,
                        "is_hit": False,
                        "cause": None,
                    },
                    {
                        "batting_side": "away",
                        "event_type": "home_run",
                        "player_name": "Star Batter",
                        "is_plate_appearance": True,
                        "is_hit": True,
                        "hit_bases": 4,
                    },
                ],
            },
            {
                "game_id": "empty-log",
                "success": True,
                "user_side": "home",
                "events": [],
            },
            {
                "game_id": "failed",
                "success": False,
                "user_side": "home",
                "events": [
                    {
                        "batting_side": "home",
                        "event_type": "home_run",
                        "player_name": "Ignored Batter",
                        "is_plate_appearance": True,
                        "is_hit": True,
                        "hit_bases": 4,
                    },
                ],
            },
        ]

        report = (
            aggregate_live_hitter_profiles(
                results
            )
        )

        self.assertEqual(
            report["games_included"],
            2,
        )
        self.assertEqual(
            len(
                report[
                    "players"
                ]
            ),
            1,
        )

        player = report[
            "players"
        ][0]

        self.assertEqual(
            player[
                "player_name"
            ],
            "Star Batter",
        )
        self.assertEqual(
            player["games"],
            2,
        )
        self.assertEqual(
            player[
                "plate_appearances"
            ],
            4,
        )
        self.assertEqual(
            player[
                "at_bats"
            ],
            3,
        )
        self.assertEqual(
            player["hits"],
            2,
        )
        self.assertEqual(
            player["singles"],
            1,
        )
        self.assertEqual(
            player[
                "home_runs"
            ],
            1,
        )
        self.assertEqual(
            player["walks"],
            1,
        )
        self.assertEqual(
            player[
                "strikeouts"
            ],
            1,
        )
        self.assertEqual(
            player[
                "batting_average"
            ],
            0.667,
        )
        self.assertEqual(
            player[
                "walk_pct"
            ],
            25.0,
        )
        self.assertEqual(
            player[
                "strikeout_pct"
            ],
            25.0,
        )
        self.assertEqual(
            player[
                "home_run_pct"
            ],
            25.0,
        )

        tendencies = player[
            "strikeout_tendencies"
        ]

        self.assertEqual(
            tendencies[
                "with_finishing_pitch"
            ],
            1,
        )
        self.assertEqual(
            tendencies[
                "finishing_pitches"
            ][0],
            {
                "value": "slider",
                "count": 1,
                "pct": 100.0,
            },
        )
        self.assertEqual(
            tendencies[
                "locations"
            ][0][
                "value"
            ],
            "low_away",
        )
        self.assertEqual(
            tendencies[
                "styles"
            ][0][
                "value"
            ],
            "chasing",
        )


class LiveScoutNormalizedEventTests(
    unittest.TestCase
):
    def test_live_events_are_attributed_to_game_sides(
        self,
    ):
        events = [
            {
                "batting_team": "Away Team",
                "event_type": "single",
            },
            {
                "batting_team": "Home Team",
                "event_type": "strikeout",
            },
            {
                "batting_team": "Unknown Team",
                "event_type": "walk",
            },
        ]

        attributed = (
            attribute_live_event_sides(
                events,
                {
                    "home_full_name": (
                        "Home Team"
                    ),
                    "away_full_name": (
                        "Away Team"
                    ),
                },
            )
        )

        self.assertEqual(
            [
                event["batting_side"]
                for event in attributed
            ],
            [
                "away",
                "home",
                "unknown",
            ],
        )

    def test_live_game_log_uses_normalized_event_parser(
        self,
    ):
        events = parse_live_normalized_events(
            make_game_log_with_text(
                home_name="ScoutUser",
                away_name="OtherUser",
            )
        )

        self.assertEqual(
            len(events),
            1,
        )

        event = events[0]

        self.assertEqual(
            event["inning"],
            1,
        )
        self.assertEqual(
            event["batting_team"],
            "Scout Team",
        )
        self.assertEqual(
            event["event_type"],
            "strikeout",
        )
        self.assertEqual(
            event["player_name"],
            "Batter",
        )
        self.assertEqual(
            event["strikeout_type"],
            "chasing",
        )
        self.assertEqual(
            event["terminal_pitch_type"],
            "slider",
        )
        self.assertEqual(
            event["terminal_pitch_location"],
            "low_away",
        )

    @patch(
        "src.live_scout.fetch_game_log_for_user"
    )
    @patch(
        "src.live_scout.create_live_session"
    )
    def test_worker_returns_normalized_events(
        self,
        mock_create_live_session,
        mock_fetch_game_log,
    ):
        mock_create_live_session.return_value = (
            object()
        )
        mock_fetch_game_log.return_value = (
            make_game_log_with_text(
                home_name="ScoutUser",
                away_name="OtherUser",
            )
        )

        result = (
            fetch_and_parse_log_for_game(
                {
                    "id": "live-game-1",
                    "home_name": "ScoutUser",
                    "away_name": "OtherUser",
                    "home_full_name": "Scout Team",
                    "away_full_name": "Other Team",
                },
                "ScoutUser",
                "psn",
            )
        )

        self.assertTrue(
            result["success"]
        )
        self.assertIsNone(
            result["error"]
        )
        self.assertEqual(
            result["user_side"],
            "home",
        )
        self.assertEqual(
            result["stats"][
                "batting_ab"
            ],
            30,
        )
        self.assertEqual(
            len(result["events"]),
            1,
        )
        self.assertEqual(
            result["events"][0][
                "event_type"
            ],
            "strikeout",
        )
        self.assertEqual(
            result["events"][0][
                "terminal_pitch_location"
            ],
            "low_away",
        )
        self.assertEqual(
            result["events"][0][
                "batting_side"
            ],
            "home",
        )


class LiveScoutLogAttributionTests(
    unittest.TestCase
):
    def test_home_side_uses_history_attribution_when_log_name_blank(
        self,
    ):
        stats = parse_live_log_stats_for_username(
            make_game_log(
                home_name="",
                away_name="Pbahr86",
            ),
            "PeanutDiamond22",
            user_side="home",
        )

        self.assertEqual(
            stats,
            {
                "batting_ab": 30,
                "batting_h": 3,
                "pitching_outs": 27,
                "pitching_er": 2,
            },
        )

    def test_away_side_uses_history_attribution_when_log_name_blank(
        self,
    ):
        stats = parse_live_log_stats_for_username(
            make_game_log(
                home_name="Slimpickens12",
                away_name="",
            ),
            "PeanutDiamond22",
            user_side="away",
        )

        self.assertEqual(
            stats,
            {
                "batting_ab": 28,
                "batting_h": 7,
                "pitching_outs": 27,
                "pitching_er": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
