import re
from typing import Any, Dict, List, Optional


CONTROL_CODE_PATTERN = re.compile(
    r"\^[^^]*\^"
)

INNING_HEADER_PATTERN = re.compile(
    r"(?=Inning\s+\d+\s*:)",
    re.IGNORECASE,
)

INNING_BLOCK_PATTERN = re.compile(
    r"^Inning\s+(\d+)\s*:\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)

BATTING_TEAM_PATTERN = re.compile(
    r"^(.+?)\s+batting\.\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)

BATTING_SECTION_PATTERN = re.compile(
    r"(?:^|\n)([^\n]+?)\s+batting\.\s*",
    re.IGNORECASE,
)

INNING_SUMMARY_PATTERN = re.compile(
    r"Runs:\s*(\d+)\s+"
    r"Hits:\s*(\d+)\s+"
    r"Walks:\s*(\d+)\s+"
    r"Errors:\s*(\d+)\s+"
    r"Pitches:\s*(\d+)"
    r"(?:\s+Runners Left On:\s*(\d+))?",
    re.IGNORECASE,
)

SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?])\s+"
)

FIELDING_CODE_PATTERN = re.compile(
    r"\(([^()]*)\)\.?$"
)

HOME_RUN_DISTANCE_PATTERN = re.compile(
    r"\((\d+)\s+feet\)",
    re.IGNORECASE,
)

PITCH_TYPE_PATTERN = re.compile(
    r"\b("
    r"fastball|sinker|slider|changeup|curveball|"
    r"cutter|sweeper|slurve|splitter|forkball|"
    r"screwball|knuckleball"
    r")\b",
    re.IGNORECASE,
)


