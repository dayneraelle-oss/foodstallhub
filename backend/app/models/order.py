"""MongoDB document shapes for orders and reviews.

Unlike the SQLAlchemy models (users/stalls/menu stored in PostgreSQL),
orders and reviews are stored as JSON documents in MongoDB. These enums
and pydantic models describe the shapes repositories write and read.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


# Order statuses a customer may still cancel.
CANCELLABLE_STATUSES = {OrderStatus.pending, OrderStatus.confirmed}


class PaymentMethod(str, Enum):
    card = "card"
    upi = "upi"
    cod = "cod"
    wallet = "wallet"


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class OrderItemInDB(BaseModel):
    menu_item_id: int
    name: str
    price: float
    quantity: int


class OrderInDB(BaseModel):
    _id: str
    user_id: int
    stall_id: int
    items: List[OrderItemInDB]
    subtotal: float
    delivery_fee: float
    total: float
    address: Optional[str] = None
    note: Optional[str] = None
    status: OrderStatus = OrderStatus.pending
    payment_method: PaymentMethod
    payment_status: PaymentStatus = PaymentStatus.pending
    estimated_delivery_minutes: int = Field(default=0)
    created_at: str
    updated_at: str


class ReviewInDB(BaseModel):
    _id: str
    order_id: str
    user_id: int
    stall_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    created_at: str