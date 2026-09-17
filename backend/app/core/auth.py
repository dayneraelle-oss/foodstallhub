"""Authentication dependencies used across controllers."""

from typing import Callable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.postgres_repo import get_db, get_user_by_id
from app.utils.error_handler import AppError

ROLE_CUSTOMER = "customer"
ROLE_VENDOR = "vendor"
ROLE_ADMIN = "admin"
ROLE_SUPER_ADMIN = "super_admin"

ALL_ROLES = (ROLE_CUSTOMER, ROLE_VENDOR, ROLE_ADMIN, ROLE_SUPER_ADMIN)

_bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token."""
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise AppError(401, "Access token has expired")
    except jwt.InvalidTokenError:
        raise AppError(401, "Invalid or malformed access token")

    subject = payload.get("sub")
    if not subject:
        raise AppError(401, "Access token is missing a subject")

    try:
        user_id = int(subject)
    except ValueError:
        raise AppError(401, "Access token subject is invalid")

    user = get_user_by_id(db, user_id)
    if user is None:
        raise AppError(401, "User associated with this token no longer exists")
    if not user.is_active:
        raise AppError(403, "This account has been disabled")

    return user


def require_roles(*roles: str) -> Callable:
    """Return a dependency that only allows the given roles.

    A super admin bypasses every restriction and is always allowed.
    """

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role in roles or user.role == ROLE_SUPER_ADMIN:
            return user
        raise AppError(403, "You do not have permission to perform this action")

    return _checker