def clean_game_log_text(
    value: str,
) -> str:
    text = str(value or "")

    text = re.sub(
        r"\^n\^",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = CONTROL_CODE_PATTERN.sub(
        " ",
        text,
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n\s+",
        "\n",
        text,
    )

    text = re.sub(
        r"\s+\n",
        "\n",
        text,
    )

    text = re.sub(
        r"\n{2,}",
        "\n",
        text,
    )

    return text.strip()


def parse_inning_summary(
    value: str,
) -> Optional[Dict[str, int]]:
    match = INNING_SUMMARY_PATTERN.search(
        value or ""
    )

    if not match:
        return None

    runners_left_on = (
        int(match.group(6))
        if match.group(6) is not None
        else None
    )

    return {
        "runs": int(match.group(1)),
        "hits": int(match.group(2)),
        "walks": int(match.group(3)),
        "errors": int(match.group(4)),
        "pitches": int(match.group(5)),
        "runners_left_on": runners_left_on,
    }


def _normalize_statement(
    value: str,
) -> str:
    text = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    text = re.sub(
        r"^\*\s*",
        "",
        text,
    )

    return text


def _fielding_code(
    statement: str,
) -> Optional[str]:
    match = FIELDING_CODE_PATTERN.search(
        statement
    )

    if not match:
        return None

    value = match.group(1).strip()

    if re.fullmatch(
        r"\d+\s+feet",
        value,
        flags=re.IGNORECASE,
    ):
        return None

    return value


def _home_run_distance(
    statement: str,
) -> Optional[int]:
    match = HOME_RUN_DISTANCE_PATTERN.search(
        statement
    )

    if not match:
        return None

    return int(match.group(1))


def _terminal_pitch_type(
    statement: str,
) -> Optional[str]:
    match = PITCH_TYPE_PATTERN.search(
        statement
    )

    if not match:
        return None

    return match.group(1).lower()


def _terminal_pitch_location(
    statement: str,
) -> Optional[str]:
    patterns = (
        (
            "low_in",
            r"\blow and in\b",
        ),
        (
            "low_away",
            r"\blow and away\b",
        ),
        (
            "high_in",
            r"\bhigh and in\b",
        ),
        (
            "high_away",
            r"\bhigh and away\b",
        ),
        (
            "middle",
            r"\bdown the middle\b",
        ),
        (
            "inside",
            r"\binside\b",
        ),
        (
            "outside",
            r"\boutside\b",
        ),
        (
            "low",
            r"\blow\b",
        ),
        (
            "high",
            r"\bhigh\b",
        ),
    )

    for location, pattern in patterns:
        if re.search(
            pattern,
            statement,
            flags=re.IGNORECASE,
        ):
            return location

    return None


def _event(
    *,
    event_type: str,
    player_name: Optional[str],
    raw_text: str,
    is_plate_appearance: bool = False,
    is_hit: bool = False,
    is_out: bool = False,
    hit_bases: Optional[int] = None,
    outs_recorded: Optional[int] = None,
    fielding_code: Optional[str] = None,
    destination_base: Optional[str] = None,
    cause: Optional[str] = None,
    strikeout_type: Optional[str] = None,
    home_run_distance_ft: Optional[int] = None,
    terminal_pitch_type: Optional[str] = None,
    terminal_pitch_location: Optional[str] = None,
    secondary_out: bool = False,
    related_player_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event_type": event_type,
        "player_name": player_name,
        "raw_text": raw_text,
        "is_plate_appearance": is_plate_appearance,
        "is_hit": is_hit,
        "is_out": is_out,
        "hit_bases": hit_bases,
        "outs_recorded": outs_recorded,
        "fielding_code": fielding_code,
        "destination_base": destination_base,
        "cause": cause,
        "strikeout_type": strikeout_type,
        "home_run_distance_ft": (
            home_run_distance_ft
        ),
        "terminal_pitch_type": (
            terminal_pitch_type
        ),
        "terminal_pitch_location": (
            terminal_pitch_location
        ),
        "secondary_out": secondary_out,
        "related_player_name": (
            related_player_name
        ),
    }


def _match_player(
    statement: str,
    pattern: str,
) -> Optional[str]:
    match = re.match(
        pattern,
        statement,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).strip()


def _normalize_base(
    value: str,
) -> str:
    normalized = (
        str(value or "")
        .rstrip(".")
        .lower()
    )

    return {
        "first": "1st",
        "second": "2nd",
        "third": "3rd",
    }.get(
        normalized,
        normalized,
    )


def classify_play_statement(
    value: str,
) -> Dict[str, Any]:
    statement = _normalize_statement(
        value
    )

    fielding_code = _fielding_code(
        statement
    )

    if re.search(
        r"\bhomered\b",
        statement,
        flags=re.IGNORECASE,
    ):
        player_name = _match_player(
            statement,
            r"^(.+?)\s+homered\b",
        )

        return _event(
            event_type="home_run",
            player_name=player_name,
            raw_text=statement,
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=4,
            home_run_distance_ft=(
                _home_run_distance(
                    statement
                )
            ),
        )

    if re.search(
        r"\btripled\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="triple",
            player_name=_match_player(
                statement,
                r"^(.+?)\s+tripled\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=3,
        )

    if re.search(
        r"\bdoubled\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="double",
            player_name=_match_player(
                statement,
                r"^(.+?)\s+doubled\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=2,
        )

    if re.search(
        r"\bfor a single\b",
        statement,
        flags=re.IGNORECASE,
    ):
        player_name = _match_player(
            statement,
            (
                r"^(.+?)\s+"
                r"(?:lined|grounded|hit|singled)\b"
            ),
        )

        secondary_out = bool(
            re.search(
                r"\bout while advancing\b",
                statement,
                flags=re.IGNORECASE,
            )
        )

        return _event(
            event_type="single",
            player_name=player_name,
            raw_text=statement,
            is_plate_appearance=True,
            is_hit=True,
            hit_bases=1,
            outs_recorded=(
                1
                if secondary_out
                else None
            ),
            fielding_code=fielding_code,
            secondary_out=secondary_out,
        )

    if (
        re.search(
            r"\bstruck out\b",
            statement,
            flags=re.IGNORECASE,
        )
        or re.search(
            r"\bcalled out on strikes\b",
            statement,
            flags=re.IGNORECASE,
        )
    ):
        if re.search(
            r"\blooking\b",
            statement,
            flags=re.IGNORECASE,
        ):
            strikeout_type = "looking"
        elif re.search(
            r"\bchasing\b",
            statement,
            flags=re.IGNORECASE,
        ):
            strikeout_type = "chasing"
        elif re.search(
            r"\bswinging late\b",
            statement,
            flags=re.IGNORECASE,
        ):
            strikeout_type = "swinging_late"
        elif re.search(
            r"\bswinging\b",
            statement,
            flags=re.IGNORECASE,
        ):
            strikeout_type = "swinging"
        else:
            strikeout_type = "other"

        player_name = _match_player(
            statement,
            (
                r"^(.+?)\s+(?:struck out|"
                r"was called out on strikes)"
            ),
        )

        dropped_third_strike = bool(
            re.search(
                r"\bstruck out but reached first\b",
                statement,
                flags=re.IGNORECASE,
            )
        )

        return _event(
            event_type="strikeout",
            player_name=player_name,
            raw_text=statement,
            is_plate_appearance=True,
            is_out=not dropped_third_strike,
            outs_recorded=(
                None
                if dropped_third_strike
                else 1
            ),
            cause=(
                "dropped_third_strike"
                if dropped_third_strike
                else None
            ),
            strikeout_type=strikeout_type,
            terminal_pitch_type=(
                _terminal_pitch_type(
                    statement
                )
            ),
            terminal_pitch_location=(
                _terminal_pitch_location(
                    statement
                )
            ),
        )

    if re.search(
        r"\bwalked\b",
        statement,
        flags=re.IGNORECASE,
    ):
        intentional_walk = bool(
            re.search(
                r"\bwas intentionally walked\b",
                statement,
                flags=re.IGNORECASE,
            )
        )

        return _event(
            event_type="walk",
            player_name=_match_player(
                statement,
                (
                    r"^(.+?)\s+"
                    r"(?:was intentionally\s+)?"
                    r"walked\b"
                ),
            ),
            raw_text=statement,
            is_plate_appearance=True,
            cause=(
                "intentional_walk"
                if intentional_walk
                else None
            ),
        )

    if re.search(
        r"\bwas hit by a pitch\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="hit_by_pitch",
            player_name=_match_player(
                statement,
                r"^(.+?)\s+was hit by a pitch\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
        )

    if re.search(
        r"\bhit a sacrifice fly\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="sacrifice_fly",
            player_name=_match_player(
                statement,
                r"^(.+?)\s+hit a sacrifice fly\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=1,
            fielding_code=fielding_code,
        )

    sacrifice_bunt_match = re.match(
        r"^(.+?)\s+sacrificed to\s+.+?\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if sacrifice_bunt_match:
        return _event(
            event_type="sacrifice_bunt",
            player_name=(
                sacrifice_bunt_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=1,
            fielding_code=fielding_code,
        )

    if re.search(
        r"\bbunted out\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="bunt_out",
            player_name=_match_player(
                statement,
                r"^(.+?)\s+bunted out\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=1,
            fielding_code=fielding_code,
        )

    if re.search(
        r"\bbatted out\b",
        statement,
        flags=re.IGNORECASE,
    ):
        event_type = (
            "line_out"
            if (
                fielding_code
                and fielding_code.upper()
                .startswith("L")
            )
            else "batted_out"
        )

        return _event(
            event_type=event_type,
            player_name=_match_player(
                statement,
                r"^(.+?)\s+batted out\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=1,
            fielding_code=fielding_code,
        )

    triple_play_match = re.match(
        (
            r"^(.+?)\s+(?:lined|hit)\s+"
            r"into a triple play\b"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if triple_play_match:
        return _event(
            event_type="triple_play",
            player_name=(
                triple_play_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=3,
            fielding_code=fielding_code,
        )

    double_play_match = re.match(
        (
            r"^(.+?)\s+(?:lined|hit)\s+"
            r"into a double play\b"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if double_play_match:
        return _event(
            event_type="double_play",
            player_name=(
                double_play_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=2,
            fielding_code=fielding_code,
        )

    if re.search(
        r"\bgrounded into a double play\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="double_play",
            player_name=_match_player(
                statement,
                (
                    r"^(.+?)\s+grounded into "
                    r"a double play\b"
                ),
            ),
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=2,
            fielding_code=fielding_code,
        )

    for event_type, verb in (
        ("ground_out", "grounded out"),
        ("fly_out", "flied out"),
        ("line_out", "lined out"),
        ("pop_out", "popped out"),
    ):
        if re.search(
            rf"\b{re.escape(verb)}\b",
            statement,
            flags=re.IGNORECASE,
        ):
            return _event(
                event_type=event_type,
                player_name=_match_player(
                    statement,
                    (
                        rf"^(.+?)\s+"
                        rf"{re.escape(verb)}\b"
                    ),
                ),
                raw_text=statement,
                is_plate_appearance=True,
                is_out=True,
                outs_recorded=1,
                fielding_code=fielding_code,
            )

    fielders_choice_reached_match = re.match(
        (
            r"^(.+?)\s+reached\s+"
            r"(first|second|third|1st|2nd|3rd)\s+"
            r"on fielder'?s choice\b"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if fielders_choice_reached_match:
        return _event(
            event_type="fielders_choice",
            player_name=(
                fielders_choice_reached_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            is_plate_appearance=True,
            outs_recorded=(
                2
                if "double play"
                in statement.lower()
                else None
            ),
            fielding_code=fielding_code,
            destination_base=_normalize_base(
                fielders_choice_reached_match
                .group(2)
            ),
        )

    if re.search(
        r"\breached first on fielder'?s choice\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="fielders_choice",
            player_name=_match_player(
                statement,
                (
                    r"^(.+?)\s+reached first "
                    r"on fielder'?s choice\b"
                ),
            ),
            raw_text=statement,
            is_plate_appearance=True,
            fielding_code=fielding_code,
        )

    if re.search(
        r"\breached first on .*error\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="reached_error",
            player_name=_match_player(
                statement,
                (
                    r"^(.+?)\s+reached first "
                    r"on .*error\b"
                ),
            ),
            raw_text=statement,
            is_plate_appearance=True,
            fielding_code=fielding_code,
        )

    stolen_match = re.match(
        r"^(.+?)\s+stole\s+(\S+)\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if stolen_match:
        return _event(
            event_type="stolen_base",
            player_name=(
                stolen_match.group(1).strip()
            ),
            raw_text=statement,
            destination_base=(
                stolen_match.group(2)
                .rstrip(".")
                .lower()
            ),
        )

    stole_without_base_match = re.match(
        r"^(.+?)\s+stole\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if stole_without_base_match:
        return _event(
            event_type="stolen_base",
            player_name=(
                stole_without_base_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
        )

    picked_off_match = re.match(
        r"^(.+?)\s+was picked off\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if picked_off_match:
        return _event(
            event_type="picked_off",
            player_name=(
                picked_off_match.group(1).strip()
            ),
            raw_text=statement,
            is_out=True,
            outs_recorded=1,
            cause="picked_off",
        )

    caught_match = re.match(
        r"^(.+?)\s+was caught stealing\b",
        statement,
        flags=re.IGNORECASE,
    )

    if caught_match:
        return _event(
            event_type="caught_stealing",
            player_name=(
                caught_match.group(1).strip()
            ),
            raw_text=statement,
            is_out=True,
            outs_recorded=1,
        )

    scored_wild_pitch_match = re.match(
        (
            r"^(.+?)\s+(?:scored|scores)\s+"
            r"on\s+a\s+wild pitch\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if scored_wild_pitch_match:
        return _event(
            event_type="runner_scored",
            player_name=(
                scored_wild_pitch_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            destination_base="home",
            cause="wild_pitch",
        )

    scored_error_match = re.match(
        (
            r"^(.+?)\s+(?:scored|scores)\s+on\s+"
            r"(?:a\s+)?(throwing|fielding)\s+error"
            r"(?:\s+by\s+.+?)?"
            r"(?:\s+\([^()]*\))?\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if scored_error_match:
        return _event(
            event_type="runner_scored",
            player_name=(
                scored_error_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            destination_base="home",
            cause=(
                f"{scored_error_match.group(2).lower()}_error"
            ),
            fielding_code=fielding_code,
        )

    scored_match = re.match(
        r"^(.+?)\s+scores?\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if scored_match:
        return _event(
            event_type="runner_scored",
            player_name=(
                scored_match.group(1).strip()
            ),
            raw_text=statement,
            destination_base="home",
        )

    reached_base_match = re.match(
        (
            r"^(.+?)\s+reached\s+"
            r"(first|second|third|1st|2nd|3rd)"
            r"(?:\s+on\s+(.+?))?\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if reached_base_match:
        cause_text = (
            reached_base_match.group(3)
            or ""
        ).lower()

        if (
            "wild pitch" in cause_text
            and "throwing error"
            in cause_text
        ):
            cause = (
                "wild_pitch_throwing_error"
            )
        elif "wild pitch" in cause_text:
            cause = "wild_pitch"
        elif "passed ball" in cause_text:
            cause = "passed_ball"
        elif "throwing error" in cause_text:
            cause = "throwing_error"
        elif "fielding error" in cause_text:
            cause = "fielding_error"
        else:
            cause = None

        return _event(
            event_type="runner_advanced",
            player_name=(
                reached_base_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            destination_base=_normalize_base(
                reached_base_match.group(2)
            ),
            cause=cause,
            fielding_code=fielding_code,
        )

    error_advance_match = re.match(
        (
            r"^(.+?)\s+advances?\s+to\s+"
            r"(\S+)\s+on\s+(?:a\s+)?"
            r"(throwing|fielding)\s+error\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if error_advance_match:
        return _event(
            event_type="runner_advanced",
            player_name=(
                error_advance_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            destination_base=(
                error_advance_match
                .group(2)
                .rstrip(".")
                .lower()
            ),
            cause=(
                f"{error_advance_match.group(3).lower()}_error"
            ),
        )

    advance_match = re.match(
        (
            r"^(.+?)\s+advances?\s+to\s+"
            r"(\S+)"
            r"(?:\s+on\s+a\s+wild pitch)?\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if advance_match:
        return _event(
            event_type="runner_advanced",
            player_name=(
                advance_match.group(1).strip()
            ),
            raw_text=statement,
            destination_base=(
                advance_match.group(2)
                .rstrip(".")
                .lower()
            ),
            cause=(
                "wild_pitch"
                if "wild pitch"
                in statement.lower()
                else None
            ),
        )

    wild_pitch_match = re.match(
        (
            r"^(.+?)\s+reached\s+(\S+)\s+"
            r"on\s+a\s+wild pitch\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if wild_pitch_match:
        return _event(
            event_type="runner_advanced",
            player_name=(
                wild_pitch_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            destination_base=(
                wild_pitch_match
                .group(2)
                .rstrip(".")
                .lower()
            ),
            cause="wild_pitch",
        )

    balk_match = re.match(
        r"^(.+?)\s+balks,\s+runners advance\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if balk_match:
        return _event(
            event_type="balk",
            player_name=(
                balk_match.group(1).strip()
            ),
            raw_text=statement,
            cause="balk",
        )

    wild_throw_match = re.match(
        r"^(.+?)\s+throws wild at first\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if wild_throw_match:
        return _event(
            event_type="throwing_error",
            player_name=(
                wild_throw_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            destination_base="1st",
            cause="throwing_error",
        )

    runner_out_match = re.match(
        r"^(.+?)(?:\s+was)?\s+out\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if runner_out_match:
        # MLBTS also emits generic runner-status lines such as
        # "Runner out." and "Runner was out." These are useful
        # context, but they are not reliable atomic out events:
        # the same runner can later appear in scoring/advance
        # bookkeeping. Preserve the status without claiming an
        # additional authoritative out.
        return _event(
            event_type="runner_out",
            player_name=(
                runner_out_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            is_out=True,
        )

    pinch_runner_match = re.match(
        (
            r"^(.+?)\s+pinch runs for\s+"
            r"(.+?)\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if pinch_runner_match:
        return _event(
            event_type="pinch_runner",
            player_name=(
                pinch_runner_match
                .group(1)
                .strip()
            ),
            related_player_name=(
                pinch_runner_match
                .group(2)
                .strip()
            ),
            raw_text=statement,
        )

    substitution_match = re.match(
        (
            r"^(.+?)\s+substituted for\s+"
            r"(.+?)\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if substitution_match:
        return _event(
            event_type="substitution",
            player_name=(
                substitution_match
                .group(1)
                .strip()
            ),
            related_player_name=(
                substitution_match
                .group(2)
                .strip()
            ),
            raw_text=statement,
        )

    pinch_hit_match = re.match(
        (
            r"^(.+?)\s+pinch hit for\s+"
            r"(.+?)\.?$"
        ),
        statement,
        flags=re.IGNORECASE,
    )

    if pinch_hit_match:
        return _event(
            event_type="pinch_hit",
            player_name=(
                pinch_hit_match
                .group(1)
                .strip()
            ),
            related_player_name=(
                pinch_hit_match
                .group(2)
                .strip()
            ),
            raw_text=statement,
        )

    batter_match = re.match(
        r"^(.+?)\s+at bat\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if batter_match:
        return _event(
            event_type="batter_marker",
            player_name=(
                batter_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
        )

    bullpen_match = re.match(
        r"^(.+?)\s+in bullpen\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if bullpen_match:
        return _event(
            event_type="bullpen_marker",
            player_name=(
                bullpen_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
        )

    pitcher_match = re.match(
        r"^(.+?)\s+pitching\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if pitcher_match:
        return _event(
            event_type="pitcher_marker",
            player_name=(
                pitcher_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
        )

    return _event(
        event_type="unknown",
        player_name=None,
        raw_text=statement,
    )


def _split_statements(
    value: str,
) -> List[str]:
    normalized = re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()

    if not normalized:
        return []

    protected = re.sub(
        r"\b(Jr|Sr)\.",
        r"\1<prd>",
        normalized,
        flags=re.IGNORECASE,
    )

    protected = re.sub(
        (
            r"\b([A-Z])\."
            r"(?=\s+[A-Z][A-Za-z])"
        ),
        r"\1<prd>",
        protected,
    )

    statements = []

    for raw_statement in (
        SENTENCE_SPLIT_PATTERN.split(
            protected
        )
    ):
        restored = raw_statement.replace(
            "<prd>",
            ".",
        )

        statement = _normalize_statement(
            restored
        )

        if statement:
            statements.append(
                statement
            )

    return statements


def _split_batting_sections(
    body: str,
) -> List[Dict[str, Any]]:
    matches = list(
        BATTING_SECTION_PATTERN.finditer(
            body or ""
        )
    )

    if not matches:
        return [
            {
                "batting_team": None,
                "body": (body or "").strip(),
            }
        ]

    sections: List[Dict[str, Any]] = []

    for index, match in enumerate(
        matches
    ):
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(body)
        )

        sections.append(
            {
                "batting_team": (
                    match.group(1).strip()
                ),
                "body": (
                    body[start:end].strip()
                ),
            }
        )

    return sections


def parse_game_log_text(
    value: str,
) -> Dict[str, Any]:
    clean_text = clean_game_log_text(
        value
    )

    raw_blocks = [
        block.strip()
        for block in (
            INNING_HEADER_PATTERN.split(
                clean_text
            )
        )
        if block.strip()
    ]

    innings: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    unknown_count = 0
    source_index = 0

    for raw_block in raw_blocks:
        block_match = (
            INNING_BLOCK_PATTERN.match(
                raw_block
            )
        )

        if not block_match:
            continue

        inning = int(
            block_match.group(1)
        )
        body = (
            block_match.group(2)
            .strip()
        )

        for batting_section in _split_batting_sections(body):
            batting_team = batting_section.get("batting_team")
            section_body = str(
                batting_section.get("body", "")
            ).strip()

            if batting_team is None:
                batting_match = BATTING_TEAM_PATTERN.match(section_body)
                if batting_match:
                    batting_team = batting_match.group(1).strip()
                    section_body = batting_match.group(2).strip()

            summary_match = INNING_SUMMARY_PATTERN.search(section_body)
            summary = (
                parse_inning_summary(summary_match.group(0))
                if summary_match
                else None
            )
            event_text = (
                section_body[:summary_match.start()]
                if summary_match
                else section_body
            )

            inning_events = []
            pending_fielding_code = None
            recorded_outs = 0

            for statement in _split_statements(event_text):
                # Some MLBTS logs contain stale/duplicated play text
                # after a batting side has already recorded three
                # authoritative outs. Do not treat that trailing text
                # as part of the completed half-inning.
                if recorded_outs >= 3:
                    break

                standalone_fielding = re.fullmatch(
                    (
                        r"\(("
                        r"(?:[LE]?\d+"
                        r"(?:-\d+)*"
                        r"(?:U)?)"
                        r"(?:\s+(?:DP|TP|FC|SH))?"
                        r")\)\.?"
                    ),
                    statement,
                    flags=re.IGNORECASE,
                )

                if standalone_fielding:
                    pending_fielding_code = standalone_fielding.group(1).strip()
                    continue

                event = classify_play_statement(statement)

                is_was_out = bool(
                    re.match(
                        r"^.+?\s+was\s+out\.?$",
                        statement,
                        flags=re.IGNORECASE,
                    )
                )

                if (
                    is_was_out
                    and inning_events
                    and inning_events[-1]["event_type"]
                    in {
                        "picked_off",
                        "caught_stealing",
                    }
                    and (
                        inning_events[-1].get(
                            "player_name"
                        )
                        or ""
                    ).casefold()
                    == (
                        event.get(
                            "player_name"
                        )
                        or ""
                    ).casefold()
                ):
                    continue

                if (
                    is_was_out
                    and recorded_outs >= 3
                ):
                    continue

                if pending_fielding_code:
                    if (
                        event["event_type"] in {"runner_out", "caught_stealing"}
                        and not event["fielding_code"]
                    ):
                        event["fielding_code"] = pending_fielding_code
                    else:
                        marker = _event(
                            event_type="fielding_code_marker",
                            player_name=None,
                            raw_text=f"({pending_fielding_code}).",
                            fielding_code=pending_fielding_code,
                        )
                        marker_enriched = {
                            **marker,
                            "inning": inning,
                            "batting_team": batting_team,
                            "source_index": source_index,
                        }
                        source_index += 1
                        inning_events.append(marker_enriched)
                        events.append(marker_enriched)
                    pending_fielding_code = None

                enriched = {
                    **event,
                    "inning": inning,
                    "batting_team": batting_team,
                    "source_index": source_index,
                }
                source_index += 1

                if enriched["event_type"] == "unknown":
                    unknown_count += 1

                recorded_outs += (
                    enriched.get(
                        "outs_recorded"
                    )
                    or 0
                )

                inning_events.append(enriched)
                events.append(enriched)

            if pending_fielding_code:
                marker = _event(
                    event_type="fielding_code_marker",
                    player_name=None,
                    raw_text=f"({pending_fielding_code}).",
                    fielding_code=pending_fielding_code,
                )
                marker_enriched = {
                    **marker,
                    "inning": inning,
                    "batting_team": batting_team,
                    "source_index": source_index,
                }
                source_index += 1
                inning_events.append(marker_enriched)
                events.append(marker_enriched)

            innings.append(
                {
                    "inning": inning,
                    "batting_team": batting_team,
                    "summary": summary,
                    "events": inning_events,
                }
            )

    return {
        "innings": innings,
        "events": events,
        "unknown_count": unknown_count,
    }
