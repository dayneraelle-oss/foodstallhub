"""Delivery estimate & dispatch (business logic).

Stub implementation: estimates are rule-based. Swap in a routing engine
(Google Directions, OSRM) and a driver provider in production.
"""

import hashlib
import math
from typing import Optional

_BASE_MINUTES = 15
_PER_KM_MINUTES = 3.0
_DEFAULT_DISTANCE_KM = 5


def haversine_km(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """Great-circle distance in km between two coordinates."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    )
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def estimate_delivery_minutes(
    city: Optional[str] = None,
    distance_km: Optional[float] = None,
) -> int:
    """Estimate door-step delivery time given city/rough distance."""
    distance = distance_km if distance_km is not None else _DEFAULT_DISTANCE_KM
    minutes = _BASE_MINUTES + int(round(_PER_KM_MINUTES * distance))

    # Dense metro cities add ~fleet traffic overhead.
    traffic_buffer = 5 if city and city.lower() in {"bangalore", "mumbai", "delhi", "pune"} else 0
    return minutes + traffic_buffer


def calculate_delivery_fee(*, distance_km: Optional[float] = None) -> float:
    """Flat delivery fee based on distance (stub)."""
    distance = distance_km if distance_km is not None else _DEFAULT_DISTANCE_KM
    if distance <= 3:
        return 0.0
    return round(20.0 + (distance - 3) * 5.0, 2)


def assign_driver(stall_id: int) -> str:
    """Deterministically fake a driver assignment for a stall."""
    digest = hashlib.md5(f"stall-{stall_id}".encode("utf-8")).hexdigest()[:6]
    return f"DRV-{digest.upper()}"