import unittest

from src.player_handedness import (
    BatterPositionResolver,
    HandednessResolver,
    box_score_batter_entries,
    normalize_player_name,
    parse_box_player_label,
)


def hitter(
    name,
    hand,
    position,
    *,
    secondary="",
    two_way=False,
):
    return {
        "name": name,
        "is_hitter": True,
        "two_way": two_way,
        "bat_hand": hand,
        "throw_hand": "R",
        "display_position": (
            position
        ),
        "display_secondary_positions": (
            secondary
        ),
    }


def pitcher(
    name,
    hand,
    position,
):
    return {
        "name": name,
        "is_hitter": False,
        "two_way": False,
        "bat_hand": "R",
        "throw_hand": hand,
        "display_position": (
            position
        ),
        "display_secondary_positions": "",
    }


class PlayerNameNormalizationTests(
    unittest.TestCase
):
    def test_diacritics_and_punctuation_are_normalized(
        self,
    ):
        self.assertEqual(
            normalize_player_name(
                "José O'Day Jr."
            ),
            "jose o day jr",
        )


class BatterPositionContextTests(
    unittest.TestCase
):
    def test_standard_position_suffix_is_parsed(
        self,
    ):
        self.assertEqual(
            parse_box_player_label(
                "Wagner, CF"
            ),
            (
                "Wagner",
                "CF",
            ),
        )

    def test_substitution_prefix_and_defensive_suffix_are_parsed(
        self,
    ):
        self.assertEqual(
            parse_box_player_label(
                "a-Benge, PH-RF"
            ),
            (
                "Benge",
                "RF",
            ),
        )

        self.assertEqual(
            parse_box_player_label(
                "3-Keaschall, PR-1B"
            ),
            (
                "Keaschall",
                "1B",
            ),
        )

    def test_dh_without_defensive_position_does_not_narrow(
        self,
    ):
        self.assertEqual(
            parse_box_player_label(
                "Schwarber, DH"
            ),
            (
                "Schwarber",
                None,
            ),
        )

    def test_team_specific_position_wins(
        self,
    ):
        resolver = BatterPositionResolver(
            [
                {
                    "team_name": "Team A",
                    "player_name": (
                        "Jones, RF"
                    ),
                },
                {
                    "team_name": "Team B",
                    "player_name": (
                        "Jones, CF"
                    ),
                },
            ]
        )

        self.assertEqual(
            resolver.resolve(
                team_name="Team A",
                player_name="Jones",
            ),
            "RF",
        )

        self.assertEqual(
            resolver.resolve(
                team_name="Team B",
                player_name="Jones",
            ),
            "CF",
        )

        self.assertIsNone(
            resolver.resolve(
                team_name="Unknown Team",
                player_name="Jones",
            )
        )

    def test_unique_global_position_is_safe_fallback(
        self,
    ):
        resolver = BatterPositionResolver(
            [
                {
                    "team_name": "Team A",
                    "player_name": (
                        "Wagner, LF"
                    ),
                },
                {
                    "team_name": "Team B",
                    "player_name": (
                        "Wagner, LF"
                    ),
                },
            ]
        )

        self.assertEqual(
            resolver.resolve(
                team_name="Different Team",
                player_name="Wagner",
            ),
            "LF",
        )

    def test_multiple_positions_for_same_team_are_ambiguous(
        self,
    ):
        resolver = BatterPositionResolver(
            [
                {
                    "team_name": "Team A",
                    "player_name": (
                        "Utility, 2B"
                    ),
                },
                {
                    "team_name": "Team A",
                    "player_name": (
                        "Utility, 3B"
                    ),
                },
            ]
        )

        self.assertIsNone(
            resolver.resolve(
                team_name="Team A",
                player_name="Utility",
            )
        )

    def test_raw_box_score_is_flattened(
        self,
    ):
        box_score = [
            {
                "team_id": "1",
                "team_name": "Test Team",
                "1": {
                    "batting_stats": [
                        {
                            "player_name": (
                                "Lindor, SS"
                            ),
                        },
                        {
                            "player_name": (
                                "Schwarber, DH"
                            ),
                        },
                    ],
                },
            }
        ]

        self.assertEqual(
            box_score_batter_entries(
                box_score
            ),
            [
                {
                    "team_name": (
                        "Test Team"
                    ),
                    "player_name": (
                        "Lindor, SS"
                    ),
                },
                {
                    "team_name": (
                        "Test Team"
                    ),
                    "player_name": (
                        "Schwarber, DH"
                    ),
                },
            ],
        )


