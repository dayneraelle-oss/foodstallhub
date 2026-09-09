from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentMethod, PaymentStatus


class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    stall_id: int
    items: List[OrderItemIn] = Field(min_length=1)
    address: Optional[str] = Field(default=None, max_length=500)
    note: Optional[str] = Field(default=None, max_length=500)
    payment_method: PaymentMethod = PaymentMethod.cod


class OrderItemOut(BaseModel):
    menu_item_id: int
    name: str
    price: float
    quantity: int

    @property
    def line_total(self) -> float:
        return round(self.price * self.quantity, 2)


class OrderOut(BaseModel):
    order_id: str
    user_id: int
    stall_id: int
    items: List[OrderItemOut]
    subtotal: float
    delivery_fee: float
    total: float
    address: Optional[str] = None
    note: Optional[str] = None
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    estimated_delivery_minutes: int
    created_at: str
    updated_at: str


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderCancelOut(BaseModel):
    order_id: str
    status: OrderStatus