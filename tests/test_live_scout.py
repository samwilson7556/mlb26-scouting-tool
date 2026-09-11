import unittest

from src.live_scout import (
    parse_live_log_stats_for_username,
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
