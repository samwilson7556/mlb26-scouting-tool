from typing import Any, Dict, List, Optional

from .parser import safe_int


TRACKED_NON_PA_EVENTS = {
    "runner_scored",
    "stolen_base",
    "caught_stealing",
    "picked_off",
}


MATCHUP_KEYS = (
    "RvR",
    "RvL",
    "LvR",
    "LvL",
)


MATCHUP_LOCATION_KEYS = (
    "high_in",
    "high",
    "high_away",
    "inside",
    "middle",
    "outside",
    "low_in",
    "low",
    "low_away",
)


def _create_matchup_bucket(
) -> Dict[str, Any]:
    return {
        "plate_appearances": 0,
        "strikeouts": 0,
        "_strikeout_pitches": {},
        "_strikeout_locations": {},
        "_strikeout_location_pitches": {},
        "_strikeout_styles": {},
    }


def hitter_event_is_relevant(
    event: Dict[str, Any],
) -> bool:
    is_plate_appearance = bool(
        safe_int(
            event.get(
                "is_plate_appearance"
            )
        )
    )

    event_type = str(
        event.get(
            "event_type"
        )
        or ""
    )

    return (
        is_plate_appearance
        or event_type
        in TRACKED_NON_PA_EVENTS
    )


def create_hitter_bucket(
    player_name: str,
    **metadata: Any,
) -> Dict[str, Any]:
    return {
        "player_name": player_name,
        **metadata,
        "_games": set(),
        "plate_appearances": 0,
        "hits": 0,
        "singles": 0,
        "doubles": 0,
        "triples": 0,
        "home_runs": 0,
        "walks": 0,
        "intentional_walks": 0,
        "hit_by_pitch": 0,
        "strikeouts": 0,
        "sacrifice_flies": 0,
        "sacrifice_bunts": 0,
        "double_plays": 0,
        "triple_plays": 0,
        "runs": 0,
        "stolen_bases": 0,
        "caught_stealing": 0,
        "picked_off": 0,
        "_strikeout_pitches": {},
        "_strikeout_locations": {},
        "_strikeout_styles": {},
        "_matchups": {
            key: (
                _create_matchup_bucket()
            )
            for key in MATCHUP_KEYS
        },
    }


def _percentage(
    numerator: int,
    denominator: int,
) -> Optional[float]:
    if denominator <= 0:
        return None

    return round(
        numerator
        / denominator
        * 100,
        1,
    )


def _increment_category(
    counts: Dict[str, int],
    value: Any,
) -> None:
    normalized = " ".join(
        str(value or "").split()
    ).casefold()

    if not normalized:
        return

    counts[normalized] = (
        counts.get(
            normalized,
            0,
        )
        + 1
    )


