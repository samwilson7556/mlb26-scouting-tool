import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set


VALID_BAT_HANDS = {
    "L",
    "R",
    "S",
}

VALID_THROW_HANDS = {
    "L",
    "R",
}

FIELD_POSITIONS = {
    "C",
    "1B",
    "2B",
    "3B",
    "SS",
    "LF",
    "CF",
    "RF",
    "OF",
}

NAME_SUFFIXES = {
    "jr",
    "sr",
    "ii",
    "iii",
    "iv",
}


def normalize_player_name(
    value: Any,
) -> str:
    """
    Normalize MLBTS display names for conservative card matching.

    Diacritics and punctuation are removed, but token order is retained.
    """
    normalized = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )

    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )

    normalized = normalized.casefold()

    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized,
    )

    return " ".join(
        normalized.split()
    )


def _surname_key(
    value: Any,
) -> str:
    parts = normalize_player_name(
        value
    ).split()

    if not parts:
        return ""

    if (
        len(parts) >= 2
        and parts[-1]
        in NAME_SUFFIXES
    ):
        return parts[-2]

    return parts[-1]


def _normalized_position(
    value: Any,
) -> Optional[str]:
    position = str(
        value or ""
    ).upper().strip()

    if not position:
        return None

    return position


def parse_box_player_label(
    value: Any,
) -> tuple[
    str,
    Optional[str],
]:
    """
    Parse an MLBTS batting box-score player label.

    Examples:
      Wagner, CF
      a-Benge, PH-RF
      3-Keaschall, PR-1B

    PH, PR, and DH by themselves are not defensive positions
    and therefore do not narrow handedness candidates.
    """
    raw = " ".join(
        str(
            value or ""
        ).split()
    )

    if not raw:
        return "", None

    name = raw
    suffix = ""

    if "," in raw:
        name, suffix = raw.rsplit(
            ",",
            1,
        )

        name = name.strip()
        suffix = suffix.strip().upper()

    name = re.sub(
        r"^[A-Za-z0-9]-",
        "",
        name,
    ).strip()

    position = None

    if suffix:
        tokens = [
            token.strip()
            for token in re.split(
                r"[-/]",
                suffix,
            )
            if token.strip()
        ]

        for token in reversed(
            tokens
        ):
            if token in FIELD_POSITIONS:
                position = token
                break

    return name, position


def box_score_batter_entries(
    box_score: Any,
) -> List[Dict[str, Any]]:
    """
    Flatten MLBTS raw box-score batting rows into simple
    team_name/player_name records.
    """
    if not isinstance(
        box_score,
        list,
    ):
        return []

    entries: List[
        Dict[str, Any]
    ] = []

    for team in box_score:
        if not isinstance(
            team,
            dict,
        ):
            continue

        team_id = str(
            team.get(
                "team_id",
                "",
            )
        )

        team_name = team.get(
            "team_name"
        )

        details = team.get(
            team_id,
            {},
        )

        if not isinstance(
            details,
            dict,
        ):
            continue

        batting_stats = details.get(
            "batting_stats",
            [],
        )

        if not isinstance(
            batting_stats,
            list,
        ):
            continue

        for batter in batting_stats:
            if not isinstance(
                batter,
                dict,
            ):
                continue

            entries.append(
                {
                    "team_name": (
                        team_name
                    ),
                    "player_name": (
                        batter.get(
                            "player_name"
                        )
                    ),
                }
            )

    return entries


class BatterPositionResolver:
    """
    Resolve one conservative defensive position for a batter.

    Team-specific information wins. A global fallback is used only
    when that displayed player name has exactly one observed position.
    """

    def __init__(
        self,
        entries: Iterable[
            Dict[str, Any]
        ],
    ) -> None:
        self._by_team: Dict[
            tuple[str, str],
            Set[str],
        ] = defaultdict(set)

        self._global: Dict[
            str,
            Set[str],
        ] = defaultdict(set)

        for entry in entries:
            if not isinstance(
                entry,
                dict,
            ):
                continue

            (
                player_name,
                position,
            ) = parse_box_player_label(
                entry.get(
                    "player_name"
                )
            )

            if (
                not player_name
                or not position
            ):
                continue

            player_key = (
                normalize_player_name(
                    player_name
                )
            )

            if not player_key:
                continue

            team_key = (
                normalize_player_name(
                    entry.get(
                        "team_name"
                    )
                )
            )

            self._global[
                player_key
            ].add(
                position
            )

            if team_key:
                self._by_team[
                    (
                        team_key,
                        player_key,
                    )
                ].add(
                    position
                )

    def resolve(
        self,
        *,
        team_name: Any,
        player_name: Any,
    ) -> Optional[str]:
        player_key = (
            normalize_player_name(
                player_name
            )
        )

        if not player_key:
            return None

        team_key = (
            normalize_player_name(
                team_name
            )
        )

        if team_key:
            team_positions = (
                self._by_team.get(
                    (
                        team_key,
                        player_key,
                    ),
                    set(),
                )
            )

            if len(
                team_positions
            ) == 1:
                return next(
                    iter(
                        team_positions
                    )
                )

        global_positions = (
            self._global.get(
                player_key,
                set(),
            )
        )

        if len(
            global_positions
        ) == 1:
            return next(
                iter(
                    global_positions
                )
            )

        return None


