from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: Optional[str] = Field(default=None, max_length=80)
    image_url: Optional[str] = None
    tags: Optional[str] = Field(default=None, max_length=255, description="Comma-separated tags like vegetarian, spicy, gluten-free")
    prep_time_minutes: Optional[int] = Field(default=None, ge=0, description="Preparation time in minutes")
    serving_size: Optional[str] = Field(default=None, max_length=80, description="Serving size like '1 plate', '2 pieces'")


class MenuItemBulkCreate(BaseModel):
    items: List[MenuItemCreate] = Field(min_length=1, max_length=100)


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category: Optional[str] = Field(default=None, max_length=80)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    tags: Optional[str] = Field(default=None, max_length=255)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    serving_size: Optional[str] = Field(default=None, max_length=80)


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stall_id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_available: bool
    tags: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    serving_size: Optional[str] = None
    created_at: datetime