def _category_breakdown(
    counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    total = sum(
        counts.values()
    )

    return [
        {
            "value": value,
            "count": count,
            "pct": _percentage(
                count,
                total,
            ),
        }
        for value, count in sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    ]


def apply_hitter_event(
    bucket: Dict[str, Any],
    event: Dict[str, Any],
    game_id: Any = None,
) -> None:
    if game_id not in {
        None,
        "",
    }:
        bucket[
            "_games"
        ].add(
            str(game_id)
        )

    is_plate_appearance = bool(
        safe_int(
            event.get(
                "is_plate_appearance"
            )
        )
    )

    event_type = str(
        event.get(
            "event_type"
        )
        or ""
    )

    matchup = str(
        event.get(
            "matchup"
        )
        or ""
    ).strip()

    matchup_bucket = None

    if (
        is_plate_appearance
        and matchup in MATCHUP_KEYS
    ):
        matchup_bucket = (
            bucket[
                "_matchups"
            ][matchup]
        )

        matchup_bucket[
            "plate_appearances"
        ] += 1

    if is_plate_appearance:
        bucket[
            "plate_appearances"
        ] += 1

    if bool(
        safe_int(
            event.get(
                "is_hit"
            )
        )
    ):
        bucket[
            "hits"
        ] += 1

        hit_bases = safe_int(
            event.get(
                "hit_bases"
            )
        )

        if hit_bases == 1:
            bucket[
                "singles"
            ] += 1
        elif hit_bases == 2:
            bucket[
                "doubles"
            ] += 1
        elif hit_bases == 3:
            bucket[
                "triples"
            ] += 1
        elif hit_bases == 4:
            bucket[
                "home_runs"
            ] += 1

    if event_type == "walk":
        bucket[
            "walks"
        ] += 1

        if (
            event.get(
                "cause"
            )
            == "intentional_walk"
        ):
            bucket[
                "intentional_walks"
            ] += 1

    elif event_type == "hit_by_pitch":
        bucket[
            "hit_by_pitch"
        ] += 1

    elif event_type == "strikeout":
        bucket[
            "strikeouts"
        ] += 1

        _increment_category(
            bucket[
                "_strikeout_pitches"
            ],
            event.get(
                "terminal_pitch_type"
            ),
        )
        _increment_category(
            bucket[
                "_strikeout_locations"
            ],
            event.get(
                "terminal_pitch_location"
            ),
        )
        _increment_category(
            bucket[
                "_strikeout_styles"
            ],
            event.get(
                "strikeout_type"
            ),
        )

        if matchup_bucket is not None:
            matchup_bucket[
                "strikeouts"
            ] += 1

            _increment_category(
                matchup_bucket[
                    "_strikeout_pitches"
                ],
                event.get(
                    "terminal_pitch_type"
                ),
            )

            _increment_category(
                matchup_bucket[
                    "_strikeout_locations"
                ],
                event.get(
                    "terminal_pitch_location"
                ),
            )

            location = str(
                event.get(
                    "terminal_pitch_location"
                )
                or ""
            ).strip()

            pitch_type = str(
                event.get(
                    "terminal_pitch_type"
                )
                or ""
            ).strip()

            if (
                location
                in MATCHUP_LOCATION_KEYS
                and pitch_type
            ):
                location_pitch_counts = (
                    matchup_bucket[
                        "_strikeout_location_pitches"
                    ].setdefault(
                        location,
                        {},
                    )
                )

                _increment_category(
                    location_pitch_counts,
                    pitch_type,
                )

            _increment_category(
                matchup_bucket[
                    "_strikeout_styles"
                ],
                event.get(
                    "strikeout_type"
                ),
            )

    elif event_type == "sacrifice_fly":
        bucket[
            "sacrifice_flies"
        ] += 1

    elif event_type == "sacrifice_bunt":
        bucket[
            "sacrifice_bunts"
        ] += 1

    elif event_type == "double_play":
        bucket[
            "double_plays"
        ] += 1

    elif event_type == "triple_play":
        bucket[
            "triple_plays"
        ] += 1

    elif event_type == "runner_scored":
        bucket[
            "runs"
        ] += 1

    elif event_type == "stolen_base":
        bucket[
            "stolen_bases"
        ] += 1

    elif event_type == "caught_stealing":
        bucket[
            "caught_stealing"
        ] += 1

    elif event_type == "picked_off":
        bucket[
            "picked_off"
        ] += 1


def finalize_hitter_bucket(
    bucket: Dict[str, Any],
) -> Dict[str, Any]:
    plate_appearances = bucket[
        "plate_appearances"
    ]

    at_bats = max(
        0,
        (
            plate_appearances
            - bucket["walks"]
            - bucket[
                "hit_by_pitch"
            ]
            - bucket[
                "sacrifice_flies"
            ]
            - bucket[
                "sacrifice_bunts"
            ]
        ),
    )

    hits = bucket[
        "hits"
    ]

    pitch_counts = bucket[
        "_strikeout_pitches"
    ]
    location_counts = bucket[
        "_strikeout_locations"
    ]
    style_counts = bucket[
        "_strikeout_styles"
    ]

    row = {
        key: value
        for key, value
        in bucket.items()
        if not key.startswith(
            "_"
        )
    }

    row[
        "games"
    ] = len(
        bucket[
            "_games"
        ]
    )
    row[
        "at_bats"
    ] = at_bats
    row[
        "batting_average"
    ] = (
        round(
            hits / at_bats,
            3,
        )
        if at_bats > 0
        else None
    )
    row[
        "walk_pct"
    ] = _percentage(
        bucket[
            "walks"
        ],
        plate_appearances,
    )
    row[
        "strikeout_pct"
    ] = _percentage(
        bucket[
            "strikeouts"
        ],
        plate_appearances,
    )
    row[
        "home_run_pct"
    ] = _percentage(
        bucket[
            "home_runs"
        ],
        plate_appearances,
    )
    row[
        "strikeout_tendencies"
    ] = {
        "with_finishing_pitch": (
            sum(
                pitch_counts.values()
            )
        ),
        "with_location": (
            sum(
                location_counts.values()
            )
        ),
        "with_style": (
            sum(
                style_counts.values()
            )
        ),
        "finishing_pitches": (
            _category_breakdown(
                pitch_counts
            )
        ),
        "locations": (
            _category_breakdown(
                location_counts
            )
        ),
        "styles": (
            _category_breakdown(
                style_counts
            )
        ),
    }

    matchup_rows = {}

    classified_plate_appearances = 0
    classified_strikeouts = 0

    for matchup in MATCHUP_KEYS:
        matchup_bucket = (
            bucket[
                "_matchups"
            ][matchup]
        )

        matchup_pa = (
            matchup_bucket[
                "plate_appearances"
            ]
        )

        matchup_strikeouts = (
            matchup_bucket[
                "strikeouts"
            ]
        )

        matchup_pitch_counts = (
            matchup_bucket[
                "_strikeout_pitches"
            ]
        )

        matchup_location_counts = (
            matchup_bucket[
                "_strikeout_locations"
            ]
        )

        matchup_style_counts = (
            matchup_bucket[
                "_strikeout_styles"
            ]
        )

        matchup_location_pitch_counts = (
            matchup_bucket[
                "_strikeout_location_pitches"
            ]
        )

        located_strikeouts = sum(
            matchup_location_counts.values()
        )

        classified_plate_appearances += (
            matchup_pa
        )

        classified_strikeouts += (
            matchup_strikeouts
        )

        matchup_rows[
            matchup
        ] = {
            "plate_appearances": matchup_pa,
            "strikeouts": (
                matchup_strikeouts
            ),
            "strikeout_pct": (
                _percentage(
                    matchup_strikeouts,
                    matchup_pa,
                )
            ),
            "with_finishing_pitch": (
                sum(
                    matchup_pitch_counts.values()
                )
            ),
            "with_location": (
                located_strikeouts
            ),
            "location_coverage_pct": (
                _percentage(
                    located_strikeouts,
                    matchup_strikeouts,
                )
            ),
            "with_style": (
                sum(
                    matchup_style_counts.values()
                )
            ),
            "location_counts": {
                location: (
                    matchup_location_counts.get(
                        location,
                        0,
                    )
                )
                for location
                in MATCHUP_LOCATION_KEYS
            },
            "location_pitch_counts": {
                location: dict(
                    sorted(
                        matchup_location_pitch_counts.get(
                            location,
                            {},
                        ).items(),
                        key=lambda item: (
                            -item[1],
                            item[0],
                        ),
                    )
                )
                for location
                in MATCHUP_LOCATION_KEYS
            },
            "finishing_pitches": (
                _category_breakdown(
                    matchup_pitch_counts
                )
            ),
            "locations": (
                _category_breakdown(
                    matchup_location_counts
                )
            ),
            "styles": (
                _category_breakdown(
                    matchup_style_counts
                )
            ),
        }

    row[
        "matchup_strikeout_profiles"
    ] = {
        "classified_plate_appearances": (
            classified_plate_appearances
        ),
        "unclassified_plate_appearances": (
            max(
                0,
                plate_appearances
                - classified_plate_appearances,
            )
        ),
        "coverage_pct": (
            _percentage(
                classified_plate_appearances,
                plate_appearances,
            )
        ),
        "classified_strikeouts": (
            classified_strikeouts
        ),
        "unclassified_strikeouts": (
            max(
                0,
                bucket["strikeouts"]
                - classified_strikeouts,
            )
        ),
        "strikeout_coverage_pct": (
            _percentage(
                classified_strikeouts,
                bucket["strikeouts"],
            )
        ),
        "matchups": matchup_rows,
    }

    return row


def finalize_hitter_buckets(
    buckets: Dict[
        Any,
        Dict[str, Any],
    ],
) -> List[Dict[str, Any]]:
    rows = [
        finalize_hitter_bucket(
            bucket
        )
        for bucket in buckets.values()
    ]

    return sorted(
        rows,
        key=lambda row: (
            -row[
                "plate_appearances"
            ],
            -row[
                "home_runs"
            ],
            row[
                "player_name"
            ].casefold(),
        ),
    )
