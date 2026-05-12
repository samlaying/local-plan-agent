from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from tools.poi.base import AbstractPOISearcher

if TYPE_CHECKING:
    from app.repositories.mock_poi_repository import MockPOIRepository
    from app.schemas.planning import POISchema, UserIntentSchema

logger = logging.getLogger(__name__)

# Fallback geocode coordinate when mock mode cannot resolve the origin.
# Shanghai People's Square is used as a neutral default.
_FALLBACK_LAT = 31.2304
_FALLBACK_LNG = 121.4737


class MockPOISearcher(AbstractPOISearcher):
    """Searcher backed by local JSON fixture files via MockPOIRepository.

    Encapsulates the scenario + city filtering that was previously inlined
    inside search_candidates() in activity_workflow.py.

    The repository is injected by the orchestrator (activity_workflow.py) so
    that this class does not import ``app.*`` at module load time — keeping
    tools/poi importable from any working directory.
    """

    def __init__(self, repository: MockPOIRepository) -> None:
        self._repo = repository

    def search_activities(self, intent: Any) -> list[Any]:
        results: list[POISchema] = [
            poi
            for poi in self._repo.list_activities()
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        ]
        logger.debug(
            "MockPOISearcher.search_activities: scenario=%s city=%s → %d results",
            intent.scenario,
            intent.city,
            len(results),
        )
        return results

    def search_activities_around(
        self,
        lat: float,
        lng: float,
        keywords: str,
        radius_m: int,
        intent: Any,
    ) -> list[Any]:
        """Coordinate-based activity search — returns mock activities filtered by scenario/city.

        Mock activities do not have meaningful coordinate data, so the lat/lng/radius
        parameters are used for logging only.  The returned list is scenario+city filtered
        (same as ``search_activities``), maintaining backward compatibility.
        """
        results: list[POISchema] = [
            poi
            for poi in self._repo.list_activities()
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        ]
        logger.debug(
            "MockPOISearcher.search_activities_around: "
            "lat=%.4f lng=%.4f radius=%dm → %d results (mock: scenario/city filter only)",
            lat, lng, radius_m, len(results),
        )
        return results

    def search_restaurants_around(
        self,
        lat: float,
        lng: float,
        keywords: str,
        radius_m: int,
        intent: Any,
    ) -> list[Any]:
        """Coordinate-based restaurant search — returns mock restaurants filtered by scenario/city."""
        results: list[POISchema] = [
            poi
            for poi in self._repo.list_restaurants()
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        ]
        logger.debug(
            "MockPOISearcher.search_restaurants_around: "
            "lat=%.4f lng=%.4f radius=%dm → %d results (mock: scenario/city filter only)",
            lat, lng, radius_m, len(results),
        )
        return results

    def geocode(self, address: str, city: str) -> tuple[float, float]:
        """Mock geocode — returns hardcoded fallback coordinates."""
        logger.debug(
            "MockPOISearcher.geocode: %r (%s) → (%f, %f) (hardcoded fallback)",
            address, city, _FALLBACK_LAT, _FALLBACK_LNG,
        )
        return (_FALLBACK_LAT, _FALLBACK_LNG)

    def search_restaurants(self, intent: Any) -> list[Any]:
        results: list[POISchema] = [
            poi
            for poi in self._repo.list_restaurants()
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        ]
        logger.debug(
            "MockPOISearcher.search_restaurants: scenario=%s city=%s → %d results",
            intent.scenario,
            intent.city,
            len(results),
        )
        return results
