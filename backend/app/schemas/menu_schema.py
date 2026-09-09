from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: Optional[str] = Field(default=None, max_length=80)
    image_url: Optional[str] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category: Optional[str] = Field(default=None, max_length=80)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


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
    created_at: datetime