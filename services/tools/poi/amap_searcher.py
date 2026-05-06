from __future__ import annotations

# AMap (高德地图) POI Searcher — skeleton only, not yet implemented.
#
# Required AMap REST APIs:
#   - /v3/geocode/geo   — geocode the user's origin address to lat/lng
#   - /v3/place/around  — search POIs within a radius of a lat/lng point
#
# Reference docs:
#   https://lbs.amap.com/api/webservice/guide/api/georegeo
#   https://lbs.amap.com/api/webservice/guide/api/search
#
# When implementing, consider using httpx (async-capable) for HTTP calls
# so the searcher can be made async later without changing the interface.

import logging
import os
from typing import Any

from tools.poi.base import AbstractPOISearcher

logger = logging.getLogger(__name__)


class AmapSearcher(AbstractPOISearcher):
    """POI searcher backed by the AMap (高德) REST API.

    Raises ValueError at construction time if AMAP_API_KEY is not set, so
    misconfiguration is caught early rather than at first search call.
    """

    def __init__(self) -> None:
        api_key = os.getenv("AMAP_API_KEY", "")
        if not api_key:
            raise ValueError(
                "AMAP_API_KEY is not set — TODO: fill in key before using AmapSearcher"
            )
        self._api_key = api_key

    def search_activities(self, intent: Any) -> list[Any]:
        raise NotImplementedError(
            "AmapSearcher.search_activities() is not yet implemented. "
            "Set USE_MOCK_POI=true to use mock data, or implement this method."
        )

    def search_restaurants(self, intent: Any) -> list[Any]:
        raise NotImplementedError(
            "AmapSearcher.search_restaurants() is not yet implemented. "
            "Set USE_MOCK_POI=true to use mock data, or implement this method."
        )
