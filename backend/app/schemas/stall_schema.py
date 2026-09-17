from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StallCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    cuisine: Optional[str] = Field(default=None, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    image_url: Optional[str] = None
    owner_id: Optional[int] = None  # admins only


class StallUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    cuisine: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    image_url: Optional[str] = None
    is_open: Optional[bool] = None


class StallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    address: str
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    is_open: bool
    is_approved: bool = True
    created_at: datetime
    avg_rating: Optional[float] = None