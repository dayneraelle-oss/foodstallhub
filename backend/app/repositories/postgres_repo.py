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
) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if user is None:
        return None
    if full_name is not None:
        user.full_name = full_name
    if phone is not None:
        user.phone = phone
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).order_by(User.id).offset(skip).limit(limit).all()


# ---------------------------------------------------------------- stalls


def get_stall(db: Session, stall_id: int) -> Optional[Stall]:
    return db.query(Stall).filter(Stall.id == stall_id).first()


def list_stalls(
    db: Session,
    *,
    city: Optional[str] = None,
    cuisine: Optional[str] = None,
    is_open: Optional[bool] = None,
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


def create_menu_item(
    db: Session,
    *,
    stall_id: int,
    name: str,
    price,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image_url: Optional[str] = None,
) -> MenuItem:
    item = MenuItem(
        stall_id=stall_id,
        name=name,
        price=price,
        description=description,
        category=category,
        image_url=image_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


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


def count_rows(db: Session, model) -> int:
    return db.query(model).count()