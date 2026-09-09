from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import ROLE_ADMIN, ROLE_VENDOR, get_current_user, require_roles
from app.models.user import User
from app.repositories.postgres_repo import (
    create_menu_item,
    delete_menu_item,
    get_db,
    get_menu_item,
    get_stall,
    list_menu_items_by_stall,
    update_menu_item,
)
from app.schemas.menu_schema import MenuItemCreate, MenuItemOut, MenuItemUpdate
from app.utils.error_handler import AppError

router = APIRouter(tags=["menu"])


def _ensure_manages_stall(user: User, stall_id: int, db: Session) -> None:
    stall = get_stall(db, stall_id)
    if stall is None:
        raise AppError(404, "Stall not found")
    if user.role == ROLE_ADMIN:
        return
    if user.role == ROLE_VENDOR and stall.owner_id == user.id:
        return
    raise AppError(403, "You do not own this stall")


@router.get("/stalls/{stall_id}/menu", response_model=List[MenuItemOut])
def list_menu(
    stall_id: int,
    include_unavailable: bool = False,
    db: Session = Depends(get_db),
) -> List[MenuItemOut]:
    if get_stall(db, stall_id) is None:
        raise AppError(404, "Stall not found")

    items = list_menu_items_by_stall(
        db,
        stall_id,
        available_only=not include_unavailable,
    )
    return [MenuItemOut.model_validate(i) for i in items]


@router.post(
    "/stalls/{stall_id}/menu",
    response_model=MenuItemOut,
    status_code=status.HTTP_201_CREATED,
)
def add_menu_item(
    stall_id: int,
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> MenuItemOut:
    _ensure_manages_stall(user, stall_id, db)

    item = create_menu_item(
        db,
        stall_id=stall_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        image_url=payload.image_url,
    )
    return MenuItemOut.model_validate(item)


@router.put("/menu/{item_id}", response_model=MenuItemOut)
def update_a_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> MenuItemOut:
    item = get_menu_item(db, item_id)
    if item is None:
        raise AppError(404, "Menu item not found")
    _ensure_manages_stall(user, item.stall_id, db)

    fields = payload.model_dump(exclude_unset=True)
    updated = update_menu_item(db, item_id, fields)
    return MenuItemOut.model_validate(updated)


@router.patch("/menu/{item_id}/availability", response_model=MenuItemOut)
def toggle_menu_item_availability(
    item_id: int,
    is_available: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> MenuItemOut:
    item = get_menu_item(db, item_id)
    if item is None:
        raise AppError(404, "Menu item not found")
    _ensure_manages_stall(user, item.stall_id, db)

    fields = {"is_available": not item.is_available if is_available is None else is_available}
    updated = update_menu_item(db, item_id, fields)
    return MenuItemOut.model_validate(updated)


@router.delete("/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_VENDOR, ROLE_ADMIN)),
) -> None:
    item = get_menu_item(db, item_id)
    if item is None:
        raise AppError(404, "Menu item not found")
    _ensure_manages_stall(user, item.stall_id, db)
    delete_menu_item(db, item_id)