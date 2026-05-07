from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from tools.poi.base import AbstractPOISearcher

if TYPE_CHECKING:
    from app.repositories.mock_poi_repository import MockPOIRepository
    from app.schemas.planning import POISchema, UserIntentSchema

logger = logging.getLogger(__name__)


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
