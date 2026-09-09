from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import ROLE_ADMIN, ROLE_VENDOR, get_current_user, require_roles
from app.models.user import User
from app.repositories import mongo_repo
from app.repositories.postgres_repo import get_db, get_stall
from app.schemas.delivery_schema import (
    DeliveryTrackingOut,
    LocationPointIn,
    LocationPointOut,
)
from app.services import delivery_service
from app.utils.error_handler import AppError

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


def _can_view_delivery(user: User, order_id: str, db: Session) -> None:
    document = mongo_repo.get_order_by_id(order_id)
    if document is None:
        raise AppError(404, "Order not found")
    if user.role == ROLE_ADMIN:
        return
    if document["user_id"] == user.id:
        return
    stall = get_stall(db, document["stall_id"])
    if user.role == ROLE_VENDOR and stall is not None and stall.owner_id == user.id:
        return
    raise AppError(403, "You cannot view this delivery")


@router.post(
    "/{order_id}/location",
    response_model=LocationPointOut,
    status_code=status.HTTP_201_CREATED,
)
def update_rider_location(
    order_id: str,
    payload: LocationPointIn,
    db: Session = Depends(get_db),
    vendor: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> LocationPointOut:
    _can_view_delivery(vendor, order_id, db)
    point = mongo_repo.upsert_rider_location(
        order_id, payload.lat, payload.lng
    )
    if point is None:
        raise AppError(404, "Order not found")
    return LocationPointOut(**point)


@router.get("/{order_id}/tracking", response_model=DeliveryTrackingOut)
def get_delivery_tracking(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeliveryTrackingOut:
    document = mongo_repo.get_order_by_id(order_id)
    if document is None:
        raise AppError(404, "Order not found")
    _can_view_delivery(user, order_id, db)

    points = mongo_repo.get_delivery_tracking(order_id) or []
    distance_km = None
    stale_geos = [p for p in points if "lat" in p and "lng" in p]
    if len(stale_geos) >= 2:
        distance_km = delivery_service.haversine_km(
            stale_geos[0]["lat"],
            stale_geos[0]["lng"],
            stale_geos[-1]["lat"],
            stale_geos[-1]["lng"],
        )

    return DeliveryTrackingOut(
        order_id=order_id,
        points=[LocationPointOut(**p) for p in points],
        distance_km=distance_km,
    )
