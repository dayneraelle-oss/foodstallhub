"""Create (or re-seed) a super admin account.

Usage:
    python -m scripts.create_superadmin \
        --email superadmin@foodstallhub.com --password "choose-a-strong-pass"
"""

import argparse

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories.postgres_repo import (
    SessionLocal,
    create_user,
    get_user_by_email,
)


def create_superadmin(email: str, name: str, password: str) -> None:
    db: Session = SessionLocal()
    try:
        existing = get_user_by_email(db, email)
        if existing is not None:
            print(f"super_admin '{email}' already exists (id={existing.id})")
            return
        user = create_user(
            db,
            email=email,
            full_name=name,
            hashed_password=hash_password(password),
            role="super_admin",
        )
        print(f"Created super_admin id={user.id} email={user.email} role={user.role}")
        print("Log in at http://localhost:8000/superadmin")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a super admin account")
    parser.add_argument("--email", default="superadmin@foodstallhub.com")
    parser.add_argument("--name", default="Super Admin")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    if not args.password:
        parser.error("--password is required")
    if len(args.password) < 8:
        parser.error("Password must be at least 8 characters")
    create_superadmin(args.email, args.name, args.password)


if __name__ == "__main__":
    main()