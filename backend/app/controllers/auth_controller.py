from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.postgres_repo import (
    create_user,
    get_db,
    get_user_by_email,
)
from app.schemas.user_schema import Token, UserCreate, UserLogin, UserOut
from app.utils.error_handler import AppError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "A user with this email already exists")

    user = create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(401, "Incorrect email or password")
    if not user.is_active:
        raise AppError(403, "This account has been disabled")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)