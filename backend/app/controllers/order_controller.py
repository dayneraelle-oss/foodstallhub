import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import (
    ROLE_ADMIN,
    ROLE_VENDOR,
    get_current_user,
    require_roles,
)
from app.models.order import (
    CANCELLABLE_STATUSES,
    OrderStatus,
)
from app.models.user import User
from app.repositories import mongo_repo
from app.repositories.postgres_repo import (
    get_db,
    get_menu_item,
    get_stall,
    list_stalls,
)
from app.schemas.order_schema import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import delivery_service, payment_service
from app.utils.error_handler import AppError

router = APIRouter(prefix="/orders", tags=["orders"])

# Allowed forward transitions per current status.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending: {OrderStatus.confirmed, OrderStatus.cancelled},
    OrderStatus.confirmed: {OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.preparing: {OrderStatus.out_for_delivery},
    OrderStatus.out_for_delivery: {OrderStatus.delivered},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}


def _order_to_out(document: dict) -> OrderOut:
    return OrderOut(
        order_id=document["_id"],
        user_id=document["user_id"],
        stall_id=document["stall_id"],
        items=document["items"],
        subtotal=document["subtotal"],
        delivery_fee=document["delivery_fee"],
        total=document["total"],
        address=document.get("address"),
        note=document.get("note"),
        status=document["status"],
        payment_method=document["payment_method"],
        payment_status=document["payment_status"],
        estimated_delivery_minutes=document.get("estimated_delivery_minutes", 0),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _can_view_order(user: User, document: dict, db: Session) -> bool:
    if user.role == ROLE_ADMIN:
        return True
    if document["user_id"] == user.id:
        return True
    stall = get_stall(db, document["stall_id"])
    return user.role == ROLE_VENDOR and stall is not None and stall.owner_id == user.id


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_an_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
) -> OrderOut:
    stall = get_stall(db, payload.stall_id)
    if stall is None:
        raise AppError(404, "Stall not found")
    if not stall.is_open:
        raise AppError(400, "This stall is currently closed")

    # Resolve and validate every menu item against the stall's catalogue.
    resolved_items = []
    subtotal = Decimal("0.00")
    for line in payload.items:
        item = get_menu_item(db, line.menu_item_id)
        if item is None or item.stall_id != payload.stall_id:
            raise AppError(400, f"Menu item {line.menu_item_id} does not belong to this stall")
        if not item.is_available:
            raise AppError(400, f"Menu item '{item.name}' is unavailable")
        unit_price = Decimal(str(item.price))
        resolved_items.append(
            {
                "menu_item_id": item.id,
                "name": item.name,
                "price": float(unit_price),
                "quantity": line.quantity,
            }
        )
        subtotal += unit_price * line.quantity

    delivery_fee = delivery_service.calculate_delivery_fee()
    total = subtotal + Decimal(str(delivery_fee))
    payment = payment_service.initiate_payment(
        payload.payment_method,
        float(total),
        user_id=customer.id,
    )
    estimated_minutes = delivery_service.estimate_delivery_minutes(stall.city)

    now = mongo_repo.utc_now_iso()
    document = {
        "_id": uuid.uuid4().hex,
        "user_id": customer.id,
        "stall_id": payload.stall_id,
        "items": resolved_items,
        "subtotal": float(subtotal),
        "delivery_fee": delivery_fee,
        "total": float(total),
        "address": payload.address,
        "note": payload.note,
        "status": OrderStatus.pending.value,
        "payment_method": payload.payment_method.value,
        "payment_status": payment.payment_status.value,
        "estimated_delivery_minutes": estimated_minutes,
        "created_at": now,
        "updated_at": now,
    }
    order_id = mongo_repo.create_order(document)
    return _order_to_out(document)


@router.get("/my", response_model=List[OrderOut])
def list_my_orders(
    skip: int = 0,
    limit: int = 50,
    _customer: User = Depends(get_current_user),
) -> List[OrderOut]:
    documents = mongo_repo.list_orders_by_user(_customer.id, skip=skip, limit=limit)
    return [_order_to_out(d) for d in documents]


@router.get("/vendor", response_model=List[OrderOut])
def list_vendor_orders(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    vendor: User = Depends(require_roles(ROLE_VENDOR)),
) -> List[OrderOut]:
    stalls = list_stalls(db, is_open=None, skip=0, limit=1000)
    stall_ids = [s.id for s in stalls if s.owner_id == vendor.id]
    if not stall_ids:
        return []
    documents = mongo_repo.list_orders_by_stalls(stall_ids, skip=skip, limit=limit)
    return [_order_to_out(d) for d in documents]


@router.get("/{order_id}", response_model=OrderOut)
def get_an_order(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    document = mongo_repo.get_order_by_id(order_id)
    if document is None:
        raise AppError(404, "Order not found")
    if not _can_view_order(user, document, db):
        raise AppError(403, "You cannot view this order")
    return _order_to_out(document)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status_endpoint(
    order_id: str,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> OrderOut:
    document = mongo_repo.get_order_by_id(order_id)
    if document is None:
        raise AppError(404, "Order not found")

    stall = get_stall(db, document["stall_id"])
    if user.role == ROLE_VENDOR:
        if stall is None or stall.owner_id != user.id:
            raise AppError(403, "You do not own this stall")

    current = OrderStatus(document["status"])
    target = payload.status
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise AppError(400, f"Cannot move order from '{current.value}' to '{target.value}'")

    updated = mongo_repo.update_order_status(order_id, target.value)
    if updated is None:
        raise AppError(404, "Order not found")
    return _order_to_out(updated)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_an_order(
    order_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
) -> OrderOut:
    document = mongo_repo.get_order_by_id(order_id)
    if document is None:
        raise AppError(404, "Order not found")
    if document["user_id"] != customer.id:
        raise AppError(403, "You cannot cancel this order")

    current = OrderStatus(document["status"])
    if current not in CANCELLABLE_STATUSES:
        raise AppError(400, f"Order in '{current.value}' status can no longer be cancelled")

    updated = mongo_repo.cancel_order(order_id)
    if updated is None:
        raise AppError(404, "Order not found")
    return _order_to_out(updated)