"""Super admin endpoints — a hidden control plane.

Restricted to the `super_admin` role only (which also bypasses every other
role check via require_roles). Exposes the full platform transaction ledger.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import ROLE_SUPER_ADMIN, ROLE_VENDOR, require_roles
from app.models.menu import MenuItem
from app.models.order import OrderItemInDB, OrderStatus, PaymentMethod, PaymentStatus
from app.models.stall import Stall
from app.models.user import User
from app.repositories import mongo_repo
from app.repositories.postgres_repo import (
    bulk_create_menu_items,
    count_rows,
    create_menu_item,
    create_stall,
    get_db,
    get_stall,
    get_user_by_id,
    list_all_menu_items as repo_list_all_menu_items,
    list_stalls,
)
from app.schemas.menu_schema import MenuItemBulkCreate, MenuItemCreate, MenuItemOut
from app.schemas.stall_schema import StallCreate, StallOut
from app.utils.error_handler import AppError

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


class SuperAdminStallCreate(StallCreate):
    owner_id: int = Field(description="Vendor user id who owns this stall")


class StallApproval(BaseModel):
    is_approved: bool = Field(
        description="True to approve/register the stall, False to reject it"
    )


class TransactionOut(BaseModel):
    order_id: str
    user_id: int
    user_email: str
    stall_id: int
    stall_name: str
    items: List[OrderItemInDB]
    subtotal: float
    delivery_fee: float
    total: float
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    created_at: str
    updated_at: str


class TransactionsSummary(BaseModel):
    transactions_count: int
    gross_volume: float
    revenue: float
    paid_amount: float
    pending_amount: float
    cancelled_amount: float
    cancelled_count: int
    by_payment_method: List[dict]
    by_status: List[dict]
    users_count: int = 0
    stall_count: int = 0
    menu_items_count: int = 0


class StallRecord(BaseModel):
    id: int
    owner_id: int
    owner_name: str
    owner_email: str
    name: str
    cuisine: Optional[str]
    city: str
    address: str
    is_open: bool
    is_approved: bool
    created_at: str
    items_count: int


class MenuRecord(BaseModel):
    id: int
    stall_id: int
    stall_name: str
    name: str
    price: float
    category: Optional[str]
    is_available: bool
    tags: Optional[str]
    prep_time_minutes: Optional[int] = None
    serving_size: Optional[str] = None
    created_at: str


def _to_transaction(document: dict, db: Session) -> TransactionOut:
    user = get_user_by_id(db, document["user_id"])
    stall = get_stall(db, document["stall_id"])
    return TransactionOut(
        order_id=document["_id"],
        user_id=document["user_id"],
        user_email=user.email if user else f"user #{document['user_id']}",
        stall_id=document["stall_id"],
        stall_name=stall.name if stall else f"stall #{document['stall_id']}",
        items=document.get("items", []),
        subtotal=document["subtotal"],
        delivery_fee=document["delivery_fee"],
        total=document["total"],
        status=document["status"],
        payment_method=document["payment_method"],
        payment_status=document["payment_status"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


@router.get("/transactions", response_model=List[TransactionOut])
def list_all_transactions(
    status: Optional[OrderStatus] = Query(default=None),
    payment_status: Optional[PaymentStatus] = Query(default=None),
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> List[TransactionOut]:
    try:
        documents = mongo_repo.list_all_orders(
            skip=skip,
            limit=limit,
            status=status.value if status else None,
            payment_status=payment_status.value if payment_status else None,
        )
    except Exception:
        documents = []
    return [_to_transaction(d, db) for d in documents]


@router.get("/transactions/summary", response_model=TransactionsSummary)
def transaction_summary(
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> TransactionsSummary:
    try:
        data = mongo_repo.transactions_summary()
    except Exception:
        data = {
            "transactions_count": 0,
            "gross_volume": 0.0,
            "revenue": 0.0,
            "paid_amount": 0.0,
            "pending_amount": 0.0,
            "cancelled_amount": 0.0,
            "cancelled_count": 0,
            "by_payment_method": [],
            "by_status": [],
        }
    data["users_count"] = count_rows(db, User)
    data["stall_count"] = count_rows(db, Stall)
    data["menu_items_count"] = count_rows(db, MenuItem)
    return TransactionsSummary(**data)


@router.get("/stalls", response_model=List[StallRecord])
def list_all_stalls(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> List[StallRecord]:
    records: List[StallRecord] = []
    for stall in list_stalls(db, skip=skip, limit=limit):
        owner = get_user_by_id(db, stall.owner_id)
        records.append(
            StallRecord(
                id=stall.id,
                owner_id=stall.owner_id,
                owner_name=owner.full_name if owner else "—",
                owner_email=owner.email if owner else "",
                name=stall.name,
                cuisine=stall.cuisine,
                city=stall.city,
                address=stall.address,
                is_open=stall.is_open,
                is_approved=stall.is_approved,
                created_at=stall.created_at.isoformat() if stall.created_at else "",
                items_count=len(stall.menus),
            )
        )
    return records


@router.get("/menu", response_model=List[MenuRecord])
def list_all_menu_records(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> List[MenuRecord]:
    records: List[MenuRecord] = []
    for item in repo_list_all_menu_items(db, skip=skip, limit=limit):
        stall = get_stall(db, item.stall_id)
        records.append(
            MenuRecord(
                id=item.id,
                stall_id=item.stall_id,
                stall_name=stall.name if stall else f"stall #{item.stall_id}",
                name=item.name,
                price=float(item.price),
                category=item.category,
                is_available=item.is_available,
                tags=item.tags,
                prep_time_minutes=item.prep_time_minutes,
                serving_size=item.serving_size,
                created_at=item.created_at.isoformat() if item.created_at else "",
            )
        )
    return records


@router.post("/stalls", response_model=StallOut, status_code=status.HTTP_201_CREATED)
def register_a_stall(
    payload: SuperAdminStallCreate,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> StallOut:
    owner = get_user_by_id(db, payload.owner_id)
    if owner is None:
        raise AppError(404, "Stall owner not found")
    if owner.role != ROLE_VENDOR:
        raise AppError(400, "Stall owner must be a vendor account")

    stall = create_stall(
        db,
        owner_id=owner.id,
        name=payload.name,
        description=payload.description,
        cuisine=payload.cuisine,
        address=payload.address,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        image_url=payload.image_url,
        is_approved=True,
    )
    return StallOut.model_validate(stall)


@router.post("/stalls/{stall_id}/approval", response_model=StallOut)
def set_stall_approval(
    stall_id: int,
    payload: StallApproval,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> StallOut:
    stall = get_stall(db, stall_id)
    if stall is None:
        raise AppError(404, "Stall not found")

    stall.is_approved = payload.is_approved
    db.commit()
    db.refresh(stall)
    return StallOut.model_validate(stall)


@router.post(
    "/stalls/{stall_id}/menu",
    response_model=MenuItemOut,
    status_code=status.HTTP_201_CREATED,
)
def register_a_menu_item(
    stall_id: int,
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> MenuItemOut:
    if get_stall(db, stall_id) is None:
        raise AppError(404, "Stall not found")

    item = create_menu_item(
        db,
        stall_id=stall_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        image_url=payload.image_url,
        tags=payload.tags,
        prep_time_minutes=payload.prep_time_minutes,
        serving_size=payload.serving_size,
    )
    return MenuItemOut.model_validate(item)


@router.post(
    "/stalls/{stall_id}/menu/batch",
    response_model=List[MenuItemOut],
    status_code=status.HTTP_201_CREATED,
)
def register_menu_items_batch(
    stall_id: int,
    payload: MenuItemBulkCreate,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
) -> List[MenuItemOut]:
    if get_stall(db, stall_id) is None:
        raise AppError(404, "Stall not found")

    items = bulk_create_menu_items(
        db,
        stall_id=stall_id,
        items=[item.model_dump() for item in payload.items],
    )
    return [MenuItemOut.model_validate(i) for i in items]