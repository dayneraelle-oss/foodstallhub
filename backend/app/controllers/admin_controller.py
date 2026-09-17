from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import ROLE_ADMIN, require_roles
from app.models.user import User
from app.repositories.postgres_repo import (
    delete_user,
    get_db,
    list_users,
    update_user,
)
from app.schemas.user_schema import AdminUserUpdate, UserOut
from app.utils.error_handler import AppError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserOut])
def admin_list_users(
    role: Optional[List[str]] = Query(
        default=None, description="Filter by role(s); repeat for multiple"
    ),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> List[UserOut]:
    return [UserOut.model_validate(u) for u in list_users(db, skip=skip, limit=limit, roles=role)]


@router.get("/users/customers", response_model=List[UserOut])
def admin_list_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> List[UserOut]:
    return [UserOut.model_validate(u) for u in list_users(db, skip=skip, limit=limit, roles=["customer"])]


@router.get("/users/vendors", response_model=List[UserOut])
def admin_list_vendors(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> List[UserOut]:
    return [UserOut.model_validate(u) for u in list_users(db, skip=skip, limit=limit, roles=["vendor"])]


@router.patch("/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> UserOut:
    updated = update_user(
        db,
        user_id,
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        is_active=payload.is_active,
    )
    if updated is None:
        raise AppError(404, "User not found")
    return UserOut.model_validate(updated)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
) -> None:
    if not delete_user(db, user_id):
        raise AppError(404, "User not found")