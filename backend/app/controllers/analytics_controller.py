from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import ROLE_ADMIN, ROLE_VENDOR, require_roles
from app.models.menu import MenuItem
from app.models.stall import Stall
from app.models.user import User
from app.repositories import mongo_repo
from app.repositories.postgres_repo import (
    count_rows,
    get_db,
    get_stall,
)
from app.utils.error_handler import AppError

router = APIRouter(prefix="/analytics", tags=["analytics"])


class TopItem(BaseModel):
    name: str
    quantity: int
    revenue: float


class StallSummary(BaseModel):
    stall_id: int
    stall_name: str
    orders_count: int
    revenue: float
    cancelled_count: int
    average_rating: Optional[float] = None
    reviews_count: int
    top_items: List[TopItem]


class PlatformOverview(BaseModel):
    users_count: int
    stalls_count: int
    menu_items_count: int
    orders_count: int


@router.get("/stalls/{stall_id}/summary", response_model=StallSummary)
def stall_summary(
    stall_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> StallSummary:
    stall = get_stall(db, stall_id)
    if stall is None:
        raise AppError(404, "Stall not found")
    if user.role == ROLE_VENDOR and stall.owner_id != user.id:
        raise AppError(403, "You do not own this stall")

    stats = mongo_repo.stall_stats(stall_id)
    return StallSummary(
        stall_id=stall.id,
        stall_name=stall.name,
        orders_count=stats["orders_count"],
        revenue=stats["revenue"],
        cancelled_count=stats["cancelled_count"],
        average_rating=mongo_repo.average_rating_for_stall(stall_id),
        reviews_count=mongo_repo.count_reviews_for_stall(stall_id),
        top_items=[TopItem(**item) for item in stats["top_items"]],
    )


@router.get("/overview", response_model=PlatformOverview)
def platform_overview(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> PlatformOverview:
    return PlatformOverview(
        users_count=count_rows(db, User),
        stalls_count=count_rows(db, Stall),
        menu_items_count=count_rows(db, MenuItem),
        orders_count=mongo_repo.count_orders(),
    )