def card_positions(
    item: Dict[str, Any],
) -> Set[str]:
    """
    Return a card's primary and secondary positions in normalized form.
    """
    positions: Set[str] = set()

    primary = _normalized_position(
        item.get(
            "display_position"
        )
    )

    if primary:
        positions.add(
            primary
        )

    secondary = item.get(
        "display_secondary_positions"
    )

    if isinstance(
        secondary,
        str,
    ):
        values = re.split(
            r"[,/]+",
            secondary,
        )

    elif isinstance(
        secondary,
        list,
    ):
        values = secondary

    else:
        values = []

    for value in values:
        position = _normalized_position(
            value
        )

        if position:
            positions.add(
                position
            )

    return positions


def _position_matches(
    observed_position: str,
    item: Dict[str, Any],
) -> bool:
    observed = _normalized_position(
        observed_position
    )

    if observed not in FIELD_POSITIONS:
        return True

    candidate_positions = (
        card_positions(
            item
        )
    )

    if not candidate_positions:
        return True

    if observed in candidate_positions:
        return True

    if (
        observed
        in {
            "LF",
            "CF",
            "RF",
        }
        and "OF"
        in candidate_positions
    ):
        return True

    if (
        observed == "OF"
        and candidate_positions.intersection(
            {
                "LF",
                "CF",
                "RF",
            }
        )
    ):
        return True

    return False


