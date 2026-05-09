from __future__ import annotations

# AMap (高德地图) POI Searcher — real implementation.
#
# Required AMap REST APIs:
#   - /v3/geocode/geo   — geocode the user's origin address to lat/lng
#   - /v3/place/around  — search POIs within a radius of a lat/lng point
#
# Reference docs:
#   https://lbs.amap.com/api/webservice/guide/api/georegeo
#   https://lbs.amap.com/api/webservice/guide/api/search

import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Any

from app.schemas.planning import (
    AudienceFitSchema,
    BusinessHoursSchema,
    LocationSchema,
    POISchema,
    QueueInfoSchema,
    UserIntentSchema,
)
from tools.poi.base import AbstractPOISearcher

logger = logging.getLogger(__name__)

_AMAP_RESTAURANT_TYPES = "050000"  # 餐饮服务

# 活动 POI 类型白名单 — LLM 不再介入类型选择，此处硬编码确保只返回适合游玩的场所。
# 110000 = 风景名胜（公园、景点、动物园、海洋馆、广场）
# 080000 = 体育休闲服务（运动场馆、KTV、影院、度假村、游乐场、采摘园）
# 140100~140900 = 博物馆、展览馆、美术馆、图书馆、科技馆、天文馆、文化宫、档案馆、文艺团体
# 061000 = 特色商业街
# 060100 = 商场/购物中心
_ACTIVITY_TYPE_WHITELIST = "110000|080000|140100|140200|140300|140400|140500|140600|140700|140800|140900|061000|060100"

_KNOWN_SCENARIOS = ["family_weight_loss_child5", "friends_4_mixed_gender"]


