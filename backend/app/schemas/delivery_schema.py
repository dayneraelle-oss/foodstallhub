from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LocationPointIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class LocationPointOut(BaseModel):
    lat: float
    lng: float
    timestamp: str


class DeliveryTrackingOut(BaseModel):
    order_id: str
    points: List[LocationPointOut]
    distance_km: Optional[float] = None
