import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .player_handedness import (
    HandednessResolver,
)


DEFAULT_BASE_URL = (
    "https://mlb26.theshow.com"
)

DEFAULT_CACHE_MAX_AGE_SECONDS = (
    24 * 60 * 60
)

DEFAULT_PAGE_DELAY_SECONDS = 0.03


def _utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _cache_age_seconds(
    path: Path,
) -> Optional[float]:
    try:
        modified = path.stat().st_mtime
    except OSError:
        return None

    return max(
        0.0,
        time.time() - modified,
    )


def _read_cache(
    path: Path,
) -> Optional[
    Dict[str, Any]
]:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        payload,
        dict,
    ):
        return None

    items = payload.get(
        "items"
    )

    if not isinstance(
        items,
        list,
    ):
        return None

    return payload


def load_cached_catalog(
    cache_path: Path,
) -> Optional[
    List[Dict[str, Any]]
]:
    payload = _read_cache(
        cache_path
    )

    if payload is None:
        return None

    return [
        item
        for item in payload[
            "items"
        ]
        if isinstance(
            item,
            dict,
        )
    ]


def catalog_cache_is_fresh(
    cache_path: Path,
    max_age_seconds: float,
) -> bool:
    age = _cache_age_seconds(
        cache_path
    )

    return (
        age is not None
        and age
        <= max_age_seconds
        and _read_cache(
            cache_path
        )
        is not None
    )


def fetch_card_catalog(
    *,
    base_url: str = (
        DEFAULT_BASE_URL
    ),
    session: Optional[
        requests.Session
    ] = None,
    page_delay_seconds: float = (
        DEFAULT_PAGE_DELAY_SECONDS
    ),
) -> List[Dict[str, Any]]:
    """
    Fetch the complete MLB26 mlb_card catalog.

    The endpoint is paginated at 25 cards per page. The first
    response supplies total_pages; remaining pages are then fetched
    sequentially with a small delay.
    """
    owns_session = (
        session is None
    )

    active_session = (
        session
        if session is not None
        else requests.Session()
    )

    if owns_session:
        active_session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "MLB26 Scouting Tool"
                ),
                "Accept": (
                    "application/json,"
                    "text/plain,*/*"
                ),
            }
        )

    try:
        first = active_session.get(
            (
                f"{base_url.rstrip('/')}"
                "/apis/items.json"
            ),
            params={
                "type": "mlb_card",
                "page": 1,
            },
            timeout=30,
        )

        first.raise_for_status()

        payload = first.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "MLBTS item catalog response "
                "was not an object."
            )

        first_items = payload.get(
            "items",
            [],
        )

        if not isinstance(
            first_items,
            list,
        ):
            raise ValueError(
                "MLBTS item catalog response "
                "did not contain an items list."
            )

        items: List[
            Dict[str, Any]
        ] = [
            item
            for item in first_items
            if isinstance(
                item,
                dict,
            )
        ]

        total_pages = int(
            payload.get(
                "total_pages",
                1,
            )
            or 1
        )

        for page in range(
            2,
            total_pages + 1,
        ):
            if (
                page_delay_seconds
                > 0
            ):
                time.sleep(
                    page_delay_seconds
                )

            response = (
                active_session.get(
                    (
                        f"{base_url.rstrip('/')}"
                        "/apis/items.json"
                    ),
                    params={
                        "type": (
                            "mlb_card"
                        ),
                        "page": page,
                    },
                    timeout=30,
                )
            )

            response.raise_for_status()

            page_payload = (
                response.json()
            )

            if not isinstance(
                page_payload,
                dict,
            ):
                raise ValueError(
                    "MLBTS item catalog page "
                    f"{page} was not an object."
                )

            page_items = (
                page_payload.get(
                    "items",
                    [],
                )
            )

            if not isinstance(
                page_items,
                list,
            ):
                raise ValueError(
                    "MLBTS item catalog page "
                    f"{page} did not contain "
                    "an items list."
                )

            items.extend(
                item
                for item in page_items
                if isinstance(
                    item,
                    dict,
                )
            )

        return items

    finally:
        if owns_session:
            active_session.close()


def write_catalog_cache(
    cache_path: Path,
    items: List[
        Dict[str, Any]
    ],
) -> None:
    cache_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "fetched_at": (
            _utc_timestamp()
        ),
        "items": items,
    }

    temporary = (
        cache_path.with_suffix(
            cache_path.suffix
            + ".tmp"
        )
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary.replace(
        cache_path
    )


def get_card_catalog(
    *,
    cache_path: Path,
    base_url: str = (
        DEFAULT_BASE_URL
    ),
    max_age_seconds: float = (
        DEFAULT_CACHE_MAX_AGE_SECONDS
    ),
    session: Optional[
        requests.Session
    ] = None,
    page_delay_seconds: float = (
        DEFAULT_PAGE_DELAY_SECONDS
    ),
) -> List[Dict[str, Any]]:
    """
    Return a locally cached MLB26 card catalog when fresh.

    When refresh fails, a valid stale cache is preferred over
    losing handedness functionality entirely. If no usable cache
    exists, the original refresh exception is raised.
    """
    cached = load_cached_catalog(
        cache_path
    )

    if (
        cached is not None
        and catalog_cache_is_fresh(
            cache_path,
            max_age_seconds,
        )
    ):
        return cached

    try:
        items = fetch_card_catalog(
            base_url=base_url,
            session=session,
            page_delay_seconds=(
                page_delay_seconds
            ),
        )

        write_catalog_cache(
            cache_path,
            items,
        )

        return items

    except Exception:
        if cached is not None:
            return cached

        raise


def get_handedness_resolver(
    *,
    cache_path: Path,
    base_url: str = (
        DEFAULT_BASE_URL
    ),
    max_age_seconds: float = (
        DEFAULT_CACHE_MAX_AGE_SECONDS
    ),
    session: Optional[
        requests.Session
    ] = None,
    page_delay_seconds: float = (
        DEFAULT_PAGE_DELAY_SECONDS
    ),
) -> HandednessResolver:
    """
    Load the cached MLB26 card catalog, refreshing it when needed,
    and construct one immutable handedness resolver for a request/run.
    """
    items = get_card_catalog(
        cache_path=cache_path,
        base_url=base_url,
        max_age_seconds=(
            max_age_seconds
        ),
        session=session,
        page_delay_seconds=(
            page_delay_seconds
        ),
    )

    if not items:
        raise ValueError(
            "MLBTS card catalog is empty."
        )

    return HandednessResolver(
        items
    )
