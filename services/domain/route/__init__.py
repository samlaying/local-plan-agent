import math

EARTH_RADIUS_KM = 6371.0
URBAN_SPEED_KMPM = 1 / 3.0  # ~3 min per km → 0.333... km/min


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two geographic coordinates."""
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def to_travel_minutes(km: float) -> int:
    """Estimated city driving minutes for a given distance in km."""
    return max(1, round(km / URBAN_SPEED_KMPM))
