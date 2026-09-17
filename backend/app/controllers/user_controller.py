from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import ROLE_ADMIN, get_current_user, require_roles
from app.models.user import User
from app.repositories.postgres_repo import get_db, list_users, update_user
from app.schemas.user_schema import UserOut, UserUpdate
from app.utils.error_handler import AppError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    updated = update_user(
        db,
        current_user.id,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    if updated is None:
        raise AppError(404, "User not found")
    return UserOut.model_validate(updated)


@router.get("", response_model=List[UserOut])
def list_all_users(
    role: Optional[List[str]] = Query(default=None, description="Filter by role(s); repeat for multiple"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> List[UserOut]:
    return [UserOut.model_validate(u) for u in list_users(db, skip=skip, limit=limit, roles=role)]


@router.get("/customers", response_model=List[UserOut])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> List[UserOut]:
    return [UserOut.model_validate(u) for u in list_users(db, skip=skip, limit=limit, roles=["customer"])]


@router.get("/vendors", response_model=List[UserOut])
def list_vendors(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> List[UserOut]:
    return [UserOut.model_validate(u) for u in list_users(db, skip=skip, limit=limit, roles=["vendor"])]