class HandednessResolverTests(
    unittest.TestCase
):
    def test_multi_token_suffix_prefers_full_log_label(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Elly De La Cruz",
                        "S",
                        "SS",
                    ),
                    hitter(
                        "Oneil Cruz",
                        "L",
                        "SS",
                    ),
                ]
            )
        )

        result = resolver.resolve_batter(
            "De La Cruz",
            position="SS",
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "S",
        )

        self.assertEqual(
            result["method"],
            "suffix",
        )

    def test_suffix_with_junior_is_supported(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Ken Griffey Jr.",
                        "L",
                        "CF",
                    ),
                ]
            )
        )

        result = resolver.resolve_batter(
            "Griffey Jr.",
            position="CF",
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "L",
        )

    def test_ambiguous_handedness_is_not_guessed(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Player Jones",
                        "L",
                        "RF",
                    ),
                    hitter(
                        "Other Jones",
                        "R",
                        "CF",
                    ),
                ]
            )
        )

        result = resolver.resolve_batter(
            "Jones"
        )

        self.assertEqual(
            result["status"],
            "ambiguous",
        )

        self.assertIsNone(
            result["hand"]
        )

    def test_position_can_resolve_ambiguous_batter(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Player Jones",
                        "L",
                        "RF",
                    ),
                    hitter(
                        "Other Jones",
                        "R",
                        "CF",
                    ),
                ]
            )
        )

        result = resolver.resolve_batter(
            "Jones",
            position="RF",
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "L",
        )

        self.assertEqual(
            result["context_used"],
            [
                "position",
            ],
        )

    def test_outfield_alias_can_match_specific_outfield_position(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Player Wagner",
                        "R",
                        "OF",
                    ),
                ]
            )
        )

        result = resolver.resolve_batter(
            "Wagner",
            position="LF",
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "R",
        )

    def test_position_with_no_matching_card_falls_back_safely(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Player Smith",
                        "L",
                        "1B",
                    ),
                    hitter(
                        "Other Smith",
                        "L",
                        "3B",
                    ),
                ]
            )
        )

        result = resolver.resolve_batter(
            "Smith",
            position="CF",
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "L",
        )

        self.assertEqual(
            result["context_used"],
            [],
        )

    def test_starting_pitcher_context_can_resolve_surname(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    pitcher(
                        "Starter Suarez",
                        "L",
                        "SP",
                    ),
                    pitcher(
                        "Reliever Suarez",
                        "R",
                        "RP",
                    ),
                ]
            )
        )

        result = resolver.resolve_pitcher(
            "Suarez",
            is_starter=True,
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "L",
        )

        self.assertEqual(
            result["context_used"],
            [
                "starter",
            ],
        )

    def test_reliever_is_not_forced_to_rp_card(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    pitcher(
                        "Starter Suarez",
                        "L",
                        "SP",
                    ),
                    pitcher(
                        "Reliever Suarez",
                        "R",
                        "RP",
                    ),
                ]
            )
        )

        result = resolver.resolve_pitcher(
            "Suarez",
            is_starter=False,
        )

        self.assertEqual(
            result["status"],
            "ambiguous",
        )

        self.assertIsNone(
            result["hand"]
        )

    def test_switch_hitter_faces_right_handed_pitcher_from_left_side(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Switch Batter",
                        "S",
                        "SS",
                    ),
                    pitcher(
                        "Right Pitcher",
                        "R",
                        "SP",
                    ),
                ]
            )
        )

        result = resolver.resolve_matchup(
            batter_name=(
                "Switch Batter"
            ),
            batter_position="SS",
            pitcher_name=(
                "Right Pitcher"
            ),
            pitcher_is_starter=True,
        )

        self.assertEqual(
            result["matchup"],
            "RvL",
        )

        self.assertEqual(
            result[
                "effective_bat_hand"
            ],
            "L",
        )

    def test_switch_hitter_faces_left_handed_pitcher_from_right_side(
        self,
    ):
        resolver = (
            HandednessResolver(
                [
                    hitter(
                        "Switch Batter",
                        "S",
                        "SS",
                    ),
                    pitcher(
                        "Left Pitcher",
                        "L",
                        "SP",
                    ),
                ]
            )
        )

        result = resolver.resolve_matchup(
            batter_name=(
                "Switch Batter"
            ),
            batter_position="SS",
            pitcher_name=(
                "Left Pitcher"
            ),
            pitcher_is_starter=True,
        )

        self.assertEqual(
            result["matchup"],
            "LvR",
        )

        self.assertEqual(
            result[
                "effective_bat_hand"
            ],
            "R",
        )


if __name__ == "__main__":
    unittest.main()
