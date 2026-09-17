from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import (
    ROLE_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_VENDOR,
    get_current_user,
    require_roles,
)
from app.models.user import User
from app.repositories import mongo_repo
from app.repositories.postgres_repo import (
    create_stall,
    delete_stall,
    get_db,
    get_stall,
    get_user_by_id,
    list_stalls,
    update_stall,
)
from app.schemas.stall_schema import StallCreate, StallOut, StallUpdate
from app.utils.error_handler import AppError

router = APIRouter(prefix="/stalls", tags=["stalls"])


def _stall_out(stall) -> StallOut:
    out = StallOut.model_validate(stall)
    try:
        out.avg_rating = mongo_repo.average_rating_for_stall(stall.id)
    except Exception:
        out.avg_rating = None
    return out


def _ensure_can_manage_stall(user: User, stall) -> None:
    if user.role in (ROLE_ADMIN, ROLE_SUPER_ADMIN):
        return
    if user.role != ROLE_VENDOR or stall.owner_id != user.id:
        raise AppError(403, "You do not own this stall")


@router.get("", response_model=List[StallOut])
def list_all_stalls(
    city: Optional[str] = None,
    cuisine: Optional[str] = None,
    is_open: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[StallOut]:
    stalls = list_stalls(
        db,
        city=city,
        cuisine=cuisine,
        is_open=is_open,
        approved_only=True,
        skip=skip,
        limit=limit,
    )
    return [_stall_out(s) for s in stalls]


@router.get("/{stall_id}", response_model=StallOut)
def get_one_stall(stall_id: int, db: Session = Depends(get_db)) -> StallOut:
    stall = get_stall(db, stall_id)
    if stall is None or not stall.is_approved:
        raise AppError(404, "Stall not found")
    return _stall_out(stall)


@router.post("", response_model=StallOut, status_code=status.HTTP_201_CREATED)
def create_a_stall(
    payload: StallCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> StallOut:
    owner_id = payload.owner_id
    if user.role == ROLE_VENDOR:
        owner_id = user.id
    elif owner_id is None:
        owner_id = user.id

    if get_user_by_id(db, owner_id) is None:
        raise AppError(400, "Owner does not exist")

    stall = create_stall(
        db,
        owner_id=owner_id,
        name=payload.name,
        description=payload.description,
        cuisine=payload.cuisine,
        address=payload.address,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        image_url=payload.image_url,
        is_approved=user.role != ROLE_VENDOR,
    )
    return _stall_out(stall)


@router.put("/{stall_id}", response_model=StallOut)
def update_a_stall(
    stall_id: int,
    payload: StallUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StallOut:
    stall = get_stall(db, stall_id)
    if stall is None:
        raise AppError(404, "Stall not found")
    _ensure_can_manage_stall(user, stall)

    fields = payload.model_dump(exclude_unset=True)
    updated = update_stall(db, stall_id, fields)
    return _stall_out(updated)


@router.delete("/{stall_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_stall(
    stall_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    stall = get_stall(db, stall_id)
    if stall is None:
        raise AppError(404, "Stall not found")
    _ensure_can_manage_stall(user, stall)
    delete_stall(db, stall_id)