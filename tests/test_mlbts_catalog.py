import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.mlbts_catalog import (
    catalog_cache_is_fresh,
    fetch_card_catalog,
    get_card_catalog,
    get_handedness_resolver,
    load_cached_catalog,
    write_catalog_cache,
)


class FakeResponse:
    def __init__(
        self,
        payload,
    ):
        self._payload = payload

    def raise_for_status(
        self,
    ):
        return None

    def json(
        self,
    ):
        return self._payload


class FakeSession:
    def __init__(
        self,
        pages,
    ):
        self.pages = pages
        self.calls = []

    def get(
        self,
        url,
        *,
        params,
        timeout,
    ):
        self.calls.append(
            {
                "url": url,
                "params": dict(
                    params
                ),
                "timeout": timeout,
            }
        )

        page = params["page"]

        return FakeResponse(
            self.pages[page]
        )


class CatalogCacheTests(
    unittest.TestCase
):
    def test_cache_round_trip(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "catalog.json"
            )

            items = [
                {
                    "name": (
                        "Test Batter"
                    ),
                    "bat_hand": "L",
                }
            ]

            write_catalog_cache(
                path,
                items,
            )

            self.assertEqual(
                load_cached_catalog(
                    path
                ),
                items,
            )

            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertIn(
                "fetched_at",
                payload,
            )

    def test_fresh_cache_avoids_network(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "catalog.json"
            )

            items = [
                {
                    "name": "Cached",
                }
            ]

            write_catalog_cache(
                path,
                items,
            )

            session = FakeSession(
                {}
            )

            result = get_card_catalog(
                cache_path=path,
                session=session,
                max_age_seconds=3600,
            )

            self.assertEqual(
                result,
                items,
            )

            self.assertEqual(
                session.calls,
                [],
            )

    def test_catalog_fetches_all_pages(
        self,
    ):
        session = FakeSession(
            {
                1: {
                    "total_pages": 3,
                    "items": [
                        {
                            "name": "One",
                        }
                    ],
                },
                2: {
                    "total_pages": 3,
                    "items": [
                        {
                            "name": "Two",
                        }
                    ],
                },
                3: {
                    "total_pages": 3,
                    "items": [
                        {
                            "name": "Three",
                        }
                    ],
                },
            }
        )

        result = fetch_card_catalog(
            base_url=(
                "https://example.test"
            ),
            session=session,
            page_delay_seconds=0,
        )

        self.assertEqual(
            [
                item["name"]
                for item in result
            ],
            [
                "One",
                "Two",
                "Three",
            ],
        )

        self.assertEqual(
            [
                call["params"][
                    "page"
                ]
                for call in (
                    session.calls
                )
            ],
            [
                1,
                2,
                3,
            ],
        )

    def test_stale_cache_is_used_when_refresh_fails(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "catalog.json"
            )

            items = [
                {
                    "name": (
                        "Stale Card"
                    ),
                }
            ]

            write_catalog_cache(
                path,
                items,
            )

            with patch(
                (
                    "src.mlbts_catalog."
                    "catalog_cache_is_fresh"
                ),
                return_value=False,
            ):
                with patch(
                    (
                        "src.mlbts_catalog."
                        "fetch_card_catalog"
                    ),
                    side_effect=(
                        RuntimeError(
                            "offline"
                        )
                    ),
                ):
                    result = (
                        get_card_catalog(
                            cache_path=path
                        )
                    )

            self.assertEqual(
                result,
                items,
            )

    def test_refresh_writes_new_cache(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "catalog.json"
            )

            new_items = [
                {
                    "name": "Fresh",
                }
            ]

            with patch(
                (
                    "src.mlbts_catalog."
                    "fetch_card_catalog"
                ),
                return_value=(
                    new_items
                ),
            ):
                result = get_card_catalog(
                    cache_path=path,
                )

            self.assertEqual(
                result,
                new_items,
            )

            self.assertEqual(
                load_cached_catalog(
                    path
                ),
                new_items,
            )

    def test_missing_cache_and_failed_refresh_raises(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "catalog.json"
            )

            with patch(
                (
                    "src.mlbts_catalog."
                    "fetch_card_catalog"
                ),
                side_effect=(
                    RuntimeError(
                        "offline"
                    )
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "offline",
                ):
                    get_card_catalog(
                        cache_path=path
                    )

    def test_catalog_can_construct_handedness_resolver(
        self,
    ):
        items = [
            {
                "name": "Test Batter",
                "is_hitter": True,
                "two_way": False,
                "bat_hand": "L",
                "throw_hand": "R",
                "display_position": "RF",
                "display_secondary_positions": "",
            }
        ]

        with patch(
            (
                "src.mlbts_catalog."
                "get_card_catalog"
            ),
            return_value=items,
        ):
            resolver = (
                get_handedness_resolver(
                    cache_path=Path(
                        "unused.json"
                    )
                )
            )

        result = (
            resolver.resolve_batter(
                "Test Batter",
                position="RF",
            )
        )

        self.assertEqual(
            result["status"],
            "resolved",
        )

        self.assertEqual(
            result["hand"],
            "L",
        )

    def test_cache_freshness_requires_valid_cache(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "catalog.json"
            )

            path.write_text(
                "not json",
                encoding="utf-8",
            )

            self.assertFalse(
                catalog_cache_is_fresh(
                    path,
                    3600,
                )
            )


if __name__ == "__main__":
    unittest.main()
