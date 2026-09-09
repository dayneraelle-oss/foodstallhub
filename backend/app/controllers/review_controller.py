import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.models.order import OrderStatus
from app.models.user import User
from app.repositories import mongo_repo
from app.repositories.postgres_repo import get_db, get_stall
from app.schemas.review_schema import (
    ReviewCreate,
    ReviewListOut,
    ReviewOut,
)
from app.utils.error_handler import AppError

router = APIRouter(tags=["reviews"])


def _review_to_out(document: dict) -> ReviewOut:
    return ReviewOut(
        review_id=document["_id"],
        order_id=document["order_id"],
        user_id=document["user_id"],
        stall_id=document["stall_id"],
        rating=document["rating"],
        comment=document.get("comment"),
        created_at=document["created_at"],
    )


@router.get("/stalls/{stall_id}/reviews", response_model=ReviewListOut)
def list_stall_reviews(
    stall_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ReviewListOut:
    if get_stall(db, stall_id) is None:
        raise AppError(404, "Stall not found")

    documents = mongo_repo.list_reviews_by_stall(stall_id, skip=skip, limit=limit)
    return ReviewListOut(
        stall_id=stall_id,
        average_rating=mongo_repo.average_rating_for_stall(stall_id),
        total=mongo_repo.count_reviews_for_stall(stall_id),
        reviews=[_review_to_out(d) for d in documents],
    )


@router.post(
    "/stalls/{stall_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_stall_review(
    stall_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
) -> ReviewOut:
    if get_stall(db, stall_id) is None:
        raise AppError(404, "Stall not found")

    order = mongo_repo.get_order_by_id(payload.order_id)
    if order is None:
        raise AppError(404, "Order not found")
    if order["user_id"] != customer.id:
        raise AppError(403, "You can only review your own orders")
    if order["stall_id"] != stall_id:
        raise AppError(400, "This order does not belong to the given stall")
    if order["status"] != OrderStatus.delivered.value:
        raise AppError(400, "Only delivered orders can be reviewed")

    document = {
        "_id": uuid.uuid4().hex,
        "order_id": payload.order_id,
        "user_id": customer.id,
        "stall_id": stall_id,
        "rating": payload.rating,
        "comment": payload.comment,
        "created_at": mongo_repo.utc_now_iso(),
    }
    saved = mongo_repo.create_review(document)
    return _review_to_out(saved)


@router.get("/reviews/me", response_model=List[ReviewOut])
def my_reviews(
    customer: User = Depends(get_current_user),
) -> List[ReviewOut]:
    documents = mongo_repo.list_reviews_by_user(customer.id)
    return [_review_to_out(d) for d in documents]