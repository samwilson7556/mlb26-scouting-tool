import unittest

from src.parser import (
    calculate_era,
    clean_username,
    get_opponent_name,
    get_opponent_team_name,
    get_user_result,
    get_user_side,
    innings_pitched_to_outs,
    is_cpu_game,
    normalize_username,
    outs_to_innings_pitched,
    safe_float,
    safe_int,
    sum_csv_ints,
)


class UsernameParsingTests(unittest.TestCase):
    def test_clean_username_removes_style_suffix(self):
        self.assertEqual(
            clean_username(
                "test_player ^b53^"
            ),
            "test_player",
        )

    def test_clean_username_leaves_plain_name(self):
        self.assertEqual(
            clean_username(
                "Solokaden1011"
            ),
            "Solokaden1011",
        )

    def test_normalize_username_is_case_insensitive(self):
        self.assertEqual(
            normalize_username(
                "PlayerName ^b53^"
            ),
            "playername",
        )


class CpuFilteringTests(unittest.TestCase):
    def test_real_cpu_team_is_filtered(self):
        game = {
            "home_full_name": "CPU",
            "away_full_name": "Hoosiers",
            "home_name": "CPU",
            "away_name": "test_player",
        }

        self.assertTrue(
            is_cpu_game(game)
        )

    def test_username_cpu_marker_does_not_make_game_cpu(self):
        game = {
            "home_full_name": "Hoosiers",
            "away_full_name": "Kraken",
            "home_name": "CPU",
            "away_name": "Opponent123",
        }

        self.assertFalse(
            is_cpu_game(game)
        )

    def test_cpu_filter_is_case_insensitive(self):
        game = {
            "home_full_name": "cpu",
            "away_full_name": "Kraken",
        }

        self.assertTrue(
            is_cpu_game(game)
        )


class UserSideTests(unittest.TestCase):
    def test_user_is_home(self):
        game = {
            "home_name": (
                "test_player ^b53^"
            ),
            "away_name": (
                "Opponent123 ^b54^"
            ),
        }

        self.assertEqual(
            get_user_side(
                game,
                "test_player",
            ),
            "home",
        )

    def test_user_is_away(self):
        game = {
            "home_name": "Opponent123",
            "away_name": "test_player",
        }

        self.assertEqual(
            get_user_side(
                game,
                "test_player",
            ),
            "away",
        )

    def test_home_cpu_marker_fallback(self):
        game = {
            "home_name": "CPU",
            "away_name": "Opponent123",
        }

        self.assertEqual(
            get_user_side(
                game,
                "test_player",
            ),
            "home",
        )

    def test_away_cpu_marker_fallback(self):
        game = {
            "home_name": "Opponent123",
            "away_name": "CPU",
        }

        self.assertEqual(
            get_user_side(
                game,
                "test_player",
            ),
            "away",
        )

    def test_unknown_side(self):
        game = {
            "home_name": "PlayerA",
            "away_name": "PlayerB",
        }

        self.assertEqual(
            get_user_side(
                game,
                "test_player",
            ),
            "unknown",
        )


class GameAttributionTests(unittest.TestCase):
    def setUp(self):
        self.game = {
            "home_name": (
                "test_player ^b53^"
            ),
            "away_name": (
                "Solokaden1011 ^b54^"
            ),
            "home_full_name": "Hoosiers",
            "away_full_name": "Kraken",
            "home_display_result": "W",
            "away_display_result": "L",
        }

    def test_user_result(self):
        self.assertEqual(
            get_user_result(
                self.game,
                "test_player",
            ),
            "W",
        )

    def test_opponent_name(self):
        self.assertEqual(
            get_opponent_name(
                self.game,
                "test_player",
            ),
            "Solokaden1011",
        )

    def test_opponent_team_name(self):
        self.assertEqual(
            get_opponent_team_name(
                self.game,
                "test_player",
            ),
            "Kraken",
        )


class InningsPitchedTests(unittest.TestCase):
    def test_zero_innings(self):
        self.assertEqual(
            innings_pitched_to_outs(
                "0.0"
            ),
            0,
        )

    def test_whole_innings(self):
        self.assertEqual(
            innings_pitched_to_outs(
                "5.0"
            ),
            15,
        )

    def test_one_partial_out(self):
        self.assertEqual(
            innings_pitched_to_outs(
                "5.1"
            ),
            16,
        )

    def test_two_partial_outs(self):
        self.assertEqual(
            innings_pitched_to_outs(
                "5.2"
            ),
            17,
        )

    def test_ip_without_decimal(self):
        self.assertEqual(
            innings_pitched_to_outs(
                "7"
            ),
            21,
        )

    def test_invalid_partial_inning(self):
        self.assertIsNone(
            innings_pitched_to_outs(
                "5.3"
            )
        )

    def test_invalid_ip_text(self):
        self.assertIsNone(
            innings_pitched_to_outs(
                "abc"
            )
        )

    def test_outs_to_ip(self):
        self.assertEqual(
            outs_to_innings_pitched(
                23
            ),
            "7.2",
        )

    def test_negative_outs_invalid(self):
        self.assertIsNone(
            outs_to_innings_pitched(
                -1
            )
        )


class EraTests(unittest.TestCase):
    def test_era_for_three_er_in_five_and_two_thirds(self):
        outs = (
            innings_pitched_to_outs(
                "5.2"
            )
        )

        self.assertEqual(
            calculate_era(
                3,
                outs,
            ),
            4.76,
        )

    def test_complete_game_one_er(self):
        self.assertEqual(
            calculate_era(
                1,
                27,
            ),
            1.0,
        )

    def test_zero_outs_has_no_era(self):
        self.assertIsNone(
            calculate_era(
                1,
                0,
            )
        )


class SafeConversionTests(unittest.TestCase):
    def test_safe_int(self):
        self.assertEqual(
            safe_int("12"),
            12,
        )

        self.assertIsNone(
            safe_int("")
        )

        self.assertIsNone(
            safe_int("abc")
        )

    def test_safe_float(self):
        self.assertEqual(
            safe_float("5.2"),
            5.2,
        )

        self.assertIsNone(
            safe_float("")
        )

    def test_sum_csv_ints(self):
        self.assertEqual(
            sum_csv_ints(
                "1, 2, , 3"
            ),
            6,
        )


if __name__ == "__main__":
    unittest.main()