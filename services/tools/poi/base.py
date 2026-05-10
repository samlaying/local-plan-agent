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

    def search_with_strategy(
        self,
        intent: Any,
        activity_keywords: str,
        activity_types: str,
        restaurant_keywords: str,
        restaurant_types: str,
    ) -> tuple[list[Any], list[Any]]:
        """搜索指定策略的活动和餐厅候选。

        默认实现忽略策略参数，直接调用 search_activities / search_restaurants。
        AmapSearcher 会覆写此方法，利用 keywords / types 实际搜索不同风格的 POI。

        Args:
            intent:               UserIntentSchema，包含城市、距离、场景等约束。
            activity_keywords:    活动搜索关键词（高德 place/around keywords 参数）。
            activity_types:       活动 POI 类型代码（高德 types 参数）。
            restaurant_keywords:  餐厅搜索关键词。
            restaurant_types:     餐厅 POI 类型代码（通常固定为"050000"）。

        Returns:
            (activities, restaurants) — 两个 POISchema 列表。
        """
        return self.search_activities(intent), self.search_restaurants(intent)

    def search_activities_around(
        self,
        lat: float,
        lng: float,
        keywords: str,
        radius_m: int,
        intent: Any,
    ) -> list[Any]:
        """Search activity POIs around an arbitrary coordinate pair.

        Subclasses that support coordinate-based search (e.g., AmapSearcher)
        should override this.  Default implementation returns an empty list.

        Args:
            lat:       Latitude of the search center.
            lng:       Longitude of the search center.
            keywords:  Search keywords (pipe-separated).
            radius_m:  Search radius in meters.
            intent:    UserIntentSchema with scenario / city / distance constraints.

        Returns:
            list of POISchema with distance_km relative to (lat, lng).
        """
        return []

    def search_restaurants_around(
        self,
        lat: float,
        lng: float,
        keywords: str,
        radius_m: int,
        intent: Any,
    ) -> list[Any]:
        """Search restaurant POIs around an arbitrary coordinate pair.

        Subclasses that support coordinate-based search (e.g., AmapSearcher)
        should override this.  Default implementation returns an empty list.

        Args:
            lat:       Latitude of the search center.
            lng:       Longitude of the search center.
            keywords:  Search keywords (pipe-separated).
            radius_m:  Search radius in meters.
            intent:    UserIntentSchema with scenario / city / distance constraints.

        Returns:
            list of POISchema with distance_km relative to (lat, lng).
        """
        return []

    def geocode(self, address: str, city: str) -> tuple[float, float]:
        """Geocode an address string to (lat, lng).

        Subclasses with real geocoding capability (e.g., AmapSearcher)
        should override this.  Default implementation returns a fallback
        coordinate for Shanghai People's Square.

        Returns:
            (lat, lng) tuple.
        """
        return (31.2304, 121.4737)
