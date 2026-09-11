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

        return _event(
            event_type="strikeout",
            player_name=player_name,
            raw_text=statement,
            is_plate_appearance=True,
            is_out=True,
            outs_recorded=1,
            strikeout_type=strikeout_type,
            terminal_pitch_type=(
                _terminal_pitch_type(
                    statement
                )
            ),
        )

    if re.search(
        r"\bwalked\b",
        statement,
        flags=re.IGNORECASE,
    ):
        return _event(
            event_type="walk",
            player_name=_match_player(
                statement,
                r"^(.+?)\s+walked\b",
            ),
            raw_text=statement,
            is_plate_appearance=True,
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

    runner_out_match = re.match(
        r"^(.+?)\s+out\.?$",
        statement,
        flags=re.IGNORECASE,
    )

    if runner_out_match:
        return _event(
            event_type="runner_out",
            player_name=(
                runner_out_match
                .group(1)
                .strip()
            ),
            raw_text=statement,
            is_out=True,
            outs_recorded=1,
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

        batting_team = None

        batting_match = (
            BATTING_TEAM_PATTERN.match(
                body
            )
        )

        if batting_match:
            batting_team = (
                batting_match.group(1)
                .strip()
            )

            body = (
                batting_match.group(2)
                .strip()
            )

        summary_match = (
            INNING_SUMMARY_PATTERN.search(
                body
            )
        )

        summary = (
            parse_inning_summary(
                summary_match.group(0)
            )
            if summary_match
            else None
        )

        event_text = (
            body[
                :summary_match.start()
            ]
            if summary_match
            else body
        )

        inning_events = []
        pending_fielding_code = None

        for statement in _split_statements(
            event_text
        ):
            standalone_fielding = re.fullmatch(
                (
                    r"\(([0-9]+"
                    r"(?:-[0-9]+)+"
                    r"(?:\s+[A-Z]+)?)\)\.?"
                ),
                statement,
                flags=re.IGNORECASE,
            )

            if standalone_fielding:
                pending_fielding_code = (
                    standalone_fielding
                    .group(1)
                    .strip()
                )
                continue

            event = classify_play_statement(
                statement
            )

            if pending_fielding_code:
                if (
                    event["event_type"]
                    in {
                        "runner_out",
                        "caught_stealing",
                    }
                    and not event[
                        "fielding_code"
                    ]
                ):
                    event["fielding_code"] = (
                        pending_fielding_code
                    )
                else:
                    marker = _event(
                        event_type=(
                            "fielding_code_marker"
                        ),
                        player_name=None,
                        raw_text=(
                            f"({pending_fielding_code})."
                        ),
                        fielding_code=(
                            pending_fielding_code
                        ),
                    )

                    marker_enriched = {
                        **marker,
                        "inning": inning,
                        "batting_team": (
                            batting_team
                        ),
                        "source_index": (
                            source_index
                        ),
                    }

                    source_index += 1

                    inning_events.append(
                        marker_enriched
                    )
                    events.append(
                        marker_enriched
                    )

                pending_fielding_code = None

            enriched = {
                **event,
                "inning": inning,
                "batting_team": (
                    batting_team
                ),
                "source_index": (
                    source_index
                ),
            }

            source_index += 1

            if (
                enriched["event_type"]
                == "unknown"
            ):
                unknown_count += 1

            inning_events.append(
                enriched
            )

            events.append(
                enriched
            )

        if pending_fielding_code:
            marker = _event(
                event_type=(
                    "fielding_code_marker"
                ),
                player_name=None,
                raw_text=(
                    f"({pending_fielding_code})."
                ),
                fielding_code=(
                    pending_fielding_code
                ),
            )

            marker_enriched = {
                **marker,
                "inning": inning,
                "batting_team": (
                    batting_team
                ),
                "source_index": (
                    source_index
                ),
            }

            source_index += 1

            inning_events.append(
                marker_enriched
            )
            events.append(
                marker_enriched
            )

        innings.append(
            {
                "inning": inning,
                "batting_team": (
                    batting_team
                ),
                "summary": summary,
                "events": inning_events,
            }
        )

    return {
        "innings": innings,
        "events": events,
        "unknown_count": (
            unknown_count
        ),
    }