class HandednessResolver:
    """
    Resolve batter/pitcher handedness from MLBTS card metadata.

    Resolution is intentionally conservative:
    - exact normalized full-name match first
    - otherwise suffix/surname candidate matching
    - role filtering
    - optional batter-position narrowing
    - optional starting-pitcher narrowing
    - resolve only when every remaining candidate agrees on the
      relevant handedness
    """

    def __init__(
        self,
        items: Iterable[
            Dict[str, Any]
        ],
    ) -> None:
        self._items: List[
            Dict[str, Any]
        ] = []

        self._by_exact: Dict[
            str,
            List[Dict[str, Any]],
        ] = defaultdict(list)

        self._by_surname: Dict[
            str,
            List[Dict[str, Any]],
        ] = defaultdict(list)

        for value in items:
            if not isinstance(
                value,
                dict,
            ):
                continue

            name = " ".join(
                str(
                    value.get(
                        "name"
                    )
                    or ""
                ).split()
            )

            if not name:
                continue

            item = dict(value)

            normalized_name = (
                normalize_player_name(
                    name
                )
            )

            surname = _surname_key(
                name
            )

            self._items.append(
                item
            )

            self._by_exact[
                normalized_name
            ].append(
                item
            )

            if surname:
                self._by_surname[
                    surname
                ].append(
                    item
                )

    @staticmethod
    def _role_matches(
        item: Dict[str, Any],
        role: str,
    ) -> bool:
        is_hitter = bool(
            item.get(
                "is_hitter"
            )
        )

        two_way = bool(
            item.get(
                "two_way"
            )
        )

        if role == "batter":
            return (
                is_hitter
                or two_way
            )

        if role == "pitcher":
            return (
                (not is_hitter)
                or two_way
            )

        raise ValueError(
            f"Unsupported role: {role}"
        )

    @staticmethod
    def _relevant_hand(
        item: Dict[str, Any],
        role: str,
    ) -> Optional[str]:
        if role == "batter":
            field = "bat_hand"
            valid = VALID_BAT_HANDS
        elif role == "pitcher":
            field = "throw_hand"
            valid = VALID_THROW_HANDS
        else:
            raise ValueError(
                f"Unsupported role: {role}"
            )

        hand = str(
            item.get(field)
            or ""
        ).upper().strip()

        if hand not in valid:
            return None

        return hand

    def _name_candidates(
        self,
        name: Any,
    ) -> tuple[
        List[Dict[str, Any]],
        Optional[str],
    ]:
        normalized = (
            normalize_player_name(
                name
            )
        )

        if not normalized:
            return [], None

        exact = list(
            self._by_exact.get(
                normalized,
                [],
            )
        )

        if exact:
            return exact, "exact"

        surname = _surname_key(
            name
        )

        pool = list(
            self._by_surname.get(
                surname,
                [],
            )
        )

        if not pool:
            return [], None

        # MLBTS play-by-play commonly uses only a surname or a
        # multi-token surname/suffix, such as "Griffey Jr." or
        # "De La Cruz". Prefer cards whose normalized full name
        # actually ends with the complete log label.
        suffix_matches = []

        for item in pool:
            card_name = (
                normalize_player_name(
                    item.get(
                        "name"
                    )
                )
            )

            if (
                card_name == normalized
                or card_name.endswith(
                    f" {normalized}"
                )
            ):
                suffix_matches.append(
                    item
                )

        if suffix_matches:
            return (
                suffix_matches,
                "suffix",
            )

        return pool, "surname"

    def resolve(
        self,
        name: Any,
        role: str,
        *,
        batter_position: Optional[
            str
        ] = None,
        pitcher_is_starter: Optional[
            bool
        ] = None,
    ) -> Dict[str, Any]:
        candidates, method = (
            self._name_candidates(
                name
            )
        )

        candidates = [
            item
            for item in candidates
            if self._role_matches(
                item,
                role,
            )
        ]

        context_used: List[str] = []

        if (
            role == "batter"
            and batter_position
            and _normalized_position(
                batter_position
            )
            in FIELD_POSITIONS
        ):
            narrowed = [
                item
                for item in candidates
                if _position_matches(
                    batter_position,
                    item,
                )
            ]

            # Context is narrowing evidence, not a hard exclusion.
            # If MLBTS card metadata provides no matching position,
            # retain the original candidates rather than guessing.
            if narrowed:
                candidates = narrowed
                context_used.append(
                    "position"
                )

        if (
            role == "pitcher"
            and pitcher_is_starter
            is True
        ):
            starters = [
                item
                for item in candidates
                if (
                    "SP"
                    in card_positions(
                        item
                    )
                )
            ]

            if starters:
                candidates = starters
                context_used.append(
                    "starter"
                )

        hands = sorted(
            {
                hand
                for item in candidates
                if (
                    hand
                    := self._relevant_hand(
                        item,
                        role,
                    )
                )
            }
        )

        candidate_names = sorted(
            {
                str(
                    item.get(
                        "name"
                    )
                    or ""
                )
                for item in candidates
            },
            key=str.casefold,
        )

        if (
            candidates
            and len(hands) == 1
        ):
            status = "resolved"
            hand = hands[0]

        elif candidates:
            status = "ambiguous"
            hand = None

        else:
            status = "unresolved"
            hand = None

        return {
            "status": status,
            "hand": hand,
            "method": method,
            "candidate_count": len(
                candidates
            ),
            "candidate_names": (
                candidate_names
            ),
            "hands": hands,
            "context_used": (
                context_used
            ),
        }

    def resolve_batter(
        self,
        name: Any,
        *,
        position: Optional[
            str
        ] = None,
    ) -> Dict[str, Any]:
        return self.resolve(
            name,
            "batter",
            batter_position=position,
        )

    def resolve_pitcher(
        self,
        name: Any,
        *,
        is_starter: Optional[
            bool
        ] = None,
    ) -> Dict[str, Any]:
        return self.resolve(
            name,
            "pitcher",
            pitcher_is_starter=(
                is_starter
            ),
        )

    def resolve_matchup(
        self,
        *,
        batter_name: Any,
        pitcher_name: Any,
        batter_position: Optional[
            str
        ] = None,
        pitcher_is_starter: Optional[
            bool
        ] = None,
    ) -> Dict[str, Any]:
        batter = self.resolve_batter(
            batter_name,
            position=batter_position,
        )

        pitcher = self.resolve_pitcher(
            pitcher_name,
            is_starter=(
                pitcher_is_starter
            ),
        )

        matchup = None
        effective_bat_hand = None

        batter_hand = batter.get(
            "hand"
        )

        pitcher_hand = pitcher.get(
            "hand"
        )

        if (
            batter.get(
                "status"
            )
            == "resolved"
            and pitcher.get(
                "status"
            )
            == "resolved"
        ):
            if batter_hand in {
                "L",
                "R",
            }:
                effective_bat_hand = (
                    batter_hand
                )

            elif batter_hand == "S":
                effective_bat_hand = (
                    "L"
                    if pitcher_hand == "R"
                    else "R"
                )

            if (
                pitcher_hand
                in VALID_THROW_HANDS
                and effective_bat_hand
                in {
                    "L",
                    "R",
                }
            ):
                matchup = (
                    f"{pitcher_hand}"
                    f"v{effective_bat_hand}"
                )

        return {
            "matchup": matchup,
            "effective_bat_hand": (
                effective_bat_hand
            ),
            "batter": batter,
            "pitcher": pitcher,
        }
