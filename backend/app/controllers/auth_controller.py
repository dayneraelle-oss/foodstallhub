from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.postgres_repo import (
    create_user,
    get_db,
    get_user_by_email,
)
from app.schemas.user_schema import (
    AdminRegister,
    CustomerRegister,
    SuperAdminRegister,
    Token,
    UserLogin,
    UserOut,
    VendorRegister,
)
from app.utils.error_handler import AppError

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()


# ── Customer Auth ──────────────────────────────────────────────────────────────


@router.post(
    "/customers/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["customer-auth"],
)
def register_customer(payload: CustomerRegister, db: Session = Depends(get_db)) -> UserOut:
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "A user with this email already exists")

    user = create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="customer",
        phone=payload.phone,
    )
    return UserOut.model_validate(user)


@router.post(
    "/customers/login",
    response_model=Token,
    tags=["customer-auth"],
)
def login_customer(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(401, "Incorrect email or password")
    if user.role != "customer":
        raise AppError(403, "This account is not a customer account")
    if not user.is_active:
        raise AppError(403, "This account has been disabled")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


# ── Vendor Auth ────────────────────────────────────────────────────────────────


@router.post(
    "/vendors/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["vendor-auth"],
)
def register_vendor(payload: VendorRegister, db: Session = Depends(get_db)) -> UserOut:
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "A user with this email already exists")

    user = create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="vendor",
        phone=payload.phone,
    )
    return UserOut.model_validate(user)


@router.post(
    "/vendors/login",
    response_model=Token,
    tags=["vendor-auth"],
)
def login_vendor(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(401, "Incorrect email or password")
    if user.role != "vendor":
        raise AppError(403, "This account is not a vendor account")
    if not user.is_active:
        raise AppError(403, "This account has been disabled")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


# ── Admin Auth ─────────────────────────────────────────────────────────────────


@router.post(
    "/admin/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["admin-auth"],
)
def register_admin(payload: AdminRegister, db: Session = Depends(get_db)) -> UserOut:
    if payload.admin_key != settings.ADMIN_REGISTRATION_KEY:
        raise AppError(403, "Invalid admin registration key")
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "A user with this email already exists")

    user = create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="admin",
    )
    return UserOut.model_validate(user)


@router.post(
    "/admin/login",
    response_model=Token,
    tags=["admin-auth"],
)
def login_admin(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(401, "Incorrect email or password")
    if user.role != "admin":
        raise AppError(403, "This account is not an admin account")
    if not user.is_active:
        raise AppError(403, "This account has been disabled")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


# ── Super Admin Auth ───────────────────────────────────────────────────────────


@router.post(
    "/superadmin/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["superadmin-auth"],
)
def register_super_admin(
    payload: SuperAdminRegister, db: Session = Depends(get_db)
) -> UserOut:
    if payload.super_admin_key != settings.SUPER_ADMIN_REGISTRATION_KEY:
        raise AppError(403, "Invalid super admin registration key")
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "A user with this email already exists")

    user = create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="super_admin",
    )
    return UserOut.model_validate(user)


@router.post(
    "/superadmin/login",
    response_model=Token,
    tags=["superadmin-auth"],
)
def login_super_admin(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(401, "Incorrect email or password")
    if user.role != "super_admin":
        raise AppError(403, "This account is not a super admin account")
    if not user.is_active:
        raise AppError(403, "This account has been disabled")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


# ── Shared ─────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)