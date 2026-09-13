import tempfile
import unittest
from pathlib import Path

from src.analytics import (
    get_inning_scoring_tendencies,
    get_plate_discipline_trends,
    get_player_event_analytics,
    get_scouting_trends,
)
from src.config import USERNAME
from src.database import connect_db, init_db
from src.player_handedness import (
    HandednessResolver,
)


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


    def insert_event(
        self,
        *,
        game_id: str,
        source_index: int,
        batting_side: str,
        event_type: str,
        player_name: str,
        is_plate_appearance: bool = False,
        is_hit: bool = False,
        hit_bases=None,
        cause=None,
        strikeout_type=None,
        terminal_pitch_type=None,
        terminal_pitch_location=None,
        pitcher_name=None,
        pitcher_is_starter=None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO game_events (
                game_id,
                source_index,
                inning,
                batting_side,
                event_type,
                player_name,
                pitcher_name,
                pitcher_is_starter,
                raw_text,
                is_plate_appearance,
                is_hit,
                hit_bases,
                cause,
                strikeout_type,
                terminal_pitch_type,
                terminal_pitch_location
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            (
                game_id,
                source_index,
                1,
                batting_side,
                event_type,
                player_name,
                pitcher_name,
                (
                    int(
                        bool(
                            pitcher_is_starter
                        )
                    )
                    if pitcher_is_starter
                    is not None
                    else None
                ),
                event_type,
                int(
                    is_plate_appearance
                ),
                int(is_hit),
                hit_bases,
                cause,
                strikeout_type,
                terminal_pitch_type,
                terminal_pitch_location,
            ),
        )


class PlayerEventAnalyticsTests(
    AnalyticsTestCase
):
    def test_player_events_are_attributed_and_aggregated(
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

        self.insert_event(
            game_id="game-1",
            source_index=1,
            batting_side="home",
            event_type="single",
            player_name="User Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=1,
        )
        self.insert_event(
            game_id="game-1",
            source_index=2,
            batting_side="home",
            event_type="walk",
            player_name="User Batter",
            is_plate_appearance=True,
            cause="intentional_walk",
        )
        self.insert_event(
            game_id="game-1",
            source_index=3,
            batting_side="home",
            event_type="strikeout",
            player_name="User Batter",
            is_plate_appearance=True,
        )
        self.insert_event(
            game_id="game-1",
            source_index=4,
            batting_side="home",
            event_type="sacrifice_fly",
            player_name="User Batter",
            is_plate_appearance=True,
        )
        self.insert_event(
            game_id="game-1",
            source_index=5,
            batting_side="home",
            event_type="runner_scored",
            player_name="User Batter",
        )
        self.insert_event(
            game_id="game-1",
            source_index=6,
            batting_side="home",
            event_type="stolen_base",
            player_name="User Batter",
        )

        self.insert_event(
            game_id="game-1",
            source_index=7,
            batting_side="away",
            event_type="home_run",
            player_name="Opponent Slugger",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=4,
        )
        self.insert_event(
            game_id="game-1",
            source_index=8,
            batting_side="away",
            event_type="hit_by_pitch",
            player_name="Opponent Slugger",
            is_plate_appearance=True,
        )
        self.insert_event(
            game_id="game-1",
            source_index=9,
            batting_side="away",
            event_type="caught_stealing",
            player_name="Opponent Slugger",
        )

        # Marker events must not create fake hitter rows.
        self.insert_event(
            game_id="game-1",
            source_index=10,
            batting_side="home",
            event_type="pitcher_marker",
            player_name="Some Pitcher",
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

        self.insert_event(
            game_id="game-2",
            source_index=1,
            batting_side="away",
            event_type="double",
            player_name="User Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=2,
        )
        self.insert_event(
            game_id="game-2",
            source_index=2,
            batting_side="away",
            event_type="fielders_choice",
            player_name="User Batter",
            is_plate_appearance=True,
        )
        self.insert_event(
            game_id="game-2",
            source_index=3,
            batting_side="home",
            event_type="single",
            player_name="Beta Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=1,
        )

        # Unknown-side events are intentionally excluded.
        self.insert_event(
            game_id="game-2",
            source_index=4,
            batting_side="unknown",
            event_type="home_run",
            player_name="Ghost Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=4,
        )

        self.conn.commit()

        report = get_player_event_analytics(
            self.conn,
            USERNAME,
            limit=20,
        )

        self.assertEqual(
            report["games_included"],
            2,
        )

        self.assertEqual(
            len(report["user_players"]),
            1,
        )

        user = report[
            "user_players"
        ][0]

        self.assertEqual(
            user["player_name"],
            "User Batter",
        )
        self.assertEqual(
            user["team_name"],
            "Configured Team",
        )
        self.assertEqual(
            user["games"],
            2,
        )
        self.assertEqual(
            user["plate_appearances"],
            6,
        )
        self.assertEqual(
            user["at_bats"],
            4,
        )
        self.assertEqual(
            user["hits"],
            2,
        )
        self.assertEqual(
            user["singles"],
            1,
        )
        self.assertEqual(
            user["doubles"],
            1,
        )
        self.assertEqual(
            user["walks"],
            1,
        )
        self.assertEqual(
            user["intentional_walks"],
            1,
        )
        self.assertEqual(
            user["strikeouts"],
            1,
        )
        self.assertEqual(
            user["sacrifice_flies"],
            1,
        )
        self.assertEqual(
            user["runs"],
            1,
        )
        self.assertEqual(
            user["stolen_bases"],
            1,
        )
        self.assertEqual(
            user["batting_average"],
            0.5,
        )
        self.assertEqual(
            user["walk_pct"],
            16.7,
        )
        self.assertEqual(
            user["strikeout_pct"],
            16.7,
        )
        self.assertEqual(
            user["home_run_pct"],
            0.0,
        )

        opponents = report[
            "opponent_players"
        ]

        self.assertEqual(
            [
                player["player_name"]
                for player in opponents
            ],
            [
                "Opponent Slugger",
                "Beta Batter",
            ],
        )

        slugger = opponents[0]

        self.assertEqual(
            slugger["plate_appearances"],
            2,
        )
        self.assertEqual(
            slugger["at_bats"],
            1,
        )
        self.assertEqual(
            slugger["hits"],
            1,
        )
        self.assertEqual(
            slugger["home_runs"],
            1,
        )
        self.assertEqual(
            slugger["hit_by_pitch"],
            1,
        )
        self.assertEqual(
            slugger["caught_stealing"],
            1,
        )
        self.assertEqual(
            slugger["batting_average"],
            1.0,
        )
        self.assertEqual(
            slugger["home_run_pct"],
            50.0,
        )

        all_names = {
            player["player_name"]
            for player in (
                report["user_players"]
                + report[
                    "opponent_players"
                ]
            )
        }

        self.assertNotIn(
            "Some Pitcher",
            all_names,
        )
        self.assertNotIn(
            "Ghost Batter",
            all_names,
        )

    def test_matchup_profiles_use_persisted_pitcher_and_box_position_context(
        self,
    ):
        self.insert_game(
            game_id="matchup-game",
            display_date=(
                "2026-01-03 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Alpha",
            opponent_team_name=(
                "Alpha Team"
            ),
        )

        self.conn.execute(
            """
            INSERT INTO player_batting_stats (
                game_id,
                team_id,
                team_name,
                player_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "matchup-game",
                "alpha",
                "Alpha Team",
                "Switch Batter, SS",
            ),
        )

        self.insert_event(
            game_id="matchup-game",
            source_index=1,
            batting_side="away",
            event_type="strikeout",
            player_name="Switch Batter",
            is_plate_appearance=True,
            strikeout_type="chasing",
            terminal_pitch_type="slider",
            terminal_pitch_location=(
                "low_away"
            ),
            pitcher_name="Right Pitcher",
            pitcher_is_starter=True,
        )

        self.conn.commit()

        resolver = HandednessResolver(
            [
                {
                    "name": "Switch Batter",
                    "is_hitter": True,
                    "two_way": False,
                    "bat_hand": "S",
                    "throw_hand": "R",
                    "display_position": "SS",
                    "display_secondary_positions": "",
                },
                {
                    "name": "Right Pitcher",
                    "is_hitter": False,
                    "two_way": False,
                    "bat_hand": "R",
                    "throw_hand": "R",
                    "display_position": "SP",
                    "display_secondary_positions": "",
                },
            ]
        )

        report = get_player_event_analytics(
            self.conn,
            USERNAME,
            limit=20,
            handedness_resolver=resolver,
        )

        player = report[
            "opponent_players"
        ][0]

        profiles = player[
            "matchup_strikeout_profiles"
        ]

        self.assertEqual(
            profiles[
                "classified_plate_appearances"
            ],
            1,
        )

        self.assertEqual(
            profiles[
                "coverage_pct"
            ],
            100.0,
        )

        self.assertEqual(
            profiles[
                "matchups"
            ][
                "RvL"
            ][
                "strikeouts"
            ],
            1,
        )

        self.assertEqual(
            profiles[
                "matchups"
            ][
                "RvL"
            ][
                "location_counts"
            ][
                "low_away"
            ],
            1,
        )

    def test_strikeout_tendencies_are_aggregated_by_hitter(
        self,
    ):
        self.insert_game(
            game_id="strikeout-game",
            display_date=(
                "2026-01-03 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Alpha",
            opponent_team_name="Alpha Team",
        )

        strikeouts = [
            (
                "slider",
                "low_away",
                "chasing",
            ),
            (
                "slider",
                "low_away",
                "chasing",
            ),
            (
                "fastball",
                "high_in",
                "looking",
            ),
            (
                "changeup",
                "middle",
                "swinging_late",
            ),
            (
                None,
                None,
                None,
            ),
        ]

        for source_index, (
            pitch,
            location,
            style,
        ) in enumerate(
            strikeouts,
            start=1,
        ):
            self.insert_event(
                game_id="strikeout-game",
                source_index=source_index,
                batting_side="away",
                event_type="strikeout",
                player_name=(
                    "Opponent Batter"
                ),
                is_plate_appearance=True,
                strikeout_type=style,
                terminal_pitch_type=pitch,
                terminal_pitch_location=(
                    location
                ),
            )

        self.conn.commit()

        report = get_player_event_analytics(
            self.conn,
            USERNAME,
            limit=20,
            opponent_name="alpha",
        )

        self.assertEqual(
            report["games_included"],
            1,
        )
        self.assertEqual(
            len(
                report[
                    "opponent_players"
                ]
            ),
            1,
        )

        hitter = report[
            "opponent_players"
        ][0]

        self.assertEqual(
            hitter["strikeouts"],
            5,
        )

        tendencies = hitter[
            "strikeout_tendencies"
        ]

        self.assertEqual(
            tendencies[
                "with_finishing_pitch"
            ],
            4,
        )
        self.assertEqual(
            tendencies[
                "with_location"
            ],
            4,
        )
        self.assertEqual(
            tendencies[
                "with_style"
            ],
            4,
        )

        self.assertEqual(
            tendencies[
                "finishing_pitches"
            ],
            [
                {
                    "value": "slider",
                    "count": 2,
                    "pct": 50.0,
                },
                {
                    "value": "changeup",
                    "count": 1,
                    "pct": 25.0,
                },
                {
                    "value": "fastball",
                    "count": 1,
                    "pct": 25.0,
                },
            ],
        )

        self.assertEqual(
            tendencies["locations"],
            [
                {
                    "value": "low_away",
                    "count": 2,
                    "pct": 50.0,
                },
                {
                    "value": "high_in",
                    "count": 1,
                    "pct": 25.0,
                },
                {
                    "value": "middle",
                    "count": 1,
                    "pct": 25.0,
                },
            ],
        )

        self.assertEqual(
            tendencies["styles"],
            [
                {
                    "value": "chasing",
                    "count": 2,
                    "pct": 50.0,
                },
                {
                    "value": "looking",
                    "count": 1,
                    "pct": 25.0,
                },
                {
                    "value": (
                        "swinging_late"
                    ),
                    "count": 1,
                    "pct": 25.0,
                },
            ],
        )

    def test_player_identity_ignores_team_rename_but_respects_opponent_account(
        self,
    ):
        self.insert_game(
            game_id="alpha-1",
            display_date=(
                "2026-02-01 12:00:00"
            ),
            user_is_home=True,
            opponent_name="AlphaUser",
            opponent_team_name="Old Alpha",
        )
        self.insert_event(
            game_id="alpha-1",
            source_index=1,
            batting_side="away",
            event_type="single",
            player_name="Jones",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=1,
        )

        self.insert_game(
            game_id="alpha-2",
            display_date=(
                "2026-02-02 12:00:00"
            ),
            user_is_home=False,
            opponent_name="AlphaUser",
            opponent_team_name="New Alpha",
        )
        self.insert_event(
            game_id="alpha-2",
            source_index=1,
            batting_side="home",
            event_type="home_run",
            player_name="JONES",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=4,
        )

        self.insert_game(
            game_id="beta-1",
            display_date=(
                "2026-02-03 12:00:00"
            ),
            user_is_home=True,
            opponent_name="BetaUser",
            opponent_team_name="Beta Team",
        )
        self.insert_event(
            game_id="beta-1",
            source_index=1,
            batting_side="away",
            event_type="double",
            player_name="Jones",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=2,
        )

        self.conn.commit()

        report = get_player_event_analytics(
            self.conn,
            USERNAME,
            limit=20,
        )

        self.assertEqual(
            len(
                report[
                    "opponent_players"
                ]
            ),
            2,
        )

        by_opponent = {
            row["opponent_name"]: row
            for row in report[
                "opponent_players"
            ]
        }

        alpha = by_opponent[
            "AlphaUser"
        ]

        self.assertEqual(
            alpha["games"],
            2,
        )
        self.assertEqual(
            alpha[
                "plate_appearances"
            ],
            2,
        )
        self.assertEqual(
            alpha["hits"],
            2,
        )
        self.assertEqual(
            alpha["singles"],
            1,
        )
        self.assertEqual(
            alpha["home_runs"],
            1,
        )

        beta = by_opponent[
            "BetaUser"
        ]

        self.assertEqual(
            beta["games"],
            1,
        )
        self.assertEqual(
            beta["hits"],
            1,
        )
        self.assertEqual(
            beta["doubles"],
            1,
        )

    def test_opponent_filter_is_applied_before_limit(
        self,
    ):
        self.insert_game(
            game_id="target-old",
            display_date=(
                "2026-03-01 12:00:00"
            ),
            user_is_home=True,
            opponent_name="TargetUser",
            opponent_team_name="Old Target",
        )
        self.insert_event(
            game_id="target-old",
            source_index=1,
            batting_side="away",
            event_type="single",
            player_name="Target Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=1,
        )

        self.insert_game(
            game_id="target-new",
            display_date=(
                "2026-03-02 12:00:00"
            ),
            user_is_home=False,
            opponent_name="TargetUser",
            opponent_team_name="New Target",
        )
        self.insert_event(
            game_id="target-new",
            source_index=1,
            batting_side="home",
            event_type="home_run",
            player_name="Target Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=4,
        )

        # This is the newest game overall. If LIMIT were applied before
        # opponent filtering, the requested TargetUser report would be empty.
        self.insert_game(
            game_id="other-newest",
            display_date=(
                "2026-03-03 12:00:00"
            ),
            user_is_home=True,
            opponent_name="OtherUser",
            opponent_team_name="Other Team",
        )
        self.insert_event(
            game_id="other-newest",
            source_index=1,
            batting_side="away",
            event_type="double",
            player_name="Other Batter",
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=2,
        )

        self.conn.commit()

        report = get_player_event_analytics(
            self.conn,
            USERNAME,
            limit=1,
            opponent_name="targetuser",
        )

        self.assertEqual(
            report["games_included"],
            1,
        )
        self.assertEqual(
            len(report["opponent_players"]),
            1,
        )

        batter = report[
            "opponent_players"
        ][0]

        self.assertEqual(
            batter["opponent_name"],
            "TargetUser",
        )
        self.assertEqual(
            batter["games"],
            1,
        )
        self.assertEqual(
            batter["plate_appearances"],
            1,
        )
        self.assertEqual(
            batter["hits"],
            1,
        )
        self.assertEqual(
            batter["home_runs"],
            1,
        )
        self.assertEqual(
            batter["singles"],
            0,
        )


    def test_empty_database_returns_empty_player_lists(
        self,
    ):
        report = get_player_event_analytics(
            self.conn,
            USERNAME,
            limit=20,
        )

        self.assertEqual(
            report,
            {
                "games_included": 0,
                "user_players": [],
                "opponent_players": [],
            },
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

    def test_opponent_filter_is_applied_before_limit(
        self,
    ):
        self.insert_game(
            game_id="alpha-old",
            display_date=(
                "2026-01-01 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Alpha",
            opponent_team_name="Alpha Team",
        )
        self.insert_inning(
            game_id="alpha-old",
            inning=1,
            home_runs=1,
            away_runs=0,
        )

        self.insert_game(
            game_id="alpha-new",
            display_date=(
                "2026-01-02 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Alpha",
            opponent_team_name="Alpha Team",
        )
        self.insert_inning(
            game_id="alpha-new",
            inning=1,
            home_runs=2,
            away_runs=1,
        )

        # This is the newest game overall. If filtering happened
        # after LIMIT 1, the Alpha report would incorrectly be empty.
        self.insert_game(
            game_id="beta-newest",
            display_date=(
                "2026-01-03 12:00:00"
            ),
            user_is_home=True,
            opponent_name="Beta",
            opponent_team_name="Beta Team",
        )
        self.insert_inning(
            game_id="beta-newest",
            inning=1,
            home_runs=9,
            away_runs=8,
        )

        self.conn.commit()

        report = (
            get_inning_scoring_tendencies(
                self.conn,
                USERNAME,
                limit=1,
                opponent_name="ALPHA",
            )
        )

        self.assertEqual(
            report["games_included"],
            1,
        )
        self.assertEqual(
            report["innings"],
            [
                {
                    "inning": 1,
                    "games_reaching_inning": 1,
                    "user_innings_observed": 1,
                    "opponent_innings_observed": 1,
                    "user_runs": 2,
                    "opponent_runs": 1,
                    "user_runs_per_observed_inning": 2.0,
                    "opponent_runs_per_observed_inning": 1.0,
                    "run_diff_per_observed_inning": 1.0,
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