class AmapSearcher(AbstractPOISearcher):
    """POI searcher backed by the AMap (高德地图) Web Service REST API.

    Reads AMAP_API_KEY from environment at construction time; raises ValueError
    immediately if the key is missing so misconfiguration is caught early.

    AMAP_API_BASE_URL defaults to https://restapi.amap.com and can be
    overridden for testing.
    """

    def __init__(self) -> None:
        api_key = os.getenv("AMAP_API_KEY", "")
        if not api_key:
            raise ValueError(
                "AMAP_API_KEY is not set. "
                "Set USE_MOCK_POI=true to use mock data, or provide a valid key."
            )
        self._api_key = api_key
        self._base_url = os.getenv("AMAP_API_BASE_URL", "https://restapi.amap.com").rstrip("/")
        # Simple geocode cache: (origin, city) -> "lng,lat"
        self._geocode_cache: dict[tuple[str, str], str] = {}

    # ------------------------------------------------------------------
    # AbstractPOISearcher interface
    # ------------------------------------------------------------------

    def search_activities(self, intent: UserIntentSchema) -> list[POISchema]:
        """Return activity POIs near the intent origin, mapped to POISchema."""
        location = self._geocode(intent.origin, intent.city)
        keywords = "亲子活动|休闲娱乐|景点"
        types = _ACTIVITY_TYPE_WHITELIST
        logger.info("AMap activity search: types=%s, keywords=%s", types, keywords)
        raw_pois = self._search_around(
            location=location,
            keywords=keywords,
            types=types,
            radius_m=int(intent.max_distance_km * 1000),
        )
        result: list[POISchema] = []
        for poi in raw_pois:
            try:
                result.append(self._map_to_schema(poi, intent, is_restaurant=False))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Skipping activity POI %s due to mapping error: %s",
                    poi.get("id"), exc,
                )
        return result

    def search_restaurants(self, intent: UserIntentSchema) -> list[POISchema]:
        """Return restaurant POIs near the intent origin, mapped to POISchema."""
        location = self._geocode(intent.origin, intent.city)
        raw_pois = self._search_around(
            location=location,
            keywords="餐厅|餐饮",
            types=_AMAP_RESTAURANT_TYPES,
            radius_m=int(intent.max_distance_km * 1000),
        )
        result: list[POISchema] = []
        for poi in raw_pois:
            try:
                result.append(self._map_to_schema(poi, intent, is_restaurant=True))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Skipping restaurant POI %s due to mapping error: %s",
                    poi.get("id"), exc,
                )
        return result

    def search_with_strategy(
        self,
        intent: UserIntentSchema,
        activity_keywords: str,
        activity_types: str,
        restaurant_keywords: str,
        restaurant_types: str,
    ) -> tuple[list[POISchema], list[POISchema]]:
        """搜索指定策略的活动和餐厅候选（覆写基类默认实现）。

        使用传入的 keywords / types 调用 AMap place/around，实现不同策略搜到
        真正不同的 POI 候选集。异常处理与 search_activities / search_restaurants 保持一致。

        注意：activity_types 参数被忽略，始终使用 _ACTIVITY_TYPE_WHITELIST 硬编码白名单。
        """
        location = self._geocode(intent.origin, intent.city)
        radius_m = int(intent.max_distance_km * 1000)

        # 活动搜索 — 使用硬编码白名单，忽略传入的 activity_types
        actual_activity_types = _ACTIVITY_TYPE_WHITELIST
        logger.info(
            "AMap activity search (strategy): types=%s, keywords=%s",
            actual_activity_types, activity_keywords,
        )
        raw_activities = self._search_around(
            location=location,
            keywords=activity_keywords,
            types=actual_activity_types,
            radius_m=radius_m,
        )
        activities: list[POISchema] = []
        for poi in raw_activities:
            try:
                activities.append(self._map_to_schema(poi, intent, is_restaurant=False))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "search_with_strategy: skipping activity POI %s: %s",
                    poi.get("id"), exc,
                )

        # 餐厅搜索
        logger.info(
            "AMap restaurant search (strategy): types=%s, keywords=%s",
            restaurant_types, restaurant_keywords,
        )
        raw_restaurants = self._search_around(
            location=location,
            keywords=restaurant_keywords,
            types=restaurant_types,
            radius_m=radius_m,
        )
        restaurants: list[POISchema] = []
        for poi in raw_restaurants:
            try:
                restaurants.append(self._map_to_schema(poi, intent, is_restaurant=True))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "search_with_strategy: skipping restaurant POI %s: %s",
                    poi.get("id"), exc,
                )

        return activities, restaurants

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _geocode(self, address: str, city: str) -> str:
        """Convert an address string to "lng,lat". Results are cached per instance."""
        cache_key = (address, city)
        if cache_key in self._geocode_cache:
            return self._geocode_cache[cache_key]

        params = {
            "address": address,
            "city": city,
            "key": self._api_key,
            "output": "JSON",
        }
        url = f"{self._base_url}/v3/geocode/geo?" + urllib.parse.urlencode(params)
        data = self._http_get(url)

        if str(data.get("status")) != "1" or not data.get("geocodes"):
            raise ValueError(f"无法解析出发地: {address!r}（AMap 返回: {data.get('info')}）")

        location: str = data["geocodes"][0]["location"]
        self._geocode_cache[cache_key] = location
        logger.debug("Geocoded %r (%s) → %s", address, city, location)
        return location

    def _search_around(
        self,
        location: str,
        keywords: str,
        types: str,
        radius_m: int,
    ) -> list[dict[str, Any]]:
        """Call AMap /v3/place/around and return the raw POI list.

        Retries up to 3 times with incremental delays (0.5s / 1.0s / 1.5s) when
        the API returns CUQPS_HAS_EXCEEDED_THE_LIMIT. Other non-1 statuses are
        logged as warnings and return an empty list immediately.

        This method is synchronous and runs inside run_in_executor, so
        time.sleep() is safe here.
        """
        _QPS_ERROR = "CUQPS_HAS_EXCEEDED_THE_LIMIT"
        _RETRY_DELAYS = [0.5, 1.0, 1.5]
        _MAX_ATTEMPTS = len(_RETRY_DELAYS) + 1  # 1 initial + 3 retries

        params = {
            "location": location,
            "keywords": keywords,
            "types": types,
            "radius": radius_m,
            "offset": 20,
            "page": 1,
            "extensions": "all",
            "key": self._api_key,
            "output": "JSON",
        }
        url = f"{self._base_url}/v3/place/around?" + urllib.parse.urlencode(params)

        for attempt in range(_MAX_ATTEMPTS):
            data = self._http_get(url)

            if str(data.get("status")) == "1":
                return data.get("pois") or []

            info = data.get("info", "")
            if info == _QPS_ERROR and attempt < _MAX_ATTEMPTS - 1:
                delay = _RETRY_DELAYS[attempt]
                logger.warning(
                    "AMap place/around QPS limit hit (attempt %d/%d), retrying in %.1fs",
                    attempt + 1, _MAX_ATTEMPTS, delay,
                )
                time.sleep(delay)
                continue

            # Non-QPS error or exhausted retries — log and give up
            logger.warning(
                "AMap place/around returned status=%s info=%s (attempt %d/%d)",
                data.get("status"), info, attempt + 1, _MAX_ATTEMPTS,
            )
            return []

        return []  # unreachable, satisfies type checker

    @staticmethod
    def _http_get(url: str) -> dict[str, Any]:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            return json.loads(resp.read())

    # ------------------------------------------------------------------
    # AMap → POISchema mapping
    # ------------------------------------------------------------------

    def _map_to_schema(
        self,
        poi: dict[str, Any],
        intent: UserIntentSchema,
        *,
        is_restaurant: bool,
    ) -> POISchema:
        amap_id: str = poi["id"]
        name: str = poi.get("name", "")
        poi_type: str = poi.get("type", "")
        address: str = poi.get("address") or ""

        # Location: AMap returns "lng,lat"
        location_str: str = poi.get("location", "0,0")
        lng_str, lat_str = location_str.split(",", 1)
        location = LocationSchema(lat=float(lat_str), lng=float(lng_str))

        # Distance and estimated travel time
        distance_km = int(poi.get("distance", 0)) / 1000.0
        travel_minutes = max(1, int(distance_km / 0.4))  # ~24 km/h walking

        biz_ext: dict[str, Any] = poi.get("biz_ext") or {}

        # Rating (0–5)
        try:
            rating = min(float(biz_ext.get("rating") or 0), 5.0)
        except (TypeError, ValueError):
            rating = 0.0

        # Price
        try:
            price_per_person = int(float(biz_ext.get("cost") or 0))
        except (TypeError, ValueError):
            price_per_person = 0
        price_level = _price_level(price_per_person)

        # Business hours: best-effort parse of AMap's open_time string
        business_hours = _parse_business_hours(biz_ext.get("open_time") or "")

        # Category: scenario-driven for activities, fixed for restaurants
        if is_restaurant:
            category = "restaurant"
        elif intent.scenario == "family_weight_loss_child5":
            category = "family_activity"
        else:
            category = "friends_activity"

        # Subcategory and tags from AMap type string ("风景名胜;公园广场;公园" → "公园")
        type_parts = [p.strip() for p in poi_type.split(";") if p.strip()]
        subcategory = type_parts[-1] if type_parts else poi_type
        tags = [subcategory] if subcategory else []

        # AudienceFit: AMap provides no scoring data — use neutral defaults
        audience_fit = AudienceFitSchema(
            family=80,
            child_age_5=80,
            weight_loss_friendly=80,
            friends_group=80,
            mixed_gender_group=80,
        )

        queue = QueueInfoSchema(wait_minutes=0, level="none")

        return POISchema(
            id=f"amap_{amap_id}",
            amap_id=amap_id,
            provider="amap",
            name=name,
            category=category,  # type: ignore[arg-type]
            subcategory=subcategory,
            address=address,
            city=intent.city,
            distance_km=distance_km,
            travel_minutes=travel_minutes,
            price_per_person=price_per_person,
            price_level=price_level,  # type: ignore[arg-type]
            rating=rating,
            audience_fit=audience_fit,
            business_hours=business_hours,
            reservable=False,
            queue=queue,
            recommended_duration_minutes=60 if is_restaurant else 120,
            tags=tags,
            suitable_scenarios=list(_KNOWN_SCENARIOS),  # type: ignore[arg-type]
            reasons=[],
            cautions=[],
            location=location,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _price_level(price_per_person: int) -> str:
    if price_per_person <= 50:
        return "low"
    if price_per_person <= 150:
        return "medium"
    return "high"


def _parse_business_hours(open_time: str) -> BusinessHoursSchema:
    """Best-effort parse AMap open_time string (e.g. "08:00-22:00" or "周一至周日 09:00-21:00").

    Falls back to wide defaults when parsing fails.
    """
    if open_time:
        match = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", open_time)
        if match:
            return BusinessHoursSchema(open=match.group(1), close=match.group(2), note=open_time)
    return BusinessHoursSchema(open="09:00", close="22:00")
