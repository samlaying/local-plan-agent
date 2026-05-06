from __future__ import annotations

import abc
from typing import Any


class AbstractPOISearcher(abc.ABC):
    """Interface between retrieval logic and the underlying data source (mock or real API).

    Each concrete implementation must return lists of POISchema so that the
    caller (search_candidates / RetrievalNode) is agnostic of the data source.

    Methods accept and return Any at the base class level to avoid coupling
    this module to a specific schema import path.  Concrete subclasses and
    callers use the precise Pydantic types (POISchema, UserIntentSchema).
    """

    @abc.abstractmethod
    def search_activities(self, intent: Any) -> list[Any]:
        """Return activity candidates (POISchema) that match the given planning intent."""
        ...

    @abc.abstractmethod
    def search_restaurants(self, intent: Any) -> list[Any]:
        """Return restaurant candidates (POISchema) that match the given planning intent."""
        ...
