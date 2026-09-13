import unittest

from src.play_by_play import (
    classify_play_statement,
    clean_game_log_text,
    parse_game_log_text,
    parse_inning_summary,
)


class GameLogTextCleanupTests(unittest.TestCase):
    def test_markup_is_removed_and_newlines_are_preserved(self):
        raw = (
            "^c51^Inning 1:^c50^^n^"
            "Hoosiers batting."
        )

        self.assertEqual(
            clean_game_log_text(raw),
            "Inning 1:\nHoosiers batting.",
        )


class InningSummaryTests(unittest.TestCase):
    def test_inning_summary_fields_are_parsed(self):
        summary = parse_inning_summary(
            (
                "Runs: 2 Hits: 4 Walks: 1 "
                "Errors: 0 Pitches: 19 "
                "Runners Left On: 2"
            )
        )

        self.assertEqual(
            summary,
            {
                "runs": 2,
                "hits": 4,
                "walks": 1,
                "errors": 0,
                "pitches": 19,
                "runners_left_on": 2,
            },
        )


class PlayClassificationTests(unittest.TestCase):
    def test_single_and_secondary_out(self):
        event = classify_play_statement(
            (
                "Martinez hit to center for a "
                "single, out while advancing "
                "extra bases (7-4)."
            )
        )

        self.assertEqual(
            event["event_type"],
            "single",
        )
        self.assertEqual(
            event["player_name"],
            "Martinez",
        )
        self.assertEqual(
            event["hit_bases"],
            1,
        )
        self.assertTrue(
            event["secondary_out"]
        )
        self.assertEqual(
            event["outs_recorded"],
            1,
        )
        self.assertEqual(
            event["fielding_code"],
            "7-4",
        )

    def test_bunt_and_chop_singles_extract_player_name(
        self,
    ):
        cases = [
            (
                (
                    "Carroll bunted to third "
                    "baseman for a single."
                ),
                "Carroll",
                False,
            ),
            (
                (
                    "Lebron bunted and deflected "
                    "off pitcher Schlittler for "
                    "a single."
                ),
                "Lebron",
                False,
            ),
            (
                (
                    "Albies chopped to shortstop "
                    "for a single."
                ),
                "Albies",
                False,
            ),
            (
                (
                    "McGee bunted to first baseman "
                    "for a single, out while "
                    "advancing extra bases (3U)."
                ),
                "McGee",
                True,
            ),
        ]

        for (
            statement,
            expected_name,
            expected_secondary_out,
        ) in cases:
            with self.subTest(
                statement=statement
            ):
                event = (
                    classify_play_statement(
                        statement
                    )
                )

                self.assertEqual(
                    event[
                        "event_type"
                    ],
                    "single",
                )

                self.assertEqual(
                    event[
                        "player_name"
                    ],
                    expected_name,
                )

                self.assertEqual(
                    event[
                        "hit_bases"
                    ],
                    1,
                )

                self.assertEqual(
                    event[
                        "secondary_out"
                    ],
                    expected_secondary_out,
                )

    def test_extra_base_hits_and_home_run_distance(self):
        double_event = (
            classify_play_statement(
                "Schwarber doubled to center."
            )
        )
        triple_event = (
            classify_play_statement(
                "Lindor tripled to center."
            )
        )
        homer_event = (
            classify_play_statement(
                (
                    "Martinez homered to center "
                    "(438 feet)."
                )
            )
        )

        self.assertEqual(
            double_event["hit_bases"],
            2,
        )
        self.assertEqual(
            triple_event["hit_bases"],
            3,
        )
        self.assertEqual(
            homer_event["hit_bases"],
            4,
        )
        self.assertEqual(
            homer_event[
                "home_run_distance_ft"
            ],
            438,
        )

    def test_strikeout_style_and_terminal_pitch(self):
        chasing = (
            classify_play_statement(
                (
                    "Lindor struck out chasing "
                    "a low changeup."
                )
            )
        )
        looking = (
            classify_play_statement(
                (
                    "Happ was called out on "
                    "strikes looking on a "
                    "sinker high and in."
                )
            )
        )

        self.assertEqual(
            chasing["strikeout_type"],
            "chasing",
        )
        self.assertEqual(
            chasing[
                "terminal_pitch_type"
            ],
            "changeup",
        )
        self.assertEqual(
            looking["strikeout_type"],
            "looking",
        )
        self.assertEqual(
            looking[
                "terminal_pitch_type"
            ],
            "sinker",
        )
        self.assertEqual(
            chasing[
                "terminal_pitch_location"
            ],
            "low",
        )
        self.assertEqual(
            looking[
                "terminal_pitch_location"
            ],
            "high_in",
        )

    def test_strikeout_terminal_pitch_locations(self):
        cases = {
            (
                "Batter struck out chasing "
                "a slider low and in."
            ): "low_in",
            (
                "Batter struck out chasing "
                "a slider low and away."
            ): "low_away",
            (
                "Batter struck out chasing "
                "a fastball high and in."
            ): "high_in",
            (
                "Batter struck out chasing "
                "a fastball high and away."
            ): "high_away",
            (
                "Batter struck out chasing "
                "an inside fastball."
            ): "inside",
            (
                "Batter struck out chasing "
                "an outside fastball."
            ): "outside",
            (
                "Batter struck out chasing "
                "a low changeup."
            ): "low",
            (
                "Batter struck out chasing "
                "a high fastball."
            ): "high",
            (
                "Batter struck out on a "
                "curveball down the middle."
            ): "middle",
        }

        for statement, expected in cases.items():
            with self.subTest(
                statement=statement
            ):
                event = (
                    classify_play_statement(
                        statement
                    )
                )

                self.assertEqual(
                    event[
                        "terminal_pitch_location"
                    ],
                    expected,
                )

        no_location = (
            classify_play_statement(
                "Batter struck out swinging."
            )
        )

        self.assertIsNone(
            no_location[
                "terminal_pitch_location"
            ]
        )

    def test_batted_ball_outs_and_double_play(self):
        ground_out = (
            classify_play_statement(
                (
                    "Baez grounded out to "
                    "Lindor (6-3)."
                )
            )
        )
        double_play = (
            classify_play_statement(
                (
                    "Langford grounded into a "
                    "double play (4-6-3 DP)."
                )
            )
        )

        self.assertEqual(
            ground_out["event_type"],
            "ground_out",
        )
        self.assertEqual(
            ground_out["fielding_code"],
            "6-3",
        )
        self.assertEqual(
            double_play["outs_recorded"],
            2,
        )
        self.assertEqual(
            double_play["fielding_code"],
            "4-6-3 DP",
        )

    def test_walk_hbp_sacrifice_choice_and_error(self):
        cases = {
            "Alvarez walked.": "walk",
            (
                "Lindor was hit by a pitch."
            ): "hit_by_pitch",
            (
                "Lowe hit a sacrifice fly "
                "to Robert Jr. (SF8)."
            ): "sacrifice_fly",
            (
                "Trout reached first on "
                "fielder's choice (6-4 FC)."
            ): "fielders_choice",
            (
                "Ramirez reached first on a "
                "fielding error by Roberts "
                "(E4)."
            ): "reached_error",
        }

        for statement, expected in (
            cases.items()
        ):
            with self.subTest(
                statement=statement
            ):
                event = (
                    classify_play_statement(
                        statement
                    )
                )

                self.assertEqual(
                    event["event_type"],
                    expected,
                )

    def test_runner_events(self):
        score = (
            classify_play_statement(
                "Lindor scores."
            )
        )
        advance = (
            classify_play_statement(
                (
                    "Ramirez advances to 2nd "
                    "on a wild pitch."
                )
            )
        )
        steal = (
            classify_play_statement(
                "Witt Jr. stole 3rd."
            )
        )
        caught = (
            classify_play_statement(
                (
                    "Carroll was caught "
                    "stealing."
                )
            )
        )
        runner_out = (
            classify_play_statement(
                "Polanco out."
            )
        )

        self.assertEqual(
            score["destination_base"],
            "home",
        )
        self.assertEqual(
            advance["cause"],
            "wild_pitch",
        )
        self.assertEqual(
            advance["destination_base"],
            "2nd",
        )
        self.assertEqual(
            steal["event_type"],
            "stolen_base",
        )
        self.assertEqual(
            caught["event_type"],
            "caught_stealing",
        )
        self.assertEqual(
            runner_out["event_type"],
            "runner_out",
        )

    def test_score_on_fielding_error(self):
        event = classify_play_statement(
            (
                "Wagner scored on a fielding "
                "error by Cavalli (E1)."
            )
        )

        self.assertEqual(
            event["event_type"],
            "runner_scored",
        )
        self.assertEqual(
            event["player_name"],
            "Wagner",
        )
        self.assertEqual(
            event["destination_base"],
            "home",
        )
        self.assertEqual(
            event["cause"],
            "fielding_error",
        )
        self.assertEqual(
            event["fielding_code"],
            "E1",
        )

    def test_picked_off_runner(self):
        event = classify_play_statement(
            "Granderson was picked off."
        )

        self.assertEqual(
            event["event_type"],
            "picked_off",
        )
        self.assertEqual(
            event["player_name"],
            "Granderson",
        )
        self.assertTrue(
            event["is_out"]
        )
        self.assertEqual(
            event["outs_recorded"],
            1,
        )
        self.assertEqual(
            event["cause"],
            "picked_off",
        )

    def test_additional_game_log_phrase_families(self):
        cases = [
            (
                "Aaron pinch runs for Alonso.",
                "pinch_runner",
            ),
            (
                "Alvarez substituted for Moreno.",
                "substitution",
            ),
            (
                "Carrigg sacrificed to Minter "
                "(1-3 SH).",
                "sacrifice_bunt",
            ),
            (
                "Cholowsky lined into a double "
                "play (L5-3 DP).",
                "double_play",
            ),
            (
                "Soto lined into a triple play "
                "(L9-2-6 TP).",
                "triple_play",
            ),
            (
                "Caissie reached 3rd on a "
                "passed ball.",
                "runner_advanced",
            ),
            (
                "Duran scored on a wild pitch.",
                "runner_scored",
            ),
            (
                "Leiter balks, runners advance.",
                "balk",
            ),
            (
                "Taylor throws wild at first.",
                "throwing_error",
            ),
            (
                "Garcia in bullpen.",
                "bullpen_marker",
            ),
            (
                "Crow-Armstrong stole.",
                "stolen_base",
            ),
        ]

        for statement, expected in cases:
            with self.subTest(
                statement=statement
            ):
                event = (
                    classify_play_statement(
                        statement
                    )
                )

                self.assertEqual(
                    event["event_type"],
                    expected,
                )

    def test_standalone_unassisted_fielding_code_is_not_unknown(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "Durham at bat. "
            "(2U). "
            "Hernandez out. "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 1 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        self.assertEqual(
            parsed["unknown_count"],
            0,
        )

        self.assertEqual(
            parsed["events"][1][
                "event_type"
            ],
            "runner_out",
        )

        self.assertEqual(
            parsed["events"][1][
                "fielding_code"
            ],
            "2U",
        )

    def test_duplicate_was_out_after_pickoff_is_suppressed(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "First Batter struck out. "
            "Second Batter flied out to Center (F8). "
            "Runner was picked off. "
            "Runner was out. "
            "Other Runner was out. "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 10 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        self.assertEqual(
            [
                event["event_type"]
                for event in parsed["events"]
            ],
            [
                "strikeout",
                "fly_out",
                "picked_off",
            ],
        )

        self.assertEqual(
            sum(
                event.get(
                    "outs_recorded"
                )
                or 0
                for event in parsed["events"]
            ),
            3,
        )

    def test_was_out_is_retained_without_claiming_out_count(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "Runner singled to center. "
            "Runner was out. "
            "Batter struck out. "
            "Next Batter flied out to Center (F8). "
            "Runs: 0 Hits: 1 Walks: 0 "
            "Errors: 0 Pitches: 10 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        runner_out = [
            event
            for event in parsed["events"]
            if event["event_type"]
            == "runner_out"
        ][0]

        self.assertEqual(
            runner_out["player_name"],
            "Runner",
        )

        self.assertIsNone(
            runner_out["outs_recorded"]
        )

        self.assertTrue(
            runner_out["is_out"]
        )

    def test_dropped_third_strike_does_not_record_out(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "Carroll struck out but reached first after it was dropped (WP). "
            "Clark struck out chasing a slider. "
            "Witt Jr. flied out to Center (F8). "
            "Marte grounded out to First (3U). "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 15 "
            "Runners Left On: 1"
        )

        parsed = parse_game_log_text(raw)

        dropped = parsed["events"][0]

        self.assertEqual(
            dropped["event_type"],
            "strikeout",
        )
        self.assertFalse(
            dropped["is_out"]
        )
        self.assertIsNone(
            dropped["outs_recorded"]
        )
        self.assertEqual(
            dropped["cause"],
            "dropped_third_strike",
        )

        self.assertEqual(
            sum(
                event.get("outs_recorded") or 0
                for event in parsed["events"]
            ),
            3,
        )

    def test_trailing_text_after_three_outs_is_ignored(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "First grounded out to Shortstop (6-3). "
            "Second struck out swinging. "
            "Third flied out to Center (F8). "
            "Bogus singled to center. "
            "BogusTwo homered to left (450 feet). "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 12 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(raw)

        self.assertEqual(
            len(parsed["events"]),
            3,
        )

        self.assertEqual(
            [
                event["event_type"]
                for event in parsed["events"]
            ],
            [
                "ground_out",
                "strikeout",
                "fly_out",
            ],
        )

        self.assertEqual(
            sum(
                event.get("outs_recorded") or 0
                for event in parsed["events"]
            ),
            3,
        )

    def test_intentional_walk_extracts_player_name(self):
        event = classify_play_statement(
            "Granderson was intentionally walked."
        )

        self.assertEqual(
            event["event_type"],
            "walk",
        )
        self.assertEqual(
            event["player_name"],
            "Granderson",
        )
        self.assertEqual(
            event["cause"],
            "intentional_walk",
        )
        self.assertTrue(
            event["is_plate_appearance"],
        )

    def test_pitcher_marker(self):
        event = classify_play_statement(
            "Morejon pitching."
        )

        self.assertEqual(
            event["event_type"],
            "pitcher_marker",
        )
        self.assertEqual(
            event["player_name"],
            "Morejon",
        )

    def test_bunt_out(self):
        event = classify_play_statement(
            (
                "Crow-Armstrong bunted out "
                "to Santana (5-3)."
            )
        )

        self.assertEqual(
            event["event_type"],
            "bunt_out",
        )
        self.assertEqual(
            event["fielding_code"],
            "5-3",
        )

    def test_advance_on_throwing_error(self):
        event = classify_play_statement(
            (
                "Edman advances to 2nd "
                "on a throwing error."
            )
        )

        self.assertEqual(
            event["event_type"],
            "runner_advanced",
        )
        self.assertEqual(
            event["destination_base"],
            "2nd",
        )
        self.assertEqual(
            event["cause"],
            "throwing_error",
        )

    def test_substitution_and_batter_markers(self):
        pinch_hit = (
            classify_play_statement(
                "McGee pinch hit for Jackson."
            )
        )
        batter = (
            classify_play_statement(
                "Durham at bat."
            )
        )

        self.assertEqual(
            pinch_hit["event_type"],
            "pinch_hit",
        )
        self.assertEqual(
            pinch_hit["player_name"],
            "McGee",
        )
        self.assertEqual(
            pinch_hit[
                "related_player_name"
            ],
            "Jackson",
        )
        self.assertEqual(
            batter["event_type"],
            "batter_marker",
        )
        self.assertEqual(
            batter["player_name"],
            "Durham",
        )

    def test_batted_out_with_line_code(self):
        event = classify_play_statement(
            (
                "Carroll batted out to "
                "Happ (L5)."
            )
        )

        self.assertEqual(
            event["event_type"],
            "line_out",
        )
        self.assertEqual(
            event["fielding_code"],
            "L5",
        )


class GameLogParsingTests(unittest.TestCase):
    def test_player_suffix_and_initial_do_not_split(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "T. Imai pitching. "
            "Tatis Jr. homered to right "
            "(388 feet). "
            "Tatis Jr. scores. "
            "Runs: 1 Hits: 1 Walks: 0 "
            "Errors: 0 Pitches: 4 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        self.assertEqual(
            [
                event["event_type"]
                for event in (
                    parsed["events"]
                )
            ],
            [
                "pitcher_marker",
                "home_run",
                "runner_scored",
            ],
        )

        self.assertEqual(
            parsed["events"][0][
                "player_name"
            ],
            "T. Imai",
        )

        self.assertEqual(
            parsed["events"][1][
                "player_name"
            ],
            "Tatis Jr.",
        )

        self.assertEqual(
            parsed["events"][2][
                "player_name"
            ],
            "Tatis Jr.",
        )

    def test_inning_blocks_events_and_summaries_are_parsed(self):
        raw = (
            "^c51^Inning 2:^c50^^n^"
            "Hoosiers batting. "
            "^c48^Morejon pitching. "
            "Lindor walked. "
            "Runs: 0 Hits: 0 Walks: 1 "
            "Errors: 0 Pitches: 7 "
            "Runners Left On: 1 "
            "^c51^Inning 1:^c50^^n^"
            "Hoosiers batting. "
            "Martinez homered to center "
            "(438 feet). "
            "Runs: 1 Hits: 1 Walks: 0 "
            "Errors: 0 Pitches: 4 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        self.assertEqual(
            [
                inning["inning"]
                for inning in (
                    parsed["innings"]
                )
            ],
            [2, 1],
        )

        self.assertEqual(
            parsed["innings"][0][
                "batting_team"
            ],
            "Hoosiers",
        )

        self.assertEqual(
            parsed["innings"][0][
                "summary"
            ]["pitches"],
            7,
        )

        self.assertEqual(
            [
                event["event_type"]
                for event in (
                    parsed["events"]
                )
            ],
            [
                "pitcher_marker",
                "walk",
                "home_run",
            ],
        )

    def test_both_batting_sides_in_one_inning_are_parsed(self):
        raw = (
            "^c51^Inning 1:^c50^^n^"
            "Away Team batting. "
            "Away Batter homered to center "
            "(400 feet). "
            "Away Batter scores. "
            "^n^Runs: 1 Hits: 1 Walks: 0 "
            "Errors: 0 Pitches: 5 "
            "Runners Left On: 0 "
            "^n^^n^Home Team batting. "
            "Home Batter struck out on a slider. "
            "^n^Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 4 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(raw)

        self.assertEqual(
            [
                (
                    inning["inning"],
                    inning["batting_team"],
                    inning["summary"]["runs"],
                )
                for inning in parsed["innings"]
            ],
            [
                (1, "Away Team", 1),
                (1, "Home Team", 0),
            ],
        )

        self.assertEqual(
            [
                (
                    event["batting_team"],
                    event["event_type"],
                )
                for event in parsed["events"]
            ],
            [
                ("Away Team", "home_run"),
                ("Away Team", "runner_scored"),
                ("Home Team", "strikeout"),
            ],
        )

    def test_standalone_fielding_code_attaches_to_runner_out(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "Durham at bat. "
            "(2-5). "
            "Hernandez out. "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 1 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        self.assertEqual(
            [
                event["event_type"]
                for event in (
                    parsed["events"]
                )
            ],
            [
                "batter_marker",
                "runner_out",
            ],
        )

        self.assertEqual(
            parsed["events"][1][
                "player_name"
            ],
            "Hernandez",
        )

        self.assertEqual(
            parsed["events"][1][
                "fielding_code"
            ],
            "2-5",
        )

    def test_pitcher_context_uses_chronological_inning_order(self):
        raw = (
            "Inning 2: "
            "Hoosiers batting. "
            "Reliever pitching. "
            "Second Batter struck out on a slider. "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 4 "
            "Runners Left On: 0 "
            "Inning 1: "
            "Hoosiers batting. "
            "Starter pitching. "
            "First Batter struck out on a fastball. "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 4 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        # Source order remains unchanged even though pitcher
        # state is reconstructed chronologically.
        self.assertEqual(
            [
                event["inning"]
                for event in (
                    parsed["events"]
                )
            ],
            [
                2,
                2,
                1,
                1,
            ],
        )

        strikeouts = {
            event["inning"]: event
            for event in (
                parsed["events"]
            )
            if (
                event[
                    "event_type"
                ]
                == "strikeout"
            )
        }

        self.assertEqual(
            strikeouts[1][
                "pitcher_name"
            ],
            "Starter",
        )

        self.assertTrue(
            strikeouts[1][
                "pitcher_is_starter"
            ]
        )

        self.assertEqual(
            strikeouts[2][
                "pitcher_name"
            ],
            "Reliever",
        )

        self.assertFalse(
            strikeouts[2][
                "pitcher_is_starter"
            ]
        )

    def test_unknown_statements_are_retained(self):
        raw = (
            "Inning 1: Hoosiers batting. "
            "Something unexpected happened. "
            "Runs: 0 Hits: 0 Walks: 0 "
            "Errors: 0 Pitches: 1 "
            "Runners Left On: 0"
        )

        parsed = parse_game_log_text(
            raw
        )

        self.assertEqual(
            parsed["unknown_count"],
            1,
        )

        self.assertEqual(
            parsed["events"][0][
                "event_type"
            ],
            "unknown",
        )


if __name__ == "__main__":
    unittest.main()
