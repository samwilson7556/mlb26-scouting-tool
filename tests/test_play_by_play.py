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
