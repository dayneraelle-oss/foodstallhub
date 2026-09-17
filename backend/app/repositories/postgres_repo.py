"""Data access layer for PostgreSQL (users, stalls, menu items)."""

from typing import Iterator, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.menu import MenuItem
from app.models.stall import Stall
from app.models.user import User

settings = get_settings()

engine = create_engine(
    settings.POSTGRES_DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------- users


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    hashed_password: str,
    role: str = "customer",
    phone: Optional[str] = None,
) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        phone=phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: int,
    *,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if user is None:
        return None
    if full_name is not None:
        user.full_name = full_name
    if phone is not None:
        user.phone = phone
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user_by_id(db, user_id)
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    roles: Optional[List[str]] = None,
) -> List[User]:
    query = db.query(User)
    if roles:
        query = query.filter(User.role.in_(roles))
    return query.order_by(User.id).offset(skip).limit(limit).all()


# ---------------------------------------------------------------- stalls


def get_stall(db: Session, stall_id: int) -> Optional[Stall]:
    return db.query(Stall).filter(Stall.id == stall_id).first()


def list_stalls(
    db: Session,
    *,
    city: Optional[str] = None,
    cuisine: Optional[str] = None,
    is_open: Optional[bool] = None,
    approved_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Stall]:
    query = db.query(Stall)
    if city:
        query = query.filter(Stall.city.ilike(f"%{city}%"))
    if cuisine:
        query = query.filter(Stall.cuisine.ilike(f"%{cuisine}%"))
    if is_open is not None:
        query = query.filter(Stall.is_open == is_open)
    if approved_only:
        query = query.filter(Stall.is_approved.is_(True))
    return query.order_by(Stall.id).offset(skip).limit(limit).all()


def create_stall(
    db: Session,
    *,
    owner_id: int,
    name: str,
    address: str,
    city: str,
    description: Optional[str] = None,
    cuisine: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    image_url: Optional[str] = None,
    is_approved: Optional[bool] = None,
) -> Stall:
    stall = Stall(
        owner_id=owner_id,
        name=name,
        address=address,
        city=city,
        description=description,
        cuisine=cuisine,
        latitude=latitude,
        longitude=longitude,
        image_url=image_url,
        is_approved=is_approved if is_approved is not None else True,
    )
    db.add(stall)
    db.commit()
    db.refresh(stall)
    return stall


def update_stall(
    db: Session,
    stall_id: int,
    fields: dict,
) -> Optional[Stall]:
    stall = get_stall(db, stall_id)
    if stall is None:
        return None
    for key, value in fields.items():
        setattr(stall, key, value)
    db.commit()
    db.refresh(stall)
    return stall


def delete_stall(db: Session, stall_id: int) -> bool:
    stall = get_stall(db, stall_id)
    if stall is None:
        return False
    db.delete(stall)
    db.commit()
    return True


# ---------------------------------------------------------------- menu


def get_menu_item(db: Session, item_id: int) -> Optional[MenuItem]:
    return db.query(MenuItem).filter(MenuItem.id == item_id).first()


def list_menu_items_by_stall(
    db: Session,
    stall_id: int,
    *,
    available_only: bool = True,
) -> List[MenuItem]:
    query = db.query(MenuItem).filter(MenuItem.stall_id == stall_id)
    if available_only:
        query = query.filter(MenuItem.is_available.is_(True))
    return query.order_by(MenuItem.category, MenuItem.name).all()


def list_all_menu_items(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[MenuItem]:
    """Every menu item on the platform (super admin ledger)."""
    return (
        db.query(MenuItem)
        .order_by(MenuItem.stall_id, MenuItem.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_menu_item(
    db: Session,
    *,
    stall_id: int,
    name: str,
    price,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image_url: Optional[str] = None,
    tags: Optional[str] = None,
    prep_time_minutes: Optional[int] = None,
    serving_size: Optional[str] = None,
) -> MenuItem:
    item = MenuItem(
        stall_id=stall_id,
        name=name,
        price=price,
        description=description,
        category=category,
        image_url=image_url,
        tags=tags,
        prep_time_minutes=prep_time_minutes,
        serving_size=serving_size,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_menu_items(
    db: Session,
    *,
    stall_id: int,
    items: List[dict],
) -> List[MenuItem]:
    created = []
    for data in items:
        item = MenuItem(stall_id=stall_id, **data)
        db.add(item)
        created.append(item)
    db.commit()
    for item in created:
        db.refresh(item)
    return created


def update_menu_item(
    db: Session,
    item_id: int,
    fields: dict,
) -> Optional[MenuItem]:
    item = get_menu_item(db, item_id)
    if item is None:
        return None
    for key, value in fields.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_menu_item(db: Session, item_id: int) -> bool:
    item = get_menu_item(db, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def delete_menu_items_by_stall(db: Session, stall_id: int) -> None:
    db.query(MenuItem).filter(MenuItem.stall_id == stall_id).delete()
    db.commit()


def bulk_create_menu_items(
    db: Session,
    stall_id: int,
    items: List[dict],
) -> List[MenuItem]:
    created = []
    for item_data in items:
        item = MenuItem(stall_id=stall_id, **item_data)
        db.add(item)
        created.append(item)
    db.commit()
    for item in created:
        db.refresh(item)
    return created


def count_rows(db: Session, model) -> int:
    return db.query(